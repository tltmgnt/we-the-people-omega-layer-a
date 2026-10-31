"""Run with python -m civic_portfolio --help."""
import argparse
import json
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .store import Conflict, MAX_TEXT, Store
from .permits import Permits

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
                    if path in ['/', '/app.js', '/style.css', '/permits', '/permits.js']:
                        name = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css', '/permits': 'permits.html', '/permits.js': 'permits.js'}[path]
                        kind = 'text/html' if name.endswith('.html') else 'text/javascript' if name.endswith('.js') else 'text/css'
                        self.send(200, (STATIC / name).read_bytes(), kind + '; charset=utf-8')
                    elif path == '/api/bootstrap':
                        exported = store.export()
                        self.send(200, {'token': token, 'projects': exported['projects'], 'sources': exported['sources']})
                    elif path == '/api/export':
                        self.send(200, store.export())
                    elif path == '/api/permits':
                        self.send(200, {'cases': permits.cases(), 'token': token})
                    elif path == '/api/permits/report':
                        query = parse_qs(urlsplit(self.path).query)
                        self.send(200, permits.report(query.get('as_of', [None])[0], query.get('category', [None])[0]))
                    elif len(parts) == 3 and parts[:2] == ['api', 'sources']:
                        self.send(200, store.source_content(parts[2]))
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
