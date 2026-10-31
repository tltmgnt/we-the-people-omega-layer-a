"""Run with python -m civic_portfolio --help."""
import argparse
import hashlib
import json
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .store import Conflict, MAX_TEXT, Store, now
from .permits import Permits
from .maintenance import Maintenance
from .sanitation import Sanitation
from .transit import Transit
from .housing import Housing
from .public_access import PublicAccess
from .utilities import Utilities
from .rights import Rights
from .justice import Justice, DIMENSIONS, MODULES, ROLES, SCHEMAS, STAGES
from .finance import Finance
from .election_services import ElectionServices

STATIC = Path(__file__).parent / 'static'


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result

    def reject(value):
        raise ValueError('nonfinite JSON constant')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)


def server(store, port=8765):
    token = secrets.token_urlsafe(32)
    permits = Permits(store)
    maintenance = Maintenance(store)
    sanitation = Sanitation(store)
    transit = Transit(store)
    housing = Housing(store)
    public_access = PublicAccess(store)
    utilities = Utilities(store)
    rights = Rights(store)
    justice = Justice(store)
    finance = Finance(store)
    election_services = ElectionServices(store)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, status, body, kind='application/json; charset=utf-8'):
            raw = json.dumps(body, allow_nan=False).encode() if kind.startswith('application/json') else body
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(raw)

        def dispatch(self, mutation=False):
            try:
                allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
                if self.headers.get('Host') not in allowed:
                    self.send(403, {'error': 'Use the local application address'})
                    return
                if mutation:
                    if self.headers.get('X-Portfolio-Token') != token:
                        self.send(403, {'error': 'Reload the application before saving'})
                        return
                    if self.headers.get('Origin') not in {None, *('http://' + h for h in allowed)}:
                        self.send(403, {'error': 'Foreign origin rejected'})
                        return
                    length = int(self.headers.get('Content-Length', '0'))
                    if length <= 0 or length > MAX_TEXT * 6 + 10000:
                        raise ValueError('request body is empty or too large')
                    data = strict_json(self.rfile.read(length).decode('utf-8'))
                    if not isinstance(data, dict):
                        raise ValueError('request must be an object')
                parts = urlsplit(self.path).path.strip('/').split('/')
                if not mutation:
                    path = urlsplit(self.path).path
                    if path in ['/', '/app.js', '/style.css', '/permits', '/permits.js', '/maintenance', '/maintenance.js', '/sanitation', '/sanitation.js', '/transit', '/transit.js', '/housing', '/housing.js', '/public-access', '/public-access.js', '/utilities', '/utilities.js', '/rights', '/rights.js', '/election-services', '/election-services.js', '/finance', '/finance.js', '/justice', '/justice.js']:
                        name = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css', '/permits': 'permits.html', '/permits.js': 'permits.js', '/maintenance': 'maintenance.html', '/maintenance.js': 'maintenance.js', '/sanitation': 'sanitation.html', '/sanitation.js': 'sanitation.js', '/transit': 'transit.html', '/transit.js': 'transit.js', '/housing': 'housing.html', '/housing.js': 'housing.js', '/public-access': 'public-access.html', '/public-access.js': 'public-access.js', '/utilities': 'utilities.html', '/utilities.js': 'utilities.js', '/rights': 'rights.html', '/rights.js': 'rights.js', '/election-services': 'election-services.html', '/election-services.js': 'election-services.js', '/finance': 'finance.html', '/finance.js': 'finance.js', '/justice': 'justice.html', '/justice.js': 'justice.js'}[path]
                        kind = 'text/html' if name.endswith('.html') else 'text/javascript' if name.endswith('.js') else 'text/css'
                        self.send(200, (STATIC / name).read_bytes(), kind + '; charset=utf-8')
                    elif path == '/api/bootstrap':
                        exported = store.export()
                        self.send(200, {'token': token, 'projects': exported['projects'], 'sources': exported['sources']})
                    elif path == '/api/export':
                        self.send(200, store.export())
                    elif path == '/api/permits':
                        self.send(200, {'cases': permits.cases(), 'token': token})
                    elif path == '/api/maintenance':
                        self.send(200, {'assets': maintenance.assets(), 'orders': maintenance.orders(), 'token': token})
                    elif path == '/api/sanitation':
                        self.send(200, {'routes': sanitation.routes(), 'runs': sanitation.runs(), 'issues': sanitation.issues(), 'token': token})
                    elif path == '/api/transit':
                        self.send(200, {'trips': transit.trips(), 'findings': transit.findings(), 'token': token})
                    elif path == '/api/housing':
                        self.send(200, {'cases': housing.cases(), 'requests': housing.requests(), 'token': token})
                    elif path == '/api/public-access':
                        self.send(200, {'cases': public_access.cases(), 'meetings': public_access.meetings(), 'token': token})
                    elif path == '/api/utilities':
                        self.send(200, {'assets': utilities.assets(), 'incidents': utilities.incidents(), 'token': token})
                    elif path == '/api/rights':
                        self.send(200, {'cases': rights.cases(), 'token': token})
                    elif path == '/api/justice/specification':
                        content=(STATIC.parent.parent/'portfolio/sources/023-user-specification.md').read_text()
                        self.send(200,dict(content=content,sha256=hashlib.sha256(content.encode()).hexdigest(),origin='User-supplied Project 023 specification, 2026-10-31; Markdown formatting normalized; external claims unverified'))
                    elif path == '/api/justice':
                        self.send(200,dict(pilots=justice.pilots(),token=token,dimensions=DIMENSIONS,modules=MODULES,roles=ROLES,schemas=SCHEMAS,stages=list(STAGES)))
                    elif len(parts)==4 and parts[:2]==['api','justice'] and parts[3]=='report':
                        query=parse_qs(urlsplit(self.path).query)
                        self.send(200,justice.report(parts[2],query.get('as_of',[now()])[0]))
                    elif path == '/api/finance':
                        self.send(200, {'ledgers': finance.ledgers(), 'token': token})
                    elif len(parts)==4 and parts[:2]==['api','finance'] and parts[3]=='report':
                        query=parse_qs(urlsplit(self.path).query)
                        self.send(200,finance.report(parts[2],query.get('as_of',[now()])[0]))
                    elif path == '/api/election-services':
                        self.send(200, {'sessions': election_services.sessions(), 'token': token})
                    elif path == '/api/election-services/report':
                        query = parse_qs(urlsplit(self.path).query)
                        self.send(200, election_services.report(query.get('as_of', [None])[0], query.get('area', [None])[0], query.get('channel', [None])[0]))
                    elif path == '/api/rights/report':
                        query = parse_qs(urlsplit(self.path).query)
                        self.send(200, rights.report(query.get('as_of', [None])[0], query.get('jurisdiction', [None])[0]))
                    elif len(parts) == 5 and parts[:3] == ['api', 'rights', 'cases'] and parts[4] in {'layer-a','bundle'}:
                        bundle=rights.bundle(parts[3])
                        self.send(200, bundle['record'] if parts[4]=='layer-a' else bundle)
                    elif path == '/api/utilities/report':
                        query = parse_qs(urlsplit(self.path).query)
                        self.send(200, utilities.report(query.get('as_of', [None])[0], query.get('area', [None])[0], query.get('utility', [None])[0]))
                    elif path == '/api/public-access/report':
                        query = parse_qs(urlsplit(self.path).query)
                        threshold=query.get('min_notice_hours', [None])[0]
                        self.send(200, public_access.report(query.get('as_of', [None])[0], query.get('area', [None])[0], query.get('kind', [None])[0], float(threshold) if threshold is not None else None))
                    elif path == '/api/housing/report':
                        query = parse_qs(urlsplit(self.path).query)
                        self.send(200, housing.report(query.get('as_of', [None])[0], query.get('program', [None])[0], query.get('area', [None])[0]))
                    elif path == '/api/transit/report':
                        query = parse_qs(urlsplit(self.path).query)
                        self.send(200, transit.report(query.get('as_of', [None])[0], query.get('service', [None])[0], query.get('area', [None])[0], float(query.get('early_minutes', ['1'])[0]), float(query.get('late_minutes', ['5'])[0])))
                    elif path == '/api/sanitation/report':
                        query = parse_qs(urlsplit(self.path).query)
                        self.send(200, sanitation.report(query.get('as_of', [None])[0], query.get('area', [None])[0], query.get('stream', [None])[0]))
                    elif path == '/api/maintenance/report':
                        query = parse_qs(urlsplit(self.path).query)
                        self.send(200, maintenance.report(query.get('as_of', [None])[0], query.get('area', [None])[0]))
                    elif path == '/api/permits/report':
                        query = parse_qs(urlsplit(self.path).query)
                        self.send(200, permits.report(query.get('as_of', [None])[0], query.get('category', [None])[0]))
                    elif len(parts) == 3 and parts[:2] == ['api', 'sources']:
                        self.send(200, store.source_content(parts[2]))
                    else:
                        self.send(404, {'error': 'route not found'})
                elif parts == ['api','justice','import-specification']:
                    if set(data)!={'actor'}:raise ValueError('actor required')
                    content=(STATIC.parent.parent/'portfolio/sources/023-user-specification.md').read_text()
                    self.send(201,store.import_source('project-023',content,data['actor'],'User-supplied Project 023 specification, 2026-10-31; Markdown formatting normalized; external claims unverified'))
                elif parts == ['api','justice','pilots']:
                    self.send(201,justice.create(data))
                elif len(parts)==4 and parts[:2]==['api','justice'] and parts[3]=='records':
                    self.send(200,justice.record(parts[2],data))
                elif parts == ['api','finance','ledgers']:
                    self.send(201,finance.create(data))
                elif len(parts)==4 and parts[:2]==['api','finance'] and parts[3]=='records':
                    self.send(200,finance.record(parts[2],data))
                elif parts == ['api', 'election-services', 'sessions']:
                    self.send(201, election_services.create_session(data))
                elif len(parts) == 5 and parts[:3] == ['api', 'election-services', 'sessions']:
                    if parts[4] == 'readiness':
                        self.send(200, election_services.readiness(parts[3], data))
                    elif parts[4] == 'readiness-checks':
                        self.send(200, election_services.verify_readiness(parts[3], data))
                    elif parts[4] == 'observations':
                        self.send(201, election_services.create_observation(parts[3], data))
                    else:
                        self.send(404, {'error': 'route not found'})
                elif len(parts) == 7 and parts[:3] == ['api', 'election-services', 'sessions'] and parts[4]=='observations':
                    if parts[6] == 'events':
                        self.send(200, election_services.advance(parts[3], parts[5], data))
                    elif parts[6] == 'checks':
                        self.send(200, election_services.verify_correction(parts[3], parts[5], data))
                    else:
                        self.send(404, {'error': 'route not found'})
                elif parts == ['api', 'rights', 'cases']:
                    self.send(201, rights.create_case(data))
                elif len(parts) == 5 and parts[:3] == ['api', 'rights', 'cases']:
                    if parts[4] == 'evidence':
                        self.send(201, rights.add_evidence(parts[3], data))
                    elif parts[4] == 'screenings':
                        self.send(200, rights.screen(parts[3], data))
                    elif parts[4] == 'authorities':
                        self.send(201, rights.add_authority(parts[3], data))
                    elif parts[4] == 'questions':
                        self.send(201, rights.add_question(parts[3], data))
                    else:
                        self.send(404, {'error': 'route not found'})
                elif len(parts) == 7 and parts[:3] == ['api', 'rights', 'cases'] and parts[4]=='questions' and parts[6]=='events':
                    self.send(200, rights.respond(parts[3], parts[5], data))
                elif parts == ['api', 'utilities', 'assets']:
                    self.send(201, utilities.create_asset(data))
                elif parts == ['api', 'utilities', 'incidents']:
                    self.send(201, utilities.create_incident(data))
                elif len(parts) == 5 and parts[:3] == ['api', 'utilities', 'incidents']:
                    if parts[4] == 'events':
                        self.send(200, utilities.advance(parts[3], data))
                    elif parts[4] == 'checks':
                        self.send(200, utilities.verify(parts[3], data))
                    else:
                        self.send(404, {'error': 'route not found'})
                elif parts == ['api', 'public-access', 'cases']:
                    self.send(201, public_access.create_case(data))
                elif parts == ['api', 'public-access', 'meetings']:
                    self.send(201, public_access.create_meeting(data))
                elif len(parts) == 5 and parts[:3] == ['api', 'public-access', 'cases']:
                    if parts[4] == 'deadlines':
                        self.send(200, public_access.deadline(parts[3], data))
                    elif parts[4] == 'responses':
                        self.send(200, public_access.respond(parts[3], data))
                    elif parts[4] == 'checks':
                        self.send(200, public_access.verify_response(parts[3], data))
                    elif parts[4] == 'events':
                        self.send(200, public_access.advance(parts[3], data))
                    else:
                        self.send(404, {'error': 'route not found'})
                elif len(parts) == 5 and parts[:3] == ['api', 'public-access', 'meetings']:
                    if parts[4] == 'notices':
                        self.send(200, public_access.notice(parts[3], data))
                    elif parts[4] == 'checks':
                        self.send(200, public_access.verify_notice(parts[3], data))
                    else:
                        self.send(404, {'error': 'route not found'})
                elif parts == ['api', 'housing', 'cases']:
                    self.send(201, housing.create_case(data))
                elif parts == ['api', 'housing', 'requests']:
                    self.send(201, housing.create_request(data))
                elif len(parts) == 5 and parts[:3] == ['api', 'housing', 'cases']:
                    if parts[4] == 'events':
                        self.send(200, housing.advance(parts[3], data))
                    elif parts[4] == 'consents':
                        self.send(200, housing.consent(parts[3], data))
                    elif parts[4] == 'checks':
                        self.send(200, housing.verify(parts[3], data))
                    else:
                        self.send(404, {'error': 'route not found'})
                elif len(parts) == 5 and parts[:3] == ['api', 'housing', 'requests'] and parts[4] == 'events':
                    self.send(200, housing.respond(parts[3], data))
                elif parts == ['api', 'transit', 'trips']:
                    self.send(201, transit.create_trip(data))
                elif parts == ['api', 'transit', 'findings']:
                    self.send(201, transit.create_finding(data))
                elif len(parts) == 5 and parts[:3] == ['api', 'transit', 'trips']:
                    if parts[4] == 'observations':
                        self.send(200, transit.observe(parts[3], data))
                    elif parts[4] == 'checks':
                        self.send(200, transit.verify(parts[3], data))
                    else:
                        self.send(404, {'error': 'route not found'})
                elif len(parts) == 5 and parts[:3] == ['api', 'transit', 'findings'] and parts[4] == 'events':
                    self.send(200, transit.update_finding(parts[3], data))
                elif parts == ['api', 'sanitation', 'routes']:
                    self.send(201, sanitation.create_route(data))
                elif parts == ['api', 'sanitation', 'runs']:
                    self.send(201, sanitation.create_run(data))
                elif parts == ['api', 'sanitation', 'issues']:
                    self.send(201, sanitation.create_issue(data))
                elif len(parts) == 5 and parts[:3] == ['api', 'sanitation', 'runs']:
                    if parts[4] == 'events':
                        self.send(200, sanitation.advance(parts[3], data))
                    elif parts[4] == 'checks':
                        self.send(200, sanitation.verify(parts[3], data))
                    else:
                        self.send(404, {'error': 'route not found'})
                elif len(parts) == 5 and parts[:3] == ['api', 'sanitation', 'issues'] and parts[4] == 'events':
                    self.send(200, sanitation.update_issue(parts[3], data))
                elif parts == ['api', 'maintenance', 'assets']:
                    self.send(201, maintenance.create_asset(data))
                elif parts == ['api', 'maintenance', 'orders']:
                    self.send(201, maintenance.create_order(data))
                elif len(parts) == 5 and parts[:3] == ['api', 'maintenance', 'orders']:
                    if parts[4] == 'events':
                        self.send(200, maintenance.advance(parts[3], data))
                    elif parts[4] == 'checks':
                        self.send(200, maintenance.verify(parts[3], data))
                    else:
                        self.send(404, {'error': 'route not found'})
                elif parts == ['api', 'permits']:
                    self.send(201, permits.create(data))
                elif len(parts) == 4 and parts[:2] == ['api', 'permits']:
                    if parts[3] == 'events':
                        self.send(200, permits.advance(parts[2], data))
                    elif parts[3] == 'quality':
                        self.send(200, permits.review(parts[2], data))
                    else:
                        self.send(404, {'error': 'route not found'})
                elif len(parts) == 3 and parts[:2] == ['api', 'projects']:
                    self.send(200, store.update(parts[2], data))
                elif len(parts) == 4 and parts[:2] == ['api', 'sources']:
                    if parts[3] == 'import':
                        self.send(201, store.import_source(parts[2], data.get('content'), data.get('actor'), data.get('origin')))
                    elif parts[3] == 'review':
                        self.send(200, store.review_source(parts[2], data.get('revision'), data.get('actor')))
                    else:
                        self.send(404, {'error': 'route not found'})
                else:
                    self.send(404, {'error': 'route not found'})
            except Conflict as error:
                self.send(409, {'error': str(error)})
            except KeyError as error:
                self.send(404, {'error': str(error)})
            except (ValueError, UnicodeError) as error:
                self.send(400, {'error': str(error)})

        def do_GET(self):
            self.dispatch()

        def do_POST(self):
            self.dispatch(True)

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local WE THE PEOPLE portfolio workspace')
    parser.add_argument('--db', type=Path, default=Path('.local/portfolio.sqlite3'))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('report')
    export = sub.add_parser('export')
    export.add_argument('--output', type=Path, required=True)
    backup = sub.add_parser('backup')
    backup.add_argument('--output', type=Path, required=True)
    imp = sub.add_parser('import-source')
    imp.add_argument('source_id')
    imp.add_argument('--file', type=Path, required=True)
    imp.add_argument('--actor', required=True)
    imp.add_argument('--origin', required=True)
    review = sub.add_parser('review-source')
    review.add_argument('source_id')
    review.add_argument('--revision', type=int, required=True)
    review.add_argument('--actor', required=True)
    serve = sub.add_parser('serve')
    serve.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        store = Store(args.db)
        if args.command == 'init':
            print('Initialized 50 projects. No source contents or completion claims invented.')
        elif args.command == 'report':
            for p in store.export()['projects']:
                print(f"{p['project_id']} {p['status']:20} {p['completed_steps']}/{p['total_steps']} {p['title'] or '[title to confirm]'}")
        elif args.command == 'export':
            args.output.write_text(json.dumps(store.export(), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            print(args.output)
        elif args.command == 'backup':
            store.backup(args.output)
            print(args.output)
        elif args.command == 'import-source':
            if args.file.stat().st_size > MAX_TEXT * 4:
                raise ValueError('source file is too large')
            print(json.dumps(store.import_source(args.source_id, args.file.read_text(encoding='utf-8'), args.actor, args.origin)))
        elif args.command == 'review-source':
            print(json.dumps(store.review_source(args.source_id, args.revision, args.actor)))
        elif args.command == 'serve':
            app = server(store, args.port)
            print(f'Portfolio workspace: http://127.0.0.1:{app.server_port}', flush=True)
            try:
                app.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                app.server_close()
    except (ValueError, OSError, KeyError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
