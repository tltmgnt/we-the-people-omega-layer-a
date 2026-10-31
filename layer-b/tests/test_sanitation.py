import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen

from civic_portfolio.__main__ import server
from civic_portfolio.sanitation import Sanitation
from civic_portfolio.store import Conflict,Store


class SanitationTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.store=Store(Path(self.directory.name)/'workspace.sqlite3');self.lab=Sanitation(self.store)

    def route(self,route_id='SYN-ROUTE',area='DEMO',stream='TRASH',stops=10):
        return self.lab.create_route(dict(route_id=route_id,area=area,stream=stream,expected_stops=stops,at='2026-01-01T00:00:00Z',actor='TEST',evidence='Synthetic route'))

    def schedule(self,run_id='SYN-RUN',route_id='SYN-ROUTE'):
        return self.lab.create_run(dict(run_id=run_id,route_id=route_id,at='2026-01-01T01:00:00Z',actor='TEST WORKER',evidence='Synthetic schedule'))

    def event(self,stage,hour,served=None,run_id='SYN-RUN'):
        return self.lab.advance(run_id,dict(version=self.lab.run(run_id)['version'],stage=stage,at=f'2026-01-01T{hour:02}:00:00Z',actor='TEST WORKER',served_total=served,evidence='Synthetic service observation'))

    def verify(self,hour,observed,run_id='SYN-RUN',verifier='TEST VERIFIER'):
        return self.lab.verify(run_id,dict(version=self.lab.run(run_id)['version'],at=f'2026-01-01T{hour:02}:00:00Z',verifier=verifier,observed_total=observed,evidence='Synthetic count check'))

    def ready(self):
        self.route();self.schedule();self.event('STARTED',2);self.event('SERVICE_RECORDED',3,8)

    def issue(self,issue_id='SYN-REPORT',hour=4):
        return self.lab.create_issue(dict(issue_id=issue_id,run_id='SYN-RUN',description='Fictional anonymous missed-service observation',at=f'2026-01-01T{hour:02}:00:00Z',actor='TEST',evidence='Synthetic report'))

    def response(self,status,hour):
        return self.lab.update_issue('SYN-REPORT',dict(version=self.lab.issue('SYN-REPORT')['version'],status=status,at=f'2026-01-01T{hour:02}:00:00Z',actor='TEST',evidence='Synthetic response record'))

    def test_empty_unverified_and_verified_denominators(self):
        self.assertIsNone(self.lab.report()['verified_missed_service_rate'])
        self.ready();r=self.lab.report('2026-01-01T03:30:00Z')
        self.assertEqual(r['unverified_recorded_runs'],1);self.assertEqual(r['verified_expected_stop_visits'],0)
        self.verify(4,8);r=self.lab.report('2026-01-01T04:30:00Z')
        self.assertEqual((r['verified_runs'],r['verified_expected_stop_visits'],r['verified_missed_stop_visits']),(1,10,2))
        self.assertEqual(r['verified_missed_service_rate'],.2)
        self.assertEqual(self.lab.run('SYN-RUN')['status'],'VERIFIED_SHORTFALL')
        self.assertFalse(r['execution_authorized'])

    def test_verification_mismatch_and_recovery_require_fresh_checks(self):
        self.ready();self.verify(4,7)
        self.assertFalse(self.lab.run('SYN-RUN')['verified'])
        self.verify(5,8);self.event('CORRECTION_RECORDED',5,10)
        self.assertFalse(self.lab.run('SYN-RUN')['verified'])
        self.assertIsNone(self.lab.report('2026-01-01T05:30:00Z')['verified_missed_service_rate'])
        self.verify(6,10);r=self.lab.report('2026-01-01T06:30:00Z')
        self.assertEqual(r['verified_missed_service_rate'],0)
        self.assertEqual(r['verified_recovery_hours']['median'],3)
        self.assertEqual(self.lab.run('SYN-RUN')['status'],'VERIFIED_COMPLETE')
        self.event('CORRECTION_RECORDED',7,6)
        self.assertFalse(self.lab.run('SYN-RUN')['verified'])

    def test_reports_are_separate_from_rate_and_reopening_is_explicit(self):
        self.ready();self.verify(4,8);self.issue();self.issue('SYN-DUPLICATE')
        r=self.lab.report('2026-01-01T04:30:00Z');self.assertEqual(r['anonymous_reports'],2)
        self.assertEqual(r['verified_missed_service_rate'],.2)
        self.response('RESOLVED',5);r=self.lab.report('2026-01-01T05:30:00Z')
        self.assertEqual(r['resolved_report_hours']['median'],1)
        self.response('OPEN',6);r=self.lab.report('2026-01-01T06:30:00Z')
        self.assertEqual((r['open_reports'],r['repeat_report_events']),(2,1))
        self.assertEqual(r['resolved_report_hours']['sample_size'],0)
        self.assertEqual(self.lab.report('2026-01-01T05:30:00Z')['resolved_report_hours']['median'],1)
        self.assertEqual(r['verified_missed_service_rate'],.2)

    def test_input_counts_chronology_versions_and_distinct_verifier(self):
        for stops in [0,-1,True,1.5,'10']:
            with self.subTest(stops=stops),self.assertRaises(ValueError):self.route(stops=stops)
        self.route()
        with self.assertRaises(Conflict):self.route()
        with self.assertRaises(KeyError):self.schedule(route_id='SYN-MISSING')
        self.schedule()
        with self.assertRaises(Conflict):self.schedule()
        with self.assertRaises(ValueError):self.verify(2,0)
        with self.assertRaises(ValueError):self.event('SERVICE_RECORDED',2,8)
        self.event('STARTED',2)
        for served in [-1,11,True,None,2.5]:
            with self.subTest(served=served),self.assertRaises(ValueError):self.event('SERVICE_RECORDED',3,served)
        self.event('SERVICE_RECORDED',3,8)
        with self.assertRaises(ValueError):self.verify(4,8,verifier='TEST WORKER')
        self.verify(4,8)
        with self.assertRaises(ValueError):self.event('CORRECTION_RECORDED',3,10)
        with self.assertRaises(Conflict):
            self.lab.advance('SYN-RUN',dict(version=1,stage='CORRECTION_RECORDED',at='2026-01-01T05:00:00Z',actor='TEST',served_total=10,evidence='Test'))
        with self.assertRaises(ValueError):self.issue(hour=2)

    def test_cutoff_area_stream_filters_and_scheduled_exclusions(self):
        self.ready();self.verify(4,8);self.schedule('SYN-PENDING')
        self.route('SYN-OTHER','OTHER','RECYCLING',5);self.schedule('SYN-OTHER-RUN','SYN-OTHER')
        r=self.lab.report('2026-01-01T04:30:00Z','DEMO','TRASH')
        self.assertEqual((r['runs'],r['verified_runs'],r['runs_without_service_record']),(2,1,1))
        self.assertEqual(r['verified_expected_stop_visits'],10)
        self.assertIsNone(self.lab.report('2026-01-01T03:30:00Z')['verified_missed_service_rate'])
        self.assertEqual(self.lab.report('2025-12-31T23:00:00Z')['runs'],0)
        self.assertEqual(self.lab.report('2026-01-02T00:00:00Z',stream='RECYCLING')['runs'],1)

    def test_issue_rejects_stale_and_invalid_responses(self):
        self.ready();self.issue()
        with self.assertRaises(Conflict):self.issue()
        with self.assertRaises(ValueError):self.response('OPEN',5)
        with self.assertRaises(ValueError):self.response('RESOLVED',3)
        self.response('RESOLVED',5)
        with self.assertRaises(Conflict):
            self.lab.update_issue('SYN-REPORT',dict(version=1,status='OPEN',at='2026-01-01T06:00:00Z',actor='TEST',evidence='Test'))

    def test_backup_export_and_http_workflow(self):
        self.ready();self.verify(4,8);self.issue()
        backup=Path(self.directory.name)/'backup.sqlite3';self.store.backup(backup)
        restored=Sanitation(Store(backup));self.assertEqual(restored.run('SYN-RUN'),self.lab.run('SYN-RUN'))
        self.assertEqual(restored.issue('SYN-REPORT'),self.lab.issue('SYN-REPORT'))
        self.assertEqual(len(self.store.export()['synthetic_sanitation']['checks']),1)
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base=f'http://127.0.0.1:{app.server_port}'
        with urlopen(base+'/api/sanitation') as response:token=json.load(response)['token']
        payload=dict(version=self.lab.issue('SYN-REPORT')['version'],status='RESOLVED',at='2026-01-01T05:00:00Z',actor='TEST',evidence='Synthetic HTTP response')
        with urlopen(Request(base+'/api/sanitation/issues/SYN-REPORT/events',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Portfolio-Token':token})) as response:self.assertEqual(json.load(response)['status'],'RESOLVED')
        with urlopen(base+'/api/sanitation/report?area=DEMO&stream=TRASH') as response:self.assertEqual(json.load(response)['verified_missed_service_rate'],.2)
        with urlopen(base+'/sanitation') as response:self.assertIn(b'Synthetic sanitation lab',response.read())


if __name__=='__main__':unittest.main()
