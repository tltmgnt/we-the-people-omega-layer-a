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
