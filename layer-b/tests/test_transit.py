import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen

from civic_portfolio.__main__ import server
from civic_portfolio.store import Conflict,Store
from civic_portfolio.transit import Transit


class TransitTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.store=Store(Path(self.directory.name)/'test.sqlite3');self.lab=Transit(self.store)

    def trip(self,trip_id='SYN-TRIP',service='DEMO',area='AREA',scheduled='2026-01-01T10:00:00Z'):
        return self.lab.create_trip(dict(trip_id=trip_id,service=service,area=area,scheduled_at=scheduled,at='2026-01-01T00:00:00Z',actor='TEST',evidence='Synthetic schedule'))

    def observe(self,trip_id='SYN-TRIP',actual='2026-01-01T10:05:00Z',result='ARRIVED',at='2026-01-01T11:00:00Z',passengers=None,delay=None):
        return self.lab.observe(trip_id,dict(version=self.lab.trip(trip_id)['version'],result=result,at=at,actual_at=actual,actor='TEST RECORDER',evidence='Synthetic observation/correction',passenger_count=passengers,passenger_delay=delay))

    def verify(self,trip_id='SYN-TRIP',passed=True,at='2026-01-01T12:00:00Z',verifier='TEST VERIFIER'):
        return self.lab.verify(trip_id,dict(version=self.lab.trip(trip_id)['version'],at=at,verifier=verifier,passed=passed,evidence='Synthetic evidence check'))

    def finding(self,finding_id='SYN-FINDING',need='MOBILITY',excluded=2):
        return self.lab.create_finding(dict(finding_id=finding_id,trip_id='SYN-TRIP',access_need=need,description='Fictional non-identifying access barrier',excluded_boardings=excluded,at='2026-01-01T10:10:00Z',actor='TEST',evidence='Synthetic finding'))

    def response(self,status,at):
        return self.lab.update_finding('SYN-FINDING',dict(version=self.lab.finding('SYN-FINDING')['version'],status=status,at=at,actor='TEST',evidence='Synthetic accessibility response'))

    def test_empty_and_unknown_observations_preserve_nulls(self):
        r=self.lab.report('2026-01-02T00:00:00Z');self.assertIsNone(r['on_time_arrival_rate'])
        self.assertIsNone(r['passenger_delay']['total_person_minutes'])
        self.trip();r=self.lab.report('2026-01-02T00:00:00Z')
        self.assertEqual(r['unobserved_due_trips'],1)
        self.assertEqual(r['verification_coverage'],0)
        self.observe();r=self.lab.report('2026-01-02T00:00:00Z')
        self.assertEqual(r['unverified_due_observations'],1);self.assertIsNone(r['on_time_arrival_rate'])
        self.verify();r=self.lab.report('2026-01-02T00:00:00Z')
        self.assertEqual(r['on_time_arrival_rate'],1);self.assertIsNone(r['passenger_delay']['mean_minutes_per_passenger_observation'])
        self.assertFalse(r['execution_authorized'])

    def test_window_boundaries_cancellations_and_denominators(self):
        for identifier,actual in [('SYN-LATE-BOUND','2026-01-01T11:05:00+01:00'),('SYN-EARLY-BOUND','2026-01-01T09:59:00Z'),('SYN-TOO-LATE','2026-01-01T10:06:00Z'),('SYN-TOO-EARLY','2026-01-01T09:58:00Z')]:
            self.trip(identifier);self.observe(identifier,actual=actual);self.verify(identifier)
        self.trip('SYN-CANCEL');self.observe('SYN-CANCEL',actual=None,result='CANCELLED');self.verify('SYN-CANCEL')
        self.trip('SYN-UNKNOWN');self.trip('SYN-UNVERIFIED');self.observe('SYN-UNVERIFIED')
        self.trip('SYN-UPCOMING',scheduled='2026-01-03T10:00:00Z');self.observe('SYN-UPCOMING',actual=None,result='CANCELLED');self.verify('SYN-UPCOMING')
        r=self.lab.report('2026-01-02T00:00:00Z')
        self.assertEqual((r['due_scheduled_trips'],r['upcoming_scheduled_trips'],r['verified_outcomes']),(7,1,5))
        self.assertEqual(r['on_time_arrival_rate'],.5);self.assertEqual(r['verified_cancellations'],1)
        self.assertEqual(r['cancellation_rate_among_verified_outcomes'],.2)
        self.assertEqual(r['verification_coverage'],5/7)
        self.assertEqual(r['arrival_deviation_minutes']['sample_size'],4)
        self.assertEqual(self.lab.report('2026-01-02T00:00:00Z',early_minutes=2,late_minutes=6)['on_time_arrival_rate'],1)

    def test_revisions_invalidate_checks_and_support_earlier_corrected_arrival(self):
        self.trip();self.observe();self.verify()
        self.observe(actual='2026-01-01T09:58:00Z',at='2026-01-01T12:00:00Z')
        self.assertFalse(self.lab.trip('SYN-TRIP')['verified'])
        self.assertIsNone(self.lab.report('2026-01-01T12:00:00Z')['on_time_arrival_rate'])
        self.verify(at='2026-01-01T12:00:00Z');r=self.lab.report('2026-01-02T00:00:00Z')
        self.assertEqual(r['on_time_arrival_rate'],0)
        self.assertEqual(r['arrival_deviation_minutes']['median'],-2)
        self.assertEqual(r['positive_arrival_delay_minutes']['median'],0)
        self.assertEqual(self.lab.report('2026-01-01T11:30:00Z')['verified_outcomes'],0)
        self.verify(passed=False,at='2026-01-01T13:00:00Z')
        self.assertEqual(self.lab.report('2026-01-02T00:00:00Z')['unverified_due_observations'],1)

    def test_passenger_delay_is_measured_not_inferred(self):
        self.trip();self.observe(passengers=2,delay=20);self.verify()
        self.trip('SYN-SECOND');self.observe('SYN-SECOND',actual='2026-01-01T10:00:00Z',passengers=3,delay=15);self.verify('SYN-SECOND')
        self.trip('SYN-MISSING');self.observe('SYN-MISSING',actual=None,result='CANCELLED');self.verify('SYN-MISSING')
        p=self.lab.report('2026-01-02T00:00:00Z')['passenger_delay']
        self.assertEqual(p,dict(outcome_samples=2,missing_verified_outcomes=1,passenger_observations=5,total_person_minutes=35,mean_minutes_per_passenger_observation=7))
        for passengers,delay in [(None,5),(2,None),(True,2),(0,2),(2,-1),(2,float('inf'))]:
            with self.subTest(passengers=passengers,delay=delay),self.assertRaises(ValueError):
                self.observe(at='2026-01-01T13:00:00Z',passengers=passengers,delay=delay)

    def test_access_findings_remain_separate_from_ontime_service(self):
        self.trip();self.observe();self.verify();self.finding();self.finding('SYN-VISUAL','VISUAL',None)
        r=self.lab.report('2026-01-02T00:00:00Z');self.assertEqual(r['on_time_arrival_rate'],1)
        self.assertEqual(r['open_access_findings'],2)
        self.assertEqual(r['access_findings_by_need']['MOBILITY']['reported_excluded_boarding_observations'],2)
        self.assertIsNone(r['access_findings_by_need']['VISUAL']['reported_excluded_boarding_observations'])
        self.response('RESOLVED','2026-01-01T11:10:00Z');self.response('OPEN','2026-01-01T12:10:00Z')
        self.assertEqual(self.lab.report('2026-01-02T00:00:00Z')['reopen_events'],1)
        self.assertEqual(self.lab.report('2026-01-01T11:30:00Z')['access_response_hours']['median'],1)
        self.assertEqual(self.lab.report('2026-01-01T09:00:00Z')['open_access_findings'],0)

    def test_validation_versions_cutoff_and_service_area_filters(self):
        self.trip()
        with self.assertRaises(Conflict):self.trip()
        with self.assertRaises(ValueError):self.verify()
        with self.assertRaises(ValueError):self.observe(actual='2026-01-01T12:00:00Z')
        self.observe();self.verify()
        with self.assertRaises(ValueError):self.verify(verifier='TEST RECORDER')
        with self.assertRaises(ValueError):self.observe(at='2026-01-01T11:00:00Z')
        with self.assertRaises(Conflict):
            self.lab.verify('SYN-TRIP',dict(version=1,at='2026-01-01T13:00:00Z',verifier='TEST',passed=True,evidence='Test'))
        for value in [-1,float('nan'),float('inf'),True]:
            with self.subTest(value=value),self.assertRaises(ValueError):self.lab.report(early_minutes=value)
        self.trip('SYN-OTHER','OTHER','OTHER AREA');self.observe('SYN-OTHER');self.verify('SYN-OTHER')
        self.assertEqual(self.lab.report('2026-01-02T00:00:00Z',service='DEMO',area='AREA')['due_scheduled_trips'],1)
        self.assertEqual(self.lab.report('2025-12-31T23:00:00Z')['due_scheduled_trips'],0)
        self.assertEqual(self.lab.report('2026-01-02T00:00:00Z',service='MISSING')['due_scheduled_trips'],0)

    def test_backup_export_and_http_workflow(self):
        self.trip();self.observe();self.verify();self.finding()
        backup=Path(self.directory.name)/'backup.sqlite3';self.store.backup(backup)
        restored=Transit(Store(backup));self.assertEqual(restored.trip('SYN-TRIP'),self.lab.trip('SYN-TRIP'))
        self.assertEqual(restored.finding('SYN-FINDING'),self.lab.finding('SYN-FINDING'))
        self.assertEqual(len(self.store.export()['synthetic_transit']['checks']),1)
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base=f'http://127.0.0.1:{app.server_port}'
        with urlopen(base+'/api/transit') as response:token=json.load(response)['token']
        payload=dict(version=1,status='RESOLVED',at='2026-01-01T11:10:00Z',actor='TEST',evidence='Synthetic HTTP response')
        with urlopen(Request(base+'/api/transit/findings/SYN-FINDING/events',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Portfolio-Token':token})) as response:self.assertEqual(json.load(response)['status'],'RESOLVED')
        with urlopen(base+'/api/transit/report?service=DEMO&early_minutes=1&late_minutes=5') as response:self.assertEqual(json.load(response)['on_time_arrival_rate'],1)
        with urlopen(base+'/transit') as response:self.assertIn(b'Synthetic transit lab',response.read())


if __name__=='__main__':unittest.main()
