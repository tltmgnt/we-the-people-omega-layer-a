import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import urlopen,Request
from civic_portfolio.finance import Finance,CATEGORIES
from civic_portfolio.store import Store,Conflict
from civic_portfolio.__main__ import server

class FinanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'db.sqlite3');self.lab=Finance(self.store)
        self.lab.create(dict(ledger_id='SYN-BUDGET',label='Fictional',currency='USD',minor_unit_digits=2,period='Demo 2026',basis='Declared scenario accrual',at='2026-01-01T00:00:00Z',actor='RECORDER'))
    def record(self,kind='ENTRY',value=123,category='EXPENDITURE',actor='RECORDER',at='2026-01-01T01:00:00Z'):
        return self.lab.record('SYN-BUDGET',dict(version=self.lab.ledger('SYN-BUDGET')['version'],kind=kind,category=category,amount_minor=value,reference='SYN-EVIDENCE',note='Fictional explanation',at=at,actor=actor))
    def report(self,at='2026-01-02T00:00:00Z'):
        return self.lab.report('SYN-BUDGET',at)
    def row(self):return next(r for r in self.report()['categories'] if r['category']=='EXPENDITURE')
    def test_nulls_and_category_separation(self):
        self.assertTrue(all(r['recorded_minor'] is None for r in self.report()['categories']))
        self.record();self.assertEqual(self.row()['recorded_minor'],123)
        self.assertEqual(sum(r['recorded_minor'] is not None for r in self.report()['categories']),1)
        self.assertIsNone(self.row()['discrepancy_minor'])
    def test_exact_signed_adjustments_and_discrepancy(self):
        self.record(value=1000000000000);self.record(value=-999999999899)
        self.record('RECONCILIATION',100,actor='CHECKER');self.assertEqual(self.row()['discrepancy_minor'],1)
        self.record(value=-1);self.assertFalse(self.row()['comparison_current'])
        self.record('RECONCILIATION',100,actor='CHECKER');self.assertEqual(self.row()['discrepancy_minor'],0)
        self.assertEqual(self.report()['unresolved_category_age_hours']['sample_size'],0)
    def test_validation_and_independent_reconciler(self):
        for value in (True,1.1,'1',None,10**12+1):
            with self.assertRaises(ValueError):self.record(value=value)
        with self.assertRaises(ValueError):self.record(category=[])
        self.record()
        with self.assertRaises(ValueError):self.record('RECONCILIATION')
        with self.assertRaises(ValueError):self.record(kind='OUTCOME')
        self.assertEqual(len(self.lab.ledger('SYN-BUDGET')['events']),1)
    def test_stale_writes_and_chronology(self):
        self.record();event=self.lab.ledger('SYN-BUDGET')['events'][0]
        with self.assertRaises(Conflict):self.lab.record('SYN-BUDGET',{k:event[k] for k in ('version','kind','category','amount_minor','reference','note','at','actor')})
        with self.assertRaises(ValueError):self.record(at='2025-01-01T00:00:00Z')
        with self.assertRaises(KeyError):self.lab.ledger('SYN-MISSING')
    def test_revision_binding_and_asof(self):
        self.record();self.record('RECONCILIATION',123,actor='CHECKER');self.record(value=0)
        self.assertFalse(self.row()['comparison_current'])
        self.record('RECONCILIATION',123,actor='CHECKER',at='2026-01-01T03:00:00Z')
        self.assertTrue(self.row()['comparison_current'])
        older=self.report('2026-01-01T02:00:00Z')
        self.assertFalse(next(r for r in older['categories'] if r['category']=='EXPENDITURE')['comparison_current'])
        self.assertEqual(older['unresolved_category_age_hours']['median'],1)
    def test_outcomes_backup_export(self):
        self.record('OUTCOME',None,None)
        self.assertEqual(len(self.report()['outcome_notes']),1)
        self.assertTrue(all(r['recorded_minor'] is None for r in self.report()['categories']))
        exported=self.store.export();self.assertEqual(len(exported['synthetic_finance']['events']),1)
        target=Path(self.tmp.name)/'backup.sqlite3';self.store.backup(target)
        self.assertEqual(Finance(Store(target)).ledger('SYN-BUDGET')['events'],self.lab.ledger('SYN-BUDGET')['events'])
    def test_http_and_guard(self):
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base='http://127.0.0.1:'+str(app.server_port)
        self.assertIn(b'Synthetic public-finance',urlopen(base+'/finance').read())
        boot=json.load(urlopen(base+'/api/finance'));self.assertEqual(len(boot['ledgers']),1)
        report=json.load(urlopen(base+'/api/finance/SYN-BUDGET/report?as_of=2026-01-02T00:00:00Z'));self.assertFalse(report['execution_authorized'])
        from urllib.error import HTTPError
        with self.assertRaises(HTTPError) as error:urlopen(Request(base+'/api/finance/SYN-BUDGET/records',data=b'{}',headers={'Content-Type':'application/json'}))
        self.assertEqual(error.exception.code,403)
