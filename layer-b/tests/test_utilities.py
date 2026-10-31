import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen

from civic_portfolio.__main__ import server
from civic_portfolio.store import Conflict,Store
from civic_portfolio.utilities import Utilities


class UtilityTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.store=Store(Path(self.directory.name)/'test.sqlite3');self.lab=Utilities(self.store)

    def asset(self,asset_id='SYN-UTILITY',utility='WATER',area='DEMO'):
        return self.lab.create_asset(dict(asset_id=asset_id,utility=utility,area=area,connection_count=20,at='2026-01-01T00:00:00Z',actor='TEST',evidence='Synthetic utility asset'))

    def create(self,incident_id='SYN-OUTAGE',asset_id='SYN-UTILITY',affected=10):
        return self.lab.create_incident(dict(incident_id=incident_id,asset_id=asset_id,started_at='2026-01-01T01:00:00Z',at='2026-01-01T02:00:00Z',affected_connections=affected,severity='SAFETY_REVIEW',escalation_reference=None,actor='TEST RECORDER',evidence='Synthetic interruption; initial count asserted from start'))

    def event(self,stage,hour,affected,incident_id='SYN-OUTAGE'):
        return self.lab.advance(incident_id,dict(version=self.lab.incident(incident_id)['version'],stage=stage,at=f'2026-01-01T{hour:02}:00:00Z',affected_connections=affected,work_order_reference='Fictional work-order label' if stage=='WORK_IN_PROGRESS' else None,escalation_reference='Fictional responsible process label' if stage=='ASSESSED' else None,actor='TEST RECORDER',evidence='Synthetic stage and count evidence'))

    def check(self,hour=7,quality='MEETS_SCENARIO',passed=True,verifier='TEST VERIFIER'):
        return self.lab.verify('SYN-OUTAGE',dict(version=self.lab.incident('SYN-OUTAGE')['version'],at=f'2026-01-01T{hour:02}:00:00Z',verifier=verifier,passed=passed,quality_status=quality,criteria_reference='SYNTHETIC CRITERIA ONLY',evidence='Synthetic quality-evidence record'))

    def ready(self,affected=10):
        self.asset();self.create(affected=affected);self.event('ASSESSED',3,8);self.event('WORK_IN_PROGRESS',4,8);self.event('RESTORATION_RECORDED',6,0)

    def test_no_baseline_and_unknown_quality_do_not_create_verified_restoration(self):
        self.assertIsNone(self.lab.report()['checked_restoration_cycle_hours']['median'])
        self.ready()
        with self.assertRaises(ValueError):self.event('CLOSED',7,0)
        self.check(7,'UNKNOWN')
        with self.assertRaises(ValueError):self.event('CLOSED',8,0)
        self.check(8,'DOES_NOT_MEET')
        with self.assertRaises(ValueError):self.event('CLOSED',9,0)
        self.check(9);self.event('CLOSED',10,0)
        r=self.lab.report('2026-01-01T11:00:00Z')
        self.assertEqual(r['failed_or_unknown_quality_checks'],2)
        self.assertEqual(r['checked_restoration_cycle_hours']['median'],5)
        self.assertEqual(r['quality_verification_lag_hours']['median'],3)
        self.assertFalse(r['execution_authorized'])

    def test_connection_hours_cycles_and_reopening_preserve_context(self):
        self.ready();self.check();self.event('CLOSED',8,0)
        r=self.lab.report('2026-01-01T09:00:00Z')
        self.assertEqual(r['reported_incident_connection_hours'],44)
        self.assertEqual(r['checked_restoration_cycle_hours']['median'],5)
        self.event('REOPENED',10,5);r=self.lab.report('2026-01-01T12:00:00Z')
        self.assertEqual((r['open_incidents'],r['closed_incidents'],r['closed_restoration_cycles'],r['reopen_events']),(1,0,1,1))
        self.assertEqual(r['open_cycle_age_hours']['median'],2)
        self.assertEqual(r['open_incident_original_age_hours']['median'],11)
        self.assertEqual(r['reported_incident_connection_hours'],54)
        self.assertEqual(self.lab.report('2026-01-01T09:00:00Z')['closed_incidents'],1)

    def test_unknown_intervals_block_complete_burden_and_escalation_gaps_are_explicit(self):
        self.ready(affected=None)
        r=self.lab.report('2026-01-01T07:00:00Z')
        self.assertIsNone(r['reported_incident_connection_hours'])
        self.assertEqual(r['unknown_burden_intervals'],1)
        self.assertEqual(r['known_interval_connection_hours'],24)
        self.assertEqual(r['unclosed_restoration_records'],1)
        self.assertEqual(self.lab.report('2026-01-01T02:30:00Z')['missing_safety_escalation_references'],1)
        self.assertEqual(r['missing_safety_escalation_references'],0)

    def test_old_check_cannot_close_a_new_cycle_even_with_equal_timestamps(self):
        self.ready();self.check(6);self.event('CLOSED',6,0);self.event('REOPENED',6,5)
        self.event('ASSESSED',6,5);self.event('WORK_IN_PROGRESS',6,5);self.event('RESTORATION_RECORDED',6,0)
        with self.assertRaises(ValueError):self.event('CLOSED',6,0)
        self.check(6);self.event('CLOSED',6,0)
        self.assertEqual(self.lab.report('2026-01-01T07:00:00Z')['closed_restoration_cycles'],2)

    def test_counts_versions_chronology_and_distinct_verifier(self):
        self.asset()
        with self.assertRaises(Conflict):self.asset()
        with self.assertRaises(KeyError):self.create(asset_id='SYN-MISSING')
        for affected in [-1,21,True,2.5]:
            with self.subTest(affected=affected),self.assertRaises(ValueError):self.create(affected=affected)
        self.create()
        with self.assertRaises(Conflict):self.create()
        with self.assertRaises(ValueError):self.event('RESTORATION_RECORDED',3,0)
        with self.assertRaises(ValueError):self.event('ASSESSED',1,8)
        self.event('ASSESSED',3,8);self.event('WORK_IN_PROGRESS',4,8)
        with self.assertRaises(ValueError):self.event('RESTORATION_RECORDED',5,None)
        self.event('RESTORATION_RECORDED',6,0)
        with self.assertRaises(ValueError):self.check(7,verifier='TEST RECORDER')
        self.check()
        with self.assertRaises(ValueError):self.event('WORK_IN_PROGRESS',6,5)
        with self.assertRaises(Conflict):
            self.lab.verify('SYN-OUTAGE',dict(version=1,at='2026-01-01T08:00:00Z',verifier='TEST',passed=True,quality_status='MEETS_SCENARIO',criteria_reference='Test',evidence='Test'))

    def test_cutoff_area_utility_filters_and_overlapping_incidents_are_not_deduplicated(self):
        self.asset();self.create();self.create('SYN-OVERLAP')
        self.asset('SYN-POWER','POWER','OTHER');self.create('SYN-POWER-OUTAGE','SYN-POWER')
        r=self.lab.report('2026-01-01T03:00:00Z','DEMO','WATER')
        self.assertEqual((r['assets'],r['incidents']),(1,2))
        self.assertEqual(r['reported_incident_connection_hours'],40)
        self.assertEqual(self.lab.report('2026-01-01T01:30:00Z')['incidents'],0)
        self.assertEqual(self.lab.report('2025-12-31T23:00:00Z')['assets'],0)
        self.assertEqual(self.lab.report('2026-01-01T03:00:00Z',utility='POWER')['incidents'],1)

    def test_backup_export_and_http_workflow(self):
        self.ready();self.check()
        backup=Path(self.directory.name)/'backup.sqlite3';self.store.backup(backup)
        restored=Utilities(Store(backup));self.assertEqual(restored.incident('SYN-OUTAGE'),self.lab.incident('SYN-OUTAGE'))
        self.assertEqual(len(self.store.export()['synthetic_utilities']['checks']),1)
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base=f'http://127.0.0.1:{app.server_port}'
        with urlopen(base+'/api/utilities') as response:token=json.load(response)['token']
        payload=dict(version=self.lab.incident('SYN-OUTAGE')['version'],stage='CLOSED',at='2026-01-01T08:00:00Z',affected_connections=0,work_order_reference=None,escalation_reference=None,actor='TEST',evidence='Synthetic HTTP closure')
        with urlopen(Request(base+'/api/utilities/incidents/SYN-OUTAGE/events',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Portfolio-Token':token})) as response:self.assertEqual(json.load(response)['stage'],'CLOSED')
        with urlopen(base+'/api/utilities/report?area=DEMO&utility=WATER') as response:self.assertEqual(json.load(response)['checked_restoration_cycle_hours']['median'],5)
        with urlopen(base+'/utilities') as response:self.assertIn(b'Synthetic utilities continuity lab',response.read())


if __name__=='__main__':unittest.main()
