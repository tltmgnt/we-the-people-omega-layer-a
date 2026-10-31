from pathlib import Path
import tempfile
import threading
import unittest
import json
from urllib.request import urlopen, Request

from civic_portfolio.store import Store, Conflict
from civic_portfolio.permits import Permits, timestamp, hours
from civic_portfolio.__main__ import server


class PermitTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = Store(Path(self.directory.name) / 'test.sqlite3')
        self.permits = Permits(self.store)

    def create(self, identifier='SYN-A', at='2026-01-01T00:00:00Z', category='TEST'):
        return self.permits.create(dict(case_id=identifier,category=category,at=at,actor='SYNTHETIC TEST',evidence='Fictional intake'))

    def advance(self, stage, at, identifier='SYN-A', staff=None, public=None):
        return self.permits.advance(identifier,dict(version=self.permits.case(identifier)['version'],stage=stage,at=at,actor='SYNTHETIC TEST',evidence='Fictional stage evidence',staff_hours=staff,public_hours=public))

    def finish(self, identifier='SYN-A', category='TEST'):
        self.create(identifier, category=category)
        for stage,hour in [('IN_REVIEW',1),('INSPECTION',2),('DECIDED',3)]:
            self.advance(stage,f'2026-01-01T{hour:02}:00:00Z',identifier)

    def test_empty_measurements_are_null_not_fabricated(self):
        report=self.permits.report('2026-01-02T00:00:00Z')
        self.assertEqual(report['arrivals'],0)
        self.assertIsNone(report['elapsed_calendar_hours']['median'])
        self.assertIsNone(report['quality_pass_rate'])
        self.assertFalse(report['execution_authorized'])

    def test_lifecycle_corrections_and_closed_cases(self):
        self.create()
        for stage,hour in [('IN_REVIEW',1),('AWAITING_CORRECTION',2),('IN_REVIEW',3),('INSPECTION',4),('DECIDED',10)]:
            self.advance(stage,f'2026-01-01T{hour:02}:00:00Z',staff=1,public=.5)
        case=self.permits.case('SYN-A')
        self.assertEqual(case['stage'],'DECIDED')
        self.assertEqual(case['allowed_next_stages'],[])
        self.assertFalse(case['execution_authorized'])
        self.assertEqual(len(case['events']),6)
        report=self.permits.report('2026-01-02T00:00:00Z')
        self.assertEqual(report['correction_cycles'],1)
        self.assertEqual(report['elapsed_calendar_hours']['median'],10)
        self.assertEqual(report['staff_person_hours']['median'],5)
        self.assertEqual(report['public_person_hours']['median'],2.5)
        self.assertEqual(report['stage_calendar_hours']['AWAITING_CORRECTION'],1)

    def test_invalid_timestamps_transitions_effort_and_stale_edits(self):
        self.create()
        with self.assertRaises(Conflict):
            self.create()
        for value in ['2026-01-01','2026-01-01T00:00:00','2026-02-30T00:00:00Z','yesterday']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                timestamp(value)
        for value in [True,-1,float('nan'),float('inf'),'2']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                hours(value)
        with self.assertRaises(ValueError):
            self.advance('DECIDED','2026-01-01T01:00:00Z')
        with self.assertRaises(ValueError):
            self.advance('IN_REVIEW','2025-12-31T23:00:00Z')
        self.advance('IN_REVIEW','2026-01-01T01:00:00Z')
        with self.assertRaises(Conflict):
            self.permits.advance('SYN-A',dict(version=1,stage='INSPECTION',at='2026-01-01T02:00:00Z',actor='TEST',evidence='Test',staff_hours=None,public_hours=None))
        self.assertEqual(len(self.permits.case('SYN-A')['events']),2)

    def test_reporting_handles_timezones_categories_censoring_and_withdrawal(self):
        self.finish()
        self.create('SYN-B','2026-01-01T00:00:00+02:00')
        for stage,hour in [('IN_REVIEW',1),('INSPECTION',2),('DECIDED',6)]:
            self.advance(stage,f'2026-01-01T{hour:02}:00:00+02:00','SYN-B')
        self.create('SYN-OPEN')
        self.create('SYN-WITHDRAWN')
        self.advance('WITHDRAWN','2026-01-01T02:00:00Z','SYN-WITHDRAWN')
        self.create('SYN-FUTURE','2026-01-03T00:00:00Z')
        self.finish('SYN-OTHER','OTHER')
        report=self.permits.report('2026-01-02T00:00:00Z','TEST')
        self.assertEqual((report['arrivals'],report['decided'],report['open'],report['withdrawn']),(4,2,1,1))
        self.assertEqual(report['elapsed_calendar_hours'],dict(sample_size=2,median=4.5,p90_nearest_rank=6))
        self.assertEqual(report['open_age_calendar_hours']['median'],24)
        self.assertEqual(report['staff_person_hours']['missing_decided_cases'],2)
        self.assertIsNone(report['staff_person_hours']['median'])
        historical=self.permits.report('2026-01-01T00:30:00Z','TEST')
        self.assertEqual(historical['decided'],0)
        self.assertEqual(historical['open'],4)
        self.assertEqual(self.permits.report('2026-01-02T00:00:00Z','NO_MATCH')['arrivals'],0)

    def test_quality_reviews_are_versioned_and_time_scoped(self):
        self.create()
        with self.assertRaises(ValueError):
            self.permits.review('SYN-A',dict(version=1,at='2026-01-01T01:00:00Z',reviewer='TEST',passed=True,evidence='Test criteria'))
        self.advance('IN_REVIEW','2026-01-01T01:00:00Z')
        self.advance('INSPECTION','2026-01-01T02:00:00Z')
        self.advance('DECIDED','2026-01-01T03:00:00Z')
        for hour,passed in [(4,True),(5,False)]:
            self.permits.review('SYN-A',dict(version=self.permits.case('SYN-A')['version'],at=f'2026-01-01T{hour:02}:00:00Z',reviewer='SYNTHETIC REVIEWER',passed=passed,evidence='Synthetic quality criteria and result'))
        self.assertIsNone(self.permits.report('2026-01-01T03:30:00Z')['quality_pass_rate'])
        self.assertEqual(self.permits.report('2026-01-01T04:30:00Z')['quality_pass_rate'],1)
        self.assertEqual(self.permits.report('2026-01-01T05:30:00Z')['quality_pass_rate'],0)
        self.assertEqual(len(self.permits.case('SYN-A')['quality_reviews']),2)

    def test_permit_data_survives_backup_and_export(self):
        self.finish()
        backup=Path(self.directory.name)/'backup.sqlite3'
        self.store.backup(backup)
        restored=Store(backup)
        self.assertEqual(Permits(restored).case('SYN-A'),self.permits.case('SYN-A'))
        exported=self.store.export()
        self.assertEqual(exported['synthetic_permits']['cases'][0]['id'],'SYN-A')
        self.assertEqual(len(exported['synthetic_permits']['events']),4)
        self.assertTrue(any(a['action']=='advance_synthetic_permit' for a in exported['audit']))

    def test_http_permit_workflow_and_report(self):
        app=server(self.store,0)
        thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base=f'http://127.0.0.1:{app.server_port}'
        with urlopen(base+'/api/permits') as response:
            token=json.load(response)['token']
        def post(route,data):
            with urlopen(Request(base+route,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Portfolio-Token':token})) as response:
                return json.load(response)
        case=post('/api/permits',dict(case_id='SYN-HTTP',category='TEST',at='2026-01-01T00:00:00Z',actor='TEST',evidence='Synthetic HTTP intake'))
        result=post('/api/permits/SYN-HTTP/events',dict(version=case['version'],stage='IN_REVIEW',at='2026-01-01T01:00:00Z',actor='TEST',evidence='Synthetic review',staff_hours=.5,public_hours=None))
        self.assertEqual(result['stage'],'IN_REVIEW')
        with urlopen(base+'/api/permits/report?as_of=2026-01-02T00%3A00%3A00Z') as response:
            self.assertEqual(json.load(response)['open'],1)
        with urlopen(base+'/permits') as response:
            self.assertIn(b'Synthetic permit lab',response.read())


if __name__=='__main__':
    unittest.main()
