import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import urlopen, Request

from civic_portfolio.__main__ import server
from civic_portfolio.maintenance import Maintenance
from civic_portfolio.store import Conflict, Store


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.store=Store(Path(self.directory.name)/'test.sqlite3');self.lab=Maintenance(self.store)

    def asset(self,asset_id='SYN-ASSET',area='TEST AREA'):
        return self.lab.create_asset(dict(asset_id=asset_id,category='Fictional sidewalk',area=area,at='2026-01-01T00:00:00Z',actor='TEST',evidence='Synthetic asset register'))

    def order(self,order_id='SYN-WORK',asset_id='SYN-ASSET'):
        return self.lab.create_order(dict(order_id=order_id,asset_id=asset_id,condition='Fictional surface defect',at='2026-01-01T01:00:00Z',actor='TEST',evidence='Synthetic condition observation'))

    def event(self,stage,hour,order_id='SYN-WORK',actor='TEST WORKER'):
        return self.lab.advance(order_id,dict(version=self.lab.order(order_id)['version'],stage=stage,at=f'2026-01-01T{hour:02}:00:00Z',actor=actor,evidence='Synthetic stage rationale',priority='URGENT' if stage=='TRIAGED' else None,team='SYNTHETIC TEAM' if stage=='SCHEDULED' else None))

    def check(self,hour,passed=True,verifier='TEST VERIFIER',order_id='SYN-WORK'):
        return self.lab.verify(order_id,dict(version=self.lab.order(order_id)['version'],at=f'2026-01-01T{hour:02}:00:00Z',verifier=verifier,passed=passed,evidence='Synthetic verification criteria and result'))

    def ready(self):
        self.asset();self.order()
        for stage,hour in [('TRIAGED',2),('SCHEDULED',3),('IN_PROGRESS',4),('VERIFICATION',5)]:self.event(stage,hour)

    def test_empty_report_and_assets_without_orders(self):
        r=self.lab.report('2026-01-02T00:00:00Z');self.assertEqual(r['assets'],0)
        self.assertIsNone(r['verified_elapsed_calendar_hours']['median'])
        self.asset();r=self.lab.report('2026-01-02T00:00:00Z')
        self.assertEqual(r['area_inventory']['TEST AREA'],dict(assets=1,reported_orders=0,open_orders=0))
        self.assertFalse(r['execution_authorized'])

    def test_verified_closure_and_reopening(self):
        self.ready()
        with self.assertRaises(ValueError):self.event('CLOSED',6)
        with self.assertRaises(ValueError):self.check(6,verifier='TEST WORKER')
        self.check(6);self.event('CLOSED',7)
        r=self.lab.report('2026-01-01T08:00:00Z')
        self.assertEqual(r['closed_orders'],1);self.assertEqual(r['verified_elapsed_calendar_hours']['median'],6)
        self.event('TRIAGED',9);r=self.lab.report('2026-01-01T10:00:00Z')
        self.assertEqual((r['closed_orders'],r['open_orders'],r['reopen_events']),(0,1,1))
        self.assertEqual(r['backlog_age_calendar_hours']['median'],9)
        self.assertEqual(self.lab.report('2026-01-01T08:00:00Z')['closed_orders'],1)

    def test_old_check_cannot_authorize_new_verification_stage_even_at_same_time(self):
        self.ready();self.check(5);self.event('CLOSED',5)
        for stage in ['TRIAGED','SCHEDULED','IN_PROGRESS','VERIFICATION']:self.event(stage,5)
        with self.assertRaises(ValueError):self.event('CLOSED',5)
        self.check(5);self.event('CLOSED',5)
        self.assertEqual(self.lab.order('SYN-WORK')['stage'],'CLOSED')

    def test_failed_verification_and_correction_loop(self):
        self.ready();self.check(6,False)
        with self.assertRaises(ValueError):self.event('CLOSED',7)
        with self.assertRaises(ValueError):self.event('IN_PROGRESS',5)
        self.event('IN_PROGRESS',7);self.event('VERIFICATION',8);self.check(9);self.event('CLOSED',10)
        r=self.lab.report('2026-01-01T11:00:00Z')
        self.assertEqual(r['failed_verifications'],1)
        self.assertEqual(r['verified_elapsed_calendar_hours']['median'],9)
        self.assertEqual(len(self.lab.order('SYN-WORK')['checks']),2)

    def test_input_validation_chronology_and_version_conflicts(self):
        self.asset()
        with self.assertRaises(Conflict):self.asset()
        with self.assertRaises(KeyError):self.order(asset_id='SYN-MISSING')
        self.order()
        with self.assertRaises(Conflict):self.order()
        with self.assertRaises(ValueError):self.event('CLOSED',2)
        with self.assertRaises(ValueError):self.event('TRIAGED',0)
        base=dict(version=1,stage='TRIAGED',at='2026-01-01T02:00:00Z',actor='TEST',evidence='Triage rationale',priority='URGENT',team=None)
        for change in [dict(priority=None),dict(priority=[]),dict(evidence=''),dict(version=True)]:
            with self.subTest(change=change),self.assertRaises(ValueError):self.lab.advance('SYN-WORK',{**base,**change})
        self.lab.advance('SYN-WORK',base)
        with self.assertRaises(Conflict):self.lab.advance('SYN-WORK',base)
        with self.assertRaises(ValueError):
            self.lab.advance('SYN-WORK',{**base,'version':2,'stage':'SCHEDULED','priority':None,'team':''})

    def test_cutoffs_area_filters_priority_and_backlog(self):
        self.asset();self.asset('SYN-OTHER','OTHER AREA');self.order();self.order('SYN-OTHER-WORK','SYN-OTHER')
        self.event('TRIAGED',2)
        r=self.lab.report('2026-01-01T03:00:00Z','TEST AREA')
        self.assertEqual((r['assets'],r['reported_orders'],r['open_orders']),(1,1,1))
        self.assertEqual(r['open_by_priority'],{'URGENT':1})
        self.assertEqual(r['backlog_age_calendar_hours']['median'],2)
        self.assertEqual(self.lab.report('2026-01-01T01:30:00Z','TEST AREA')['open_by_priority'],{'UNTRIAGED':1})
        self.assertEqual(self.lab.report('2025-12-31T23:00:00Z')['assets'],0)
        self.assertEqual(self.lab.report('2026-01-02T00:00:00Z','MISSING')['reported_orders'],0)

    def test_export_backup_and_http_workflow(self):
        self.asset();self.order()
        backup=Path(self.directory.name)/'backup.sqlite3';self.store.backup(backup)
        restored=Maintenance(Store(backup));self.assertEqual(restored.order('SYN-WORK'),self.lab.order('SYN-WORK'))
        self.assertEqual(len(self.store.export()['synthetic_maintenance']['assets']),1)
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base=f'http://127.0.0.1:{app.server_port}'
        with urlopen(base+'/api/maintenance') as response:token=json.load(response)['token']
        payload=dict(version=1,stage='TRIAGED',at='2026-01-01T02:00:00Z',actor='TEST',evidence='Synthetic HTTP triage',priority='SAFETY_REVIEW',team=None)
        with urlopen(Request(base+'/api/maintenance/orders/SYN-WORK/events',data=json.dumps(payload).encode(),headers={'X-Portfolio-Token':token,'Content-Type':'application/json'})) as response:
            self.assertEqual(json.load(response)['priority'],'SAFETY_REVIEW')
        with urlopen(base+'/api/maintenance/report?area=TEST%20AREA') as response:self.assertEqual(json.load(response)['open_orders'],1)
        with urlopen(base+'/maintenance') as response:self.assertIn(b'Synthetic maintenance lab',response.read())


if __name__=='__main__':unittest.main()
