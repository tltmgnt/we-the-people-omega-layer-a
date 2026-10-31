"""SQLite portfolio, immutable source versions and attributable work records.

Recorded reviewers and evidence are user assertions, not authenticated approval.
This application does not grant authority to operate public services.
"""
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from scripts.build_implementation_plans import build

ROOT = Path(__file__).resolve().parents[1]
MAX_TEXT = 1_000_000


class Conflict(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def text(value, name, limit=10000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'{name} must be nonblank text of at most {limit} characters')
    return value.strip()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS projects (
                  id TEXT PRIMARY KEY, body TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS sources (
                  id TEXT PRIMARY KEY, project_id TEXT, url TEXT);
                CREATE TABLE IF NOT EXISTS snapshots (
                  source_id TEXT NOT NULL REFERENCES sources(id), revision INTEGER NOT NULL,
                  content TEXT NOT NULL, sha256 TEXT NOT NULL, actor TEXT NOT NULL,
                  imported_at TEXT NOT NULL, origin TEXT NOT NULL,
                  reviewer TEXT, reviewed_at TEXT, PRIMARY KEY(source_id, revision));
                CREATE TABLE IF NOT EXISTS audit (
                  sequence INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL,
                  actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL,
                  detail TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS permit_cases (
                  id TEXT PRIMARY KEY, category TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS permit_events (
                  case_id TEXT NOT NULL REFERENCES permit_cases(id), sequence INTEGER NOT NULL,
                  stage TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL,
                  evidence TEXT NOT NULL, staff_hours REAL, public_hours REAL,
                  PRIMARY KEY(case_id,sequence));
                CREATE TABLE IF NOT EXISTS permit_quality (
                  case_id TEXT NOT NULL REFERENCES permit_cases(id), sequence INTEGER NOT NULL,
                  at TEXT NOT NULL, reviewer TEXT NOT NULL, passed INTEGER NOT NULL,
                  evidence TEXT NOT NULL, PRIMARY KEY(case_id,sequence));
                CREATE TABLE IF NOT EXISTS maintenance_assets (
                  id TEXT PRIMARY KEY, category TEXT NOT NULL, area TEXT NOT NULL,
                  registered_at TEXT NOT NULL, actor TEXT NOT NULL, evidence TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS maintenance_orders (
                  id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES maintenance_assets(id),
                  condition TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS maintenance_events (
                  order_id TEXT NOT NULL REFERENCES maintenance_orders(id), sequence INTEGER NOT NULL,
                  stage TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL, evidence TEXT NOT NULL,
                  priority TEXT, team TEXT, PRIMARY KEY(order_id,sequence));
                CREATE TABLE IF NOT EXISTS maintenance_checks (
                  order_id TEXT NOT NULL REFERENCES maintenance_orders(id), sequence INTEGER NOT NULL,
                  event_sequence INTEGER NOT NULL,
                  at TEXT NOT NULL, verifier TEXT NOT NULL, passed INTEGER NOT NULL,
                  evidence TEXT NOT NULL, PRIMARY KEY(order_id,sequence));
                CREATE TABLE IF NOT EXISTS sanitation_routes (
                  id TEXT PRIMARY KEY, stream TEXT NOT NULL, area TEXT NOT NULL,
                  expected_stops INTEGER NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL, evidence TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sanitation_runs (
                  id TEXT PRIMARY KEY, route_id TEXT NOT NULL REFERENCES sanitation_routes(id),
                  expected_stops INTEGER NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS sanitation_events (
                  run_id TEXT NOT NULL REFERENCES sanitation_runs(id), sequence INTEGER NOT NULL,
                  stage TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL,
                  served_total INTEGER, evidence TEXT NOT NULL, PRIMARY KEY(run_id,sequence));
                CREATE TABLE IF NOT EXISTS sanitation_checks (
                  run_id TEXT NOT NULL REFERENCES sanitation_runs(id), sequence INTEGER NOT NULL,
                  event_sequence INTEGER NOT NULL, at TEXT NOT NULL, verifier TEXT NOT NULL,
                  observed_total INTEGER NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(run_id,sequence));
                CREATE TABLE IF NOT EXISTS sanitation_issues (
                  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES sanitation_runs(id),
                  description TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS sanitation_issue_events (
                  issue_id TEXT NOT NULL REFERENCES sanitation_issues(id), sequence INTEGER NOT NULL,
                  status TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL,
                  evidence TEXT NOT NULL, PRIMARY KEY(issue_id,sequence));
                CREATE TABLE IF NOT EXISTS transit_trips (
                  id TEXT PRIMARY KEY, service TEXT NOT NULL, area TEXT NOT NULL,
                  scheduled_at TEXT NOT NULL, registered_at TEXT NOT NULL,
                  actor TEXT NOT NULL, evidence TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS transit_observations (
                  trip_id TEXT NOT NULL REFERENCES transit_trips(id), sequence INTEGER NOT NULL,
                  result TEXT NOT NULL, at TEXT NOT NULL, actual_at TEXT,
                  actor TEXT NOT NULL, evidence TEXT NOT NULL, passenger_count INTEGER,
                  passenger_delay REAL, PRIMARY KEY(trip_id,sequence));
                CREATE TABLE IF NOT EXISTS transit_checks (
                  trip_id TEXT NOT NULL REFERENCES transit_trips(id), sequence INTEGER NOT NULL,
                  observation_sequence INTEGER NOT NULL, at TEXT NOT NULL, verifier TEXT NOT NULL,
                  passed INTEGER NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(trip_id,sequence));
                CREATE TABLE IF NOT EXISTS transit_findings (
                  id TEXT PRIMARY KEY, trip_id TEXT NOT NULL REFERENCES transit_trips(id),
                  access_need TEXT NOT NULL, description TEXT NOT NULL,
                  excluded_boardings INTEGER, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS transit_finding_events (
                  finding_id TEXT NOT NULL REFERENCES transit_findings(id), sequence INTEGER NOT NULL,
                  status TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL,
                  evidence TEXT NOT NULL, PRIMARY KEY(finding_id,sequence));
                CREATE TABLE IF NOT EXISTS housing_cases (
                  id TEXT PRIMARY KEY, program TEXT NOT NULL, area TEXT NOT NULL,
                  notice_reference TEXT, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS housing_events (
                  case_id TEXT NOT NULL REFERENCES housing_cases(id), sequence INTEGER NOT NULL,
                  stage TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL,
                  evidence TEXT NOT NULL, continuity TEXT, follow_up_due_at TEXT,
                  PRIMARY KEY(case_id,sequence));
                CREATE TABLE IF NOT EXISTS housing_consents (
                  case_id TEXT NOT NULL REFERENCES housing_cases(id), sequence INTEGER NOT NULL,
                  status TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL,
                  evidence TEXT NOT NULL, PRIMARY KEY(case_id,sequence));
                CREATE TABLE IF NOT EXISTS housing_checks (
                  case_id TEXT NOT NULL REFERENCES housing_cases(id), sequence INTEGER NOT NULL,
                  event_sequence INTEGER NOT NULL, at TEXT NOT NULL, verifier TEXT NOT NULL,
                  passed INTEGER NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(case_id,sequence));
                CREATE TABLE IF NOT EXISTS housing_requests (
                  id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES housing_cases(id),
                  description TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS housing_request_events (
                  request_id TEXT NOT NULL REFERENCES housing_requests(id), sequence INTEGER NOT NULL,
                  status TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL,
                  evidence TEXT NOT NULL, PRIMARY KEY(request_id,sequence));
                CREATE TABLE IF NOT EXISTS public_cases (
                  id TEXT PRIMARY KEY, kind TEXT NOT NULL, area TEXT NOT NULL,
                  generation INTEGER NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS public_case_events (
                  case_id TEXT NOT NULL REFERENCES public_cases(id), sequence INTEGER NOT NULL,
                  action TEXT NOT NULL, generation INTEGER NOT NULL, at TEXT NOT NULL,
                  actor TEXT NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(case_id,sequence));
                CREATE TABLE IF NOT EXISTS public_deadlines (
                  case_id TEXT NOT NULL REFERENCES public_cases(id), sequence INTEGER NOT NULL,
                  at TEXT NOT NULL, due_at TEXT, actor TEXT NOT NULL, evidence TEXT NOT NULL,
                  PRIMARY KEY(case_id,sequence));
                CREATE TABLE IF NOT EXISTS public_responses (
                  case_id TEXT NOT NULL REFERENCES public_cases(id), sequence INTEGER NOT NULL,
                  generation INTEGER NOT NULL, deadline_sequence INTEGER, at TEXT NOT NULL, sent_at TEXT NOT NULL,
                  completeness TEXT NOT NULL, response_reference TEXT NOT NULL,
                  review_route_reference TEXT, restriction_reference TEXT,
                  actor TEXT NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(case_id,sequence));
                CREATE TABLE IF NOT EXISTS public_response_checks (
                  case_id TEXT NOT NULL REFERENCES public_cases(id), sequence INTEGER NOT NULL,
                  response_sequence INTEGER NOT NULL, at TEXT NOT NULL, verifier TEXT NOT NULL,
                  passed INTEGER NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(case_id,sequence));
                CREATE TABLE IF NOT EXISTS public_meetings (
                  id TEXT PRIMARY KEY, title TEXT NOT NULL, area TEXT NOT NULL,
                  starts_at TEXT NOT NULL, registered_at TEXT NOT NULL,
                  actor TEXT NOT NULL, evidence TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS public_notices (
                  meeting_id TEXT NOT NULL REFERENCES public_meetings(id), sequence INTEGER NOT NULL,
                  at TEXT NOT NULL, published_at TEXT NOT NULL, accessibility TEXT NOT NULL,
                  participation_reference TEXT, agenda_reference TEXT, actor TEXT NOT NULL,
                  evidence TEXT NOT NULL, PRIMARY KEY(meeting_id,sequence));
                CREATE TABLE IF NOT EXISTS public_notice_checks (
                  meeting_id TEXT NOT NULL REFERENCES public_meetings(id), sequence INTEGER NOT NULL,
                  notice_sequence INTEGER NOT NULL, at TEXT NOT NULL, verifier TEXT NOT NULL,
                  passed INTEGER NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(meeting_id,sequence));
                CREATE TABLE IF NOT EXISTS utility_assets (
                  id TEXT PRIMARY KEY, utility TEXT NOT NULL, area TEXT NOT NULL,
                  connection_count INTEGER, registered_at TEXT NOT NULL,
                  actor TEXT NOT NULL, evidence TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS utility_incidents (
                  id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES utility_assets(id),
                  started_at TEXT NOT NULL, severity TEXT NOT NULL, escalation_reference TEXT,
                  version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS utility_events (
                  incident_id TEXT NOT NULL REFERENCES utility_incidents(id), sequence INTEGER NOT NULL,
                  stage TEXT NOT NULL, at TEXT NOT NULL, affected_connections INTEGER,
                  work_order_reference TEXT, escalation_reference TEXT, actor TEXT NOT NULL, evidence TEXT NOT NULL,
                  PRIMARY KEY(incident_id,sequence));
                CREATE TABLE IF NOT EXISTS utility_checks (
                  incident_id TEXT NOT NULL REFERENCES utility_incidents(id), sequence INTEGER NOT NULL,
                  restoration_sequence INTEGER NOT NULL, at TEXT NOT NULL, verifier TEXT NOT NULL,
                  passed INTEGER NOT NULL, quality_status TEXT NOT NULL, criteria_reference TEXT NOT NULL,
                  evidence TEXT NOT NULL, PRIMARY KEY(incident_id,sequence));
                CREATE TABLE IF NOT EXISTS rights_cases (
                  id TEXT PRIMARY KEY, proposal_id TEXT NOT NULL, summary TEXT NOT NULL,
                  institution TEXT NOT NULL, jurisdiction TEXT NOT NULL,
                  created_at TEXT NOT NULL, last_at TEXT NOT NULL, actor TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS rights_screenings (
                  case_id TEXT NOT NULL REFERENCES rights_cases(id), sequence INTEGER NOT NULL,
                  domain TEXT NOT NULL, relevance TEXT NOT NULL, rationale TEXT,
                  evidence_pins TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL,
                  PRIMARY KEY(case_id,sequence));
                CREATE TABLE IF NOT EXISTS rights_evidence (
                  case_id TEXT NOT NULL REFERENCES rights_cases(id), evidence_id TEXT NOT NULL,
                  revision INTEGER NOT NULL, sha256 TEXT NOT NULL, content TEXT NOT NULL,
                  origin TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL,
                  PRIMARY KEY(case_id,evidence_id,revision));
                CREATE TABLE IF NOT EXISTS rights_authorities (
                  case_id TEXT NOT NULL REFERENCES rights_cases(id), authority_id TEXT NOT NULL,
                  reference TEXT NOT NULL, proposed_scope TEXT NOT NULL, source_date TEXT,
                  at TEXT NOT NULL, actor TEXT NOT NULL, PRIMARY KEY(case_id,authority_id));
                CREATE TABLE IF NOT EXISTS rights_questions (
                  id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES rights_cases(id),
                  domain TEXT NOT NULL, question TEXT NOT NULL, alternative_explanation TEXT NOT NULL,
                  limitations TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS rights_question_events (
                  question_id TEXT NOT NULL REFERENCES rights_questions(id), sequence INTEGER NOT NULL,
                  status TEXT NOT NULL, evidence_pins TEXT NOT NULL, at TEXT NOT NULL,
                  actor TEXT NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(question_id,sequence));
                CREATE TABLE IF NOT EXISTS initiative_programs (id TEXT PRIMARY KEY,body TEXT NOT NULL,version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS initiative_events (
                  program_id TEXT NOT NULL REFERENCES initiative_programs(id),sequence INTEGER NOT NULL,body TEXT NOT NULL,PRIMARY KEY(program_id,sequence));
                CREATE TABLE IF NOT EXISTS justice_pilots (
                  id TEXT PRIMARY KEY,body TEXT NOT NULL,version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS justice_events (
                  pilot_id TEXT NOT NULL REFERENCES justice_pilots(id),sequence INTEGER NOT NULL,body TEXT NOT NULL,
                  PRIMARY KEY(pilot_id,sequence));
                CREATE TABLE IF NOT EXISTS finance_ledgers (
                  id TEXT PRIMARY KEY,label TEXT NOT NULL,currency TEXT NOT NULL,minor_unit_digits INTEGER NOT NULL,
                  period TEXT NOT NULL,basis TEXT NOT NULL,created_at TEXT NOT NULL,last_at TEXT NOT NULL,actor TEXT NOT NULL,version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS finance_events (
                  ledger_id TEXT NOT NULL REFERENCES finance_ledgers(id),sequence INTEGER NOT NULL,body TEXT NOT NULL,
                  PRIMARY KEY(ledger_id,sequence));
                CREATE TABLE IF NOT EXISTS election_sessions (
                  id TEXT PRIMARY KEY, label TEXT NOT NULL, area TEXT NOT NULL, channel TEXT NOT NULL,
                  opens_at TEXT NOT NULL, closes_at TEXT NOT NULL, registered_at TEXT NOT NULL,
                  last_at TEXT NOT NULL, actor TEXT NOT NULL, report_reference TEXT, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS election_readiness (
                  session_id TEXT NOT NULL REFERENCES election_sessions(id), sequence INTEGER NOT NULL,
                  item TEXT NOT NULL, status TEXT NOT NULL, criteria_reference TEXT,
                  evidence TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL,
                  PRIMARY KEY(session_id,sequence));
                CREATE TABLE IF NOT EXISTS election_readiness_checks (
                  session_id TEXT NOT NULL REFERENCES election_sessions(id), sequence INTEGER NOT NULL,
                  readiness_sequence INTEGER NOT NULL, at TEXT NOT NULL, verifier TEXT NOT NULL,
                  passed INTEGER NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(session_id,sequence));
                CREATE TABLE IF NOT EXISTS election_access_observations (
                  id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES election_sessions(id),
                  barrier TEXT NOT NULL, description TEXT NOT NULL, affected_observations INTEGER,
                  at TEXT NOT NULL, actor TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS election_observation_events (
                  observation_id TEXT NOT NULL REFERENCES election_access_observations(id), sequence INTEGER NOT NULL,
                  status TEXT NOT NULL, correction_reference TEXT, at TEXT NOT NULL,
                  actor TEXT NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(observation_id,sequence));
                CREATE TABLE IF NOT EXISTS election_correction_checks (
                  observation_id TEXT NOT NULL REFERENCES election_access_observations(id), sequence INTEGER NOT NULL,
                  correction_sequence INTEGER NOT NULL, at TEXT NOT NULL, verifier TEXT NOT NULL,
                  passed INTEGER NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(observation_id,sequence));
            ''')
            register = json.loads((ROOT / 'portfolio/project-register.json').read_text())
            plans = build()[1]
            for item in register['projects']:
                identifier = item['project_id']
                body = {**item, 'owner': '', 'scope': '', 'scope_confirmed': False,
                        'plan': plans[identifier], 'tasks': {step['id']: {
                            'done': False, 'evidence': '', 'actor': '', 'at': ''
                        } for step in plans[identifier]['steps']}}
                db.execute('INSERT OR IGNORE INTO projects VALUES (?, ?, 1)',
                           (identifier, json.dumps(body)))
                db.execute('INSERT OR IGNORE INTO sources VALUES (?, ?, ?)',
                           ('project-' + identifier, identifier, item['source_url']))
            for category, entries in [
                ('foundation', {str(i+1): u for i, u in enumerate(register['unassigned_foundational_sources'])}),
                ('layer', register['layer_sources']), ('additional', register['additional_sources'])
            ]:
                for key, url in entries.items():
                    db.execute('INSERT OR IGNORE INTO sources VALUES (?, NULL, ?)',
                               (category + '-' + key.lower(), url))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def log(self, db, actor, action, target, detail):
        db.execute('INSERT INTO audit(at,actor,action,target,detail) VALUES (?,?,?,?,?)',
                   (now(), actor, action, target, json.dumps(detail)))

    def sources(self, db=None):
        if db is None:
            with self.connect() as connection:
                return self.sources(connection)
        rows = db.execute('''SELECT s.*, n.revision, n.sha256, n.actor,
                  n.imported_at, n.origin, n.reviewer, n.reviewed_at,
                  length(n.content) AS characters FROM sources s LEFT JOIN snapshots n
                  ON n.source_id=s.id AND n.revision=(SELECT MAX(revision) FROM snapshots
                  WHERE source_id=s.id) ORDER BY s.id''').fetchall()
        return [dict(row) for row in rows]

    def project(self, identifier, db=None):
        if db is None:
            with self.connect() as connection:
                return self.project(identifier, connection)
        row = db.execute('SELECT * FROM projects WHERE id=?', (identifier,)).fetchone()
        if row is None:
            raise KeyError('project not found')
        result = json.loads(row['body'])
        result['version'] = row['version']
        source = next(s for s in self.sources(db) if s['id'] == 'project-' + identifier)
        blockers = []
        if not result['title']:
            blockers.append('Project title is undefined')
        if not result['scope_confirmed'] or not result['scope']:
            blockers.append('Scope needs confirmation against source requirements')
        if not result['owner']:
            blockers.append('Accountable owner is missing')
        if source['revision'] is None:
            blockers.append('Source document has not been imported')
        elif not source['reviewer']:
            blockers.append('Current source version has not been reviewed')
        pending = sum(not t['done'] for t in result['tasks'].values())
        if pending:
            blockers.append(f'{pending} implementation steps lack completion evidence')
        result['blockers'] = blockers
        result['completed_steps'] = len(result['tasks']) - pending
        result['total_steps'] = len(result['tasks'])
        result['status'] = 'COMPLETE_AS_RECORDED' if not blockers else (
            'IN_PROGRESS' if result['completed_steps'] else 'NEEDS_DEFINITION' if not result['title'] else 'PLANNED')
        result['source'] = source
        result['execution_authorized'] = False
        return result

    def export(self):
        with self.connect() as db:
            projects = [self.project(r['id'], db) for r in db.execute('SELECT id FROM projects ORDER BY id')]
            return {'format_version': '1.0', 'exported_at': now(), 'projects': projects,
                    'sources': self.sources(db), 'snapshots': [dict(r) for r in db.execute(
                        'SELECT * FROM snapshots ORDER BY source_id, revision')],
                    'audit': [dict(r) for r in db.execute('SELECT * FROM audit ORDER BY sequence')],
                    'synthetic_permits': {
                        'cases': [dict(r) for r in db.execute('SELECT * FROM permit_cases ORDER BY id')],
                        'events': [dict(r) for r in db.execute('SELECT * FROM permit_events ORDER BY case_id,sequence')],
                        'quality': [dict(r) for r in db.execute('SELECT * FROM permit_quality ORDER BY case_id,sequence')]},
                    'synthetic_maintenance': {
                        'assets': [dict(r) for r in db.execute('SELECT * FROM maintenance_assets ORDER BY id')],
                        'orders': [dict(r) for r in db.execute('SELECT * FROM maintenance_orders ORDER BY id')],
                        'events': [dict(r) for r in db.execute('SELECT * FROM maintenance_events ORDER BY order_id,sequence')],
                        'checks': [dict(r) for r in db.execute('SELECT * FROM maintenance_checks ORDER BY order_id,sequence')]},
                    'synthetic_sanitation': {
                        'routes': [dict(r) for r in db.execute('SELECT * FROM sanitation_routes ORDER BY id')],
                        'runs': [dict(r) for r in db.execute('SELECT * FROM sanitation_runs ORDER BY id')],
                        'events': [dict(r) for r in db.execute('SELECT * FROM sanitation_events ORDER BY run_id,sequence')],
                        'checks': [dict(r) for r in db.execute('SELECT * FROM sanitation_checks ORDER BY run_id,sequence')],
                        'issues': [dict(r) for r in db.execute('SELECT * FROM sanitation_issues ORDER BY id')],
                        'issue_events': [dict(r) for r in db.execute('SELECT * FROM sanitation_issue_events ORDER BY issue_id,sequence')]},
                    'synthetic_transit': {
                        'trips': [dict(r) for r in db.execute('SELECT * FROM transit_trips ORDER BY id')],
                        'observations': [dict(r) for r in db.execute('SELECT * FROM transit_observations ORDER BY trip_id,sequence')],
                        'checks': [dict(r) for r in db.execute('SELECT * FROM transit_checks ORDER BY trip_id,sequence')],
                        'findings': [dict(r) for r in db.execute('SELECT * FROM transit_findings ORDER BY id')],
                        'finding_events': [dict(r) for r in db.execute('SELECT * FROM transit_finding_events ORDER BY finding_id,sequence')]},
                    'synthetic_housing': {
                        'cases': [dict(r) for r in db.execute('SELECT * FROM housing_cases ORDER BY id')],
                        'events': [dict(r) for r in db.execute('SELECT * FROM housing_events ORDER BY case_id,sequence')],
                        'consents': [dict(r) for r in db.execute('SELECT * FROM housing_consents ORDER BY case_id,sequence')],
                        'checks': [dict(r) for r in db.execute('SELECT * FROM housing_checks ORDER BY case_id,sequence')],
                        'requests': [dict(r) for r in db.execute('SELECT * FROM housing_requests ORDER BY id')],
                        'request_events': [dict(r) for r in db.execute('SELECT * FROM housing_request_events ORDER BY request_id,sequence')]},
                    'synthetic_public_access': {
                        name: [dict(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY '+order)]
                        for name,table,order in [
                            ('cases','public_cases','id'),('case_events','public_case_events','case_id,sequence'),
                            ('deadlines','public_deadlines','case_id,sequence'),('responses','public_responses','case_id,sequence'),
                            ('response_checks','public_response_checks','case_id,sequence'),('meetings','public_meetings','id'),
                            ('notices','public_notices','meeting_id,sequence'),('notice_checks','public_notice_checks','meeting_id,sequence')]},
                    'synthetic_utilities': {
                        'assets': [dict(r) for r in db.execute('SELECT * FROM utility_assets ORDER BY id')],
                        'incidents': [dict(r) for r in db.execute('SELECT * FROM utility_incidents ORDER BY id')],
                        'events': [dict(r) for r in db.execute('SELECT * FROM utility_events ORDER BY incident_id,sequence')],
                        'checks': [dict(r) for r in db.execute('SELECT * FROM utility_checks ORDER BY incident_id,sequence')]},
                    'synthetic_rights': {
                        name: [dict(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY '+order)]
                        for name,table,order in [
                            ('cases','rights_cases','id'),('screenings','rights_screenings','case_id,sequence'),
                            ('evidence','rights_evidence','case_id,evidence_id,revision'),('candidate_authorities','rights_authorities','case_id,authority_id'),
                            ('questions','rights_questions','id'),('question_events','rights_question_events','question_id,sequence')]},
                    'synthetic_initiative': {'programs':[dict(r) for r in db.execute('SELECT * FROM initiative_programs ORDER BY id')], 'events':[dict(r) for r in db.execute('SELECT * FROM initiative_events ORDER BY program_id,sequence')]},
                    'synthetic_justice': {'pilots':[dict(r) for r in db.execute('SELECT * FROM justice_pilots ORDER BY id')], 'events':[dict(r) for r in db.execute('SELECT * FROM justice_events ORDER BY pilot_id,sequence')]},
                    'synthetic_finance': {'ledgers':[dict(r) for r in db.execute('SELECT * FROM finance_ledgers ORDER BY id')], 'events':[dict(r) for r in db.execute('SELECT * FROM finance_events ORDER BY ledger_id,sequence')]},
                    'synthetic_election_services': {
                        name: [dict(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY '+order)]
                        for name,table,order in [
                            ('sessions','election_sessions','id'),('readiness','election_readiness','session_id,sequence'),
                            ('readiness_checks','election_readiness_checks','session_id,sequence'),
                            ('access_observations','election_access_observations','id'),
                            ('observation_events','election_observation_events','observation_id,sequence'),
                            ('correction_checks','election_correction_checks','observation_id,sequence')]},
                    'notice': 'Local user assertions; completion does not authorize public-service execution.'}

    def update(self, identifier, data):
        allowed = {'version', 'actor', 'title', 'owner', 'scope', 'scope_confirmed', 'task'}
        if not isinstance(data, dict) or set(data) - allowed:
            raise ValueError('unknown project fields')
        actor = text(data.get('actor'), 'actor', 200)
        if type(data.get('version')) is not int:
            raise ValueError('integer version is required')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM projects WHERE id=?', (identifier,)).fetchone()
            if not row:
                raise KeyError('project not found')
            if row['version'] != data['version']:
                raise Conflict('Project changed. Reload before saving.')
            body = json.loads(row['body'])
            for field in ['title', 'owner', 'scope']:
                if field in data:
                    body[field] = text(data[field], field)
            if 'scope_confirmed' in data:
                if type(data['scope_confirmed']) is not bool:
                    raise ValueError('scope_confirmed must be boolean')
                body['scope_confirmed'] = data['scope_confirmed']
            if 'task' in data:
                task = data['task']
                if not isinstance(task, dict) or set(task) != {'id', 'done', 'evidence'}:
                    raise ValueError('task needs id, done and evidence')
                if not isinstance(task['id'], str) or task['id'] not in body['tasks'] or type(task['done']) is not bool:
                    raise ValueError('invalid task')
                evidence = text(task['evidence'], 'completion evidence') if task['done'] else ''
                body['tasks'][task['id']] = {'done': task['done'], 'evidence': evidence,
                                              'actor': actor, 'at': now()}
            # Changes to requirements invalidate downstream work assertions.
            if any(field in data and data[field] != json.loads(row['body'])[field]
                   for field in ['title', 'scope']):
                for task in body['tasks'].values():
                    task.update(done=False, evidence='', actor='', at='')
                body['scope_confirmed'] = False
            db.execute('UPDATE projects SET body=?, version=version+1 WHERE id=?',
                       (json.dumps(body), identifier))
            self.log(db, actor, 'update_project', identifier, data)
            return self.project(identifier, db)

    def import_source(self, source_id, content, actor, origin):
        actor, origin = text(actor, 'actor', 200), text(origin, 'origin', 2000)
        text(content, 'source content', MAX_TEXT)
        digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            source = db.execute('SELECT * FROM sources WHERE id=?', (source_id,)).fetchone()
            if not source:
                raise KeyError('source not found')
            revision = db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM snapshots WHERE source_id=?',
                                  (source_id,)).fetchone()[0]
            db.execute('''INSERT INTO snapshots(source_id,revision,content,sha256,actor,imported_at,origin)
                          VALUES (?,?,?,?,?,?,?)''', (source_id, revision, content, digest, actor, now(), origin))
            if source['project_id']:
                row = db.execute('SELECT body FROM projects WHERE id=?', (source['project_id'],)).fetchone()
                body = json.loads(row['body'])
                body['scope_confirmed'] = False
                for task in body['tasks'].values():
                    task.update(done=False, evidence='', actor='', at='')
                db.execute('UPDATE projects SET body=?,version=version+1 WHERE id=?',
                           (json.dumps(body), source['project_id']))
            self.log(db, actor, 'import_source', source_id, {'revision': revision, 'sha256': digest, 'origin': origin})
            return {'source_id': source_id, 'revision': revision, 'sha256': digest}

    def review_source(self, source_id, revision, actor):
        actor = text(actor, 'reviewer', 200)
        if type(revision) is not int:
            raise ValueError('integer revision is required')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            latest = db.execute('SELECT MAX(revision) FROM snapshots WHERE source_id=?', (source_id,)).fetchone()[0]
            if latest is None:
                raise KeyError('source has no imported content')
            if revision != latest:
                raise Conflict('Source changed. Review the current version.')
            db.execute('UPDATE snapshots SET reviewer=?,reviewed_at=? WHERE source_id=? AND revision=?',
                       (actor, now(), source_id, revision))
            self.log(db, actor, 'review_source', source_id, {'revision': revision})
            return {'source_id': source_id, 'revision': revision, 'reviewer': actor}

    def source_content(self, source_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM snapshots WHERE source_id=? ORDER BY revision DESC LIMIT 1',
                             (source_id,)).fetchone()
            if row is None:
                raise KeyError('source has no imported content')
            return dict(row)

    def backup(self, destination):
        destination = Path(destination)
        if destination.resolve() == self.path.resolve() or destination.exists():
            raise ValueError('backup destination must be a new file')
        with self.connect() as db:
            target = sqlite3.connect(destination)
            try:
                db.backup(target)
            finally:
                target.close()
