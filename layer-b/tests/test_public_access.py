import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen

from civic_portfolio.__main__ import server
from civic_portfolio.public_access import PublicAccess
from civic_portfolio.store import Conflict,Store


class PublicAccessTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.store=Store(Path(self.directory.name)/'test.sqlite3');self.lab=PublicAccess(self.store)

    def create(self,case_id='SYN-CASE',kind='RECORDS_REQUEST',area='AREA',due='2026-01-01T06:00:00Z'):
        return self.lab.create_case(dict(case_id=case_id,kind=kind,area=area,at='2026-01-01T00:00:00Z',due_at=due,actor='TEST',evidence='Synthetic receipt and externally supplied due assertion'))

    def response(self,hour=7,completeness='COMPLETE',case_id='SYN-CASE'):
        return self.lab.respond(case_id,dict(version=self.lab.case(case_id)['version'],at=f'2026-01-01T{hour:02}:00:00Z',sent_at=f'2026-01-01T{hour:02}:00:00Z',completeness=completeness,response_reference='Fictional response label',review_route_reference=None,restriction_reference='Fictional scope note',actor='TEST RECORDER',evidence='Synthetic response scope assertion'))

    def verify(self,hour=8,case_id='SYN-CASE',passed=True,verifier='TEST VERIFIER'):
        return self.lab.verify_response(case_id,dict(version=self.lab.case(case_id)['version'],at=f'2026-01-01T{hour:02}:00:00Z',verifier=verifier,passed=passed,evidence='Synthetic response check'))

    def action(self,action,hour,case_id='SYN-CASE'):
        return self.lab.advance(case_id,dict(version=self.lab.case(case_id)['version'],action=action,at=f'2026-01-01T{hour:02}:00:00Z',actor='TEST',evidence='Synthetic handoff/closure/reopening'))

    def meeting(self,meeting_id='SYN-MEETING',area='AREA'):
        return self.lab.create_meeting(dict(meeting_id=meeting_id,title='Fictional public meeting',area=area,starts_at='2026-01-02T12:00:00Z',at='2026-01-01T00:00:00Z',actor='TEST',evidence='Synthetic meeting schedule'))

    def notice(self,at='2026-01-01T12:00:00Z',published='2026-01-01T12:00:00Z',access='INCOMPLETE',participation=None,agenda=None):
        return self.lab.notice('SYN-MEETING',dict(version=self.lab.meeting('SYN-MEETING')['version'],at=at,published_at=published,accessibility=access,participation_reference=participation,agenda_reference=agenda,actor='TEST RECORDER',evidence='Synthetic notice and access assertion'))

    def notice_check(self,at='2026-01-01T12:00:00Z'):
        return self.lab.verify_notice('SYN-MEETING',dict(version=self.lab.meeting('SYN-MEETING')['version'],at=at,verifier='TEST VERIFIER',passed=True,evidence='Synthetic notice check'))

    def test_unknowns_partial_scope_and_handoffs_do_not_create_success(self):
        r=self.lab.report();self.assertIsNone(r['latest_complete_response_hours']['median'])
        self.create();self.action('HANDOFF',2);self.response(3,'PARTIAL');self.verify(4)
        with self.assertRaises(ValueError):self.action('CLOSED',5)
        r=self.lab.report('2026-01-01T08:00:00Z')
        self.assertEqual((r['requests']['incomplete_current_responses'],r['requests']['checked_complete_responses'],r['requests']['handoff_events']),(1,0,1))
        self.assertEqual(r['unresolved_case_age_hours']['median'],8)
        self.assertEqual(r['requests']['overdue_unresolved_cases'],1)
        self.assertFalse(r['execution_authorized'])

    def test_deadline_snapshot_prevents_same_timestamp_retroactive_rewrite(self):
        self.create();self.response(7)
        self.lab.deadline('SYN-CASE',dict(version=self.lab.case('SYN-CASE')['version'],at='2026-01-01T07:00:00Z',due_at='2026-01-01T10:00:00Z',actor='TEST',evidence='Later deadline assertion at same simulated timestamp'))
        self.verify(8);r=self.lab.report('2026-01-01T09:00:00Z')
        self.assertEqual(r['requests']['responses_assessed_against_recorded_due'],1)
        self.assertEqual(r['requests']['responses_meeting_recorded_due'],0)
        self.assertEqual(self.lab.case('SYN-CASE')['responses'][0]['deadline_sequence'],1)
        self.assertEqual(r['latest_complete_response_hours']['median'],7)

    def test_response_revision_and_reopening_require_current_proof(self):
        self.create();self.response(2,'PARTIAL');self.verify(3)
        self.response(3,'COMPLETE')
        with self.assertRaises(ValueError):self.action('CLOSED',3)
        self.verify(3);self.action('CLOSED',3);self.action('REOPENED',3)
        with self.assertRaises(ValueError):self.action('CLOSED',3)
        r=self.lab.report('2026-01-01T04:00:00Z')
        self.assertEqual(r['requests']['missing_current_responses'],1)
        self.assertEqual(r['requests']['reopen_events'],1)
        self.assertEqual(r['unresolved_case_age_hours']['median'],4)
        self.response(4);self.verify(4);self.action('CLOSED',4)
        self.assertEqual(self.lab.case('SYN-CASE')['status'],'CLOSED')

    def test_meeting_notice_threshold_is_optional_and_revisions_invalidate_checks(self):
        self.meeting();self.notice();self.notice_check()
        r=self.lab.report('2026-01-01T12:30:00Z')
        self.assertIsNone(r['notice_threshold_rate']);self.assertIsNone(r['meeting_notices']['notices_meeting_supplied_threshold'])
        self.assertEqual(r['notice_lead_hours']['median'],24)
        self.assertEqual(r['meeting_notices']['incomplete_or_unknown_participation'],1)
        self.assertEqual(self.lab.report('2026-01-01T12:30:00Z',min_notice_hours=24)['notice_threshold_rate'],1)
        self.notice(at='2026-01-01T13:00:00Z',published='2026-01-01T11:00:00Z',access='AVAILABLE',participation='Fictional accessible participation label',agenda='Fictional agenda label')
        self.assertEqual(self.lab.report('2026-01-01T13:30:00Z')['meeting_notices']['unverified_notices'],1)
        self.notice_check('2026-01-01T14:00:00Z')
        r=self.lab.report('2026-01-01T14:30:00Z',min_notice_hours=25)
        self.assertEqual(r['notice_lead_hours']['median'],25)
        self.assertEqual(r['meeting_notices']['available_participation_assertions'],1)
        self.notice(at='2026-01-02T13:00:00Z',published='2026-01-02T13:00:00Z');self.notice_check('2026-01-02T14:00:00Z')
        self.assertEqual(self.lab.report('2026-01-02T15:00:00Z',min_notice_hours=0)['notice_lead_hours']['median'],-1)

    def test_validation_versions_chronology_and_access_references(self):
        self.create()
        with self.assertRaises(Conflict):self.create()
        with self.assertRaises(ValueError):self.action('REOPENED',1)
        self.response(2)
        with self.assertRaises(ValueError):self.verify(3,verifier='TEST RECORDER')
        self.verify(3)
        with self.assertRaises(ValueError):self.response(2)
        with self.assertRaises(Conflict):
            self.lab.advance('SYN-CASE',dict(version=1,action='CLOSED',at='2026-01-01T04:00:00Z',actor='TEST',evidence='Test'))
        self.meeting()
        with self.assertRaises(ValueError):self.notice(access='AVAILABLE')
        for threshold in [-1,float('nan'),float('inf'),True]:
            with self.subTest(threshold=threshold),self.assertRaises(ValueError):self.lab.report(min_notice_hours=threshold)

    def test_cutoffs_kind_area_filters_and_unknown_deadlines(self):
        self.create();self.create('SYN-COMPLAINT','COMPLAINT','OTHER',None);self.meeting(area='OTHER')
        self.response(7);self.verify(8)
        self.assertEqual(self.lab.report('2026-01-01T07:30:00Z')['requests']['unverified_current_responses'],1)
        r=self.lab.report('2026-01-02T00:00:00Z',area='OTHER',kind='COMPLAINT')
        self.assertEqual((r['requests']['cases'],r['requests']['unknown_current_due_dates'],r['meeting_notices']['meetings']),(1,1,1))
        self.assertEqual(self.lab.report('2025-12-31T23:00:00Z')['requests']['cases'],0)

    def test_backup_export_and_http_workflow(self):
        self.create();self.response(7);self.verify(8);self.meeting();self.notice();self.notice_check()
        backup=Path(self.directory.name)/'backup.sqlite3';self.store.backup(backup)
        restored=PublicAccess(Store(backup));self.assertEqual(restored.case('SYN-CASE'),self.lab.case('SYN-CASE'))
        self.assertEqual(restored.meeting('SYN-MEETING'),self.lab.meeting('SYN-MEETING'))
        self.assertEqual(len(self.store.export()['synthetic_public_access']['notices']),1)
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base=f'http://127.0.0.1:{app.server_port}'
        with urlopen(base+'/api/public-access') as response:token=json.load(response)['token']
        payload=dict(version=self.lab.case('SYN-CASE')['version'],action='CLOSED',at='2026-01-01T09:00:00Z',actor='TEST',evidence='Synthetic closure')
        with urlopen(Request(base+'/api/public-access/cases/SYN-CASE/events',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Portfolio-Token':token})) as response:self.assertEqual(json.load(response)['status'],'CLOSED')
        with urlopen(base+'/api/public-access/report?min_notice_hours=24') as response:self.assertEqual(json.load(response)['notice_threshold_rate'],1)
        with urlopen(base+'/public-access') as response:self.assertIn(b'Synthetic records and meetings lab',response.read())


if __name__=='__main__':unittest.main()
