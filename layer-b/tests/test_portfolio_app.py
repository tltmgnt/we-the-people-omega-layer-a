import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from civic_portfolio.store import Conflict, Store
from civic_portfolio.__main__ import server, strict_json
from scripts.build_implementation_plans import build


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'work.sqlite3'
        self.store = Store(self.path)

    def update(self, **fields):
        p = self.store.project('009')
        return self.store.update('009', {'version': p['version'], 'actor': 'TEST-OWNER', **fields})

    def test_all_projects_and_proposed_plans_preserve_unknowns(self):
        exported = self.store.export()
        self.assertEqual([p['project_id'] for p in exported['projects']], [f'{i:03}' for i in range(1,51)])
        self.assertEqual(len(exported['sources']), 61)
        self.assertEqual(exported['snapshots'], [])
        self.assertTrue(all(p['blockers'] and not p['execution_authorized'] for p in exported['projects']))
        self.assertTrue(all(p['title'] is None for p in exported['projects'][:6]))
        self.assertEqual(set(build()[1]), {f'{i:03}' for i in range(1,51)})
        for project in exported['projects']:
            self.assertEqual(len(project['plan']['steps']),8)
            plan_path = Path(__file__).resolve().parents[1] / 'portfolio/plans' / (project['project_id']+'.md')
            self.assertIn(project['plan']['outcome'],plan_path.read_text())

    def test_source_is_full_text_hashed_versioned_and_persisted(self):
        raw = '\nFull source text Ω\nSecond paragraph.\n'
        snap = self.store.import_source('project-009',raw,'TEST-IMPORTER','supplied-export.txt')
        self.assertEqual(snap['sha256'],hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(Store(self.path).source_content('project-009')['content'],raw)
        self.store.review_source('project-009',1,'TEST-REVIEWER')
        self.store.import_source('project-009','Revised source','TEST-IMPORTER','supplied-export-v2.txt')
        self.assertIsNone(self.store.source_content('project-009')['reviewer'])
        self.assertEqual(len(self.store.export()['snapshots']),2)
        with self.assertRaises(Conflict):
            self.store.review_source('project-009',1,'TEST-REVIEWER')

    def test_completion_requires_definition_review_and_every_step(self):
        for task in self.store.project('009')['tasks']:
            self.update(task=dict(id=task,done=True,evidence='TEST FIXTURE ONLY: verified result'))
        self.assertNotEqual(self.store.project('009')['status'],'COMPLETE_AS_RECORDED')
        self.store.import_source('project-009','Synthetic requirements for test','TEST-IMPORTER','synthetic.txt')
        self.store.review_source('project-009',1,'TEST-REVIEWER')
        self.update(owner='TEST-OWNER',scope='Synthetic test workflow')
        self.update(scope_confirmed=True)
        for task in self.store.project('009')['tasks']:
            self.update(task=dict(id=task,done=True,evidence='TEST FIXTURE ONLY: verified result'))
        complete = self.store.project('009')
        self.assertEqual(complete['status'],'COMPLETE_AS_RECORDED')
        self.assertFalse(complete['execution_authorized'])
        self.store.import_source('project-009','Changed requirements','TEST-IMPORTER','synthetic-v2.txt')
        self.assertNotEqual(self.store.project('009')['status'],'COMPLETE_AS_RECORDED')
        self.assertEqual(self.store.project('009')['completed_steps'],0)

    def test_definition_changes_clear_old_evidence(self):
        self.update(task=dict(id='build',done=True,evidence='Old test output'))
        changed = self.update(scope='Changed requirements',scope_confirmed=True)
        self.assertEqual(changed['completed_steps'],0)
        self.assertFalse(changed['scope_confirmed'])

    def test_conflicting_edits_and_invalid_fields(self):
        version = self.store.project('009')['version']
        self.update(owner='Owner')
        with self.assertRaises(Conflict):
            self.store.update('009',dict(version=version,actor='Owner',owner='Other'))
        for fields in [dict(status='COMPLETE'),dict(scope_confirmed='yes'),dict(actor=''),
                       dict(task=dict(id='build',done=True,evidence='')),
                       dict(task=dict(id=[],done=True,evidence='test'))]:
            with self.subTest(fields=fields),self.assertRaises(ValueError):
                self.update(**fields)
        with self.assertRaises(KeyError):
            self.store.project('999')
        for raw in ['{"a":1,"a":2}', '{"x":NaN}']:
            with self.assertRaises(ValueError):
                strict_json(raw)

    def test_backup_restores_sources_and_audit(self):
        self.store.import_source('foundation-1','Synthetic foundation text','TEST','fixture.txt')
        self.update(owner='TEST OWNER')
        backup = Path(self.directory.name) / 'backup.sqlite3'
        self.store.backup(backup)
        restored = Store(backup).export()
        expected = self.store.export()
        for field in ['projects','sources','snapshots','audit']:
            self.assertEqual(restored[field],expected[field])
        with self.assertRaises(ValueError):
            self.store.backup(backup)

    def test_http_ui_mutations_exports_and_security_boundaries(self):
        app = server(self.store,0)
        thread = threading.Thread(target=app.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(app.server_close)
        self.addCleanup(thread.join,2)
        self.addCleanup(app.shutdown)
        base = f'http://127.0.0.1:{app.server_port}'

        def get(path):
            with urlopen(base+path) as response:
                return response.read(),response.headers

        def post(path,body,token='',origin=None):
            headers={'Content-Type':'application/json','X-Portfolio-Token':token}
            if origin:
                headers['Origin']=origin
            with urlopen(Request(base+path,data=json.dumps(body).encode(),headers=headers)) as response:
                return json.loads(response.read())

        html,headers = get('/')
        self.assertIn(b'Civic portfolio workspace',html)
        self.assertIn("script-src 'self'",headers['Content-Security-Policy'])
        bootstrap = json.loads(get('/api/bootstrap')[0])
        self.assertEqual(len(bootstrap['projects']),50)
        payload=dict(version=self.store.project('009')['version'],actor='TEST',owner='HTTP OWNER')
        for token,origin in [('',None),(bootstrap['token'],'https://foreign.example')]:
            with self.assertRaises(HTTPError) as caught:
                post('/api/projects/009',payload,token,origin)
            self.assertEqual(caught.exception.code,403)
        saved=post('/api/projects/009',payload,bootstrap['token'])
        self.assertEqual(saved['owner'],'HTTP OWNER')
        source=post('/api/sources/project-009/import',dict(content='Synthetic HTTP source',actor='TEST',origin='fixture.txt'),bootstrap['token'])
        post('/api/sources/project-009/review',dict(revision=source['revision'],actor='TEST REVIEWER'),bootstrap['token'])
        exported=json.loads(get('/api/export')[0])
        self.assertEqual(exported['snapshots'][0]['content'],'Synthetic HTTP source')
        for path in ['/../store.py','/api/sources/unknown']:
            with self.assertRaises(HTTPError) as caught:
                get(path)
            self.assertEqual(caught.exception.code,404)


if __name__ == '__main__':
    unittest.main()
