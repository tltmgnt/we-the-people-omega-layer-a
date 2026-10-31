"""Fictional asset maintenance, verification and historical queue reporting."""
import re

from .permits import statistic, timestamp
from .store import Conflict, now, text

STAGES = {'REPORTED': {'TRIAGED'}, 'TRIAGED': {'SCHEDULED'},
          'SCHEDULED': {'IN_PROGRESS'}, 'IN_PROGRESS': {'VERIFICATION'},
          'VERIFICATION': {'CLOSED', 'IN_PROGRESS'}, 'CLOSED': {'TRIAGED'}}
PRIORITIES = {'ROUTINE', 'URGENT', 'SAFETY_REVIEW'}


def identifier(value):
    value = text(value, 'synthetic identifier', 64)
    if not re.fullmatch(r'SYN-[A-Z0-9-]{1,60}', value):
        raise ValueError('synthetic identifiers must start SYN- and use uppercase letters, digits or hyphens')
    return value


def fields(data, required):
    if not isinstance(data, dict) or set(data) != set(required.split()):
        raise ValueError('required fields: '+required)


class Maintenance:
    def __init__(self, store):
        self.store = store

    def assets(self):
        with self.store.connect() as db:
            return [{**dict(row), 'kind': 'SYNTHETIC'} for row in db.execute('SELECT * FROM maintenance_assets ORDER BY id')]

    def create_asset(self, data):
        fields(data, 'asset_id category area at actor evidence')
        asset_id = identifier(data['asset_id'])
        category, area = text(data['category'], 'asset category', 100), text(data['area'], 'fictional area', 100)
        at = timestamp(data['at']).isoformat()
        actor, evidence = text(data['actor'], 'actor', 200), text(data['evidence'], 'asset evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM maintenance_assets WHERE id=?', (asset_id,)).fetchone():
                raise Conflict('synthetic asset already exists')
            db.execute('INSERT INTO maintenance_assets VALUES (?,?,?,?,?,?)', (asset_id, category, area, at, actor, evidence))
            self.store.log(db, actor, 'create_synthetic_asset', asset_id, data)
            return {**data, 'id': asset_id, 'kind': 'SYNTHETIC'}

    def order(self, order_id, db=None):
        if db is None:
            with self.store.connect() as connection:
                return self.order(order_id, connection)
        row = db.execute('''SELECT o.*, a.category,a.area FROM maintenance_orders o
                            JOIN maintenance_assets a ON o.asset_id=a.id WHERE o.id=?''', (order_id,)).fetchone()
        if not row:
            raise KeyError('synthetic work order not found')
        events = [dict(r) for r in db.execute('SELECT * FROM maintenance_events WHERE order_id=? ORDER BY sequence', (order_id,))]
        checks = [dict(r) for r in db.execute('SELECT * FROM maintenance_checks WHERE order_id=? ORDER BY sequence', (order_id,))]
        priorities = [e['priority'] for e in events if e['priority']]
        return {**dict(row), 'events': events, 'checks': checks, 'stage': events[-1]['stage'],
                'priority': priorities[-1] if priorities else 'UNTRIAGED',
                'allowed_next_stages': sorted(STAGES[events[-1]['stage']]),
                'kind': 'SYNTHETIC', 'execution_authorized': False}

    def orders(self):
        with self.store.connect() as db:
            return [self.order(row['id'], db) for row in db.execute('SELECT id FROM maintenance_orders ORDER BY id')]

    def create_order(self, data):
        fields(data, 'order_id asset_id condition at actor evidence')
        order_id, asset_id = identifier(data['order_id']), identifier(data['asset_id'])
        condition = text(data['condition'], 'reported condition')
        actor, evidence = text(data['actor'], 'actor', 200), text(data['evidence'], 'condition evidence')
        at = timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            asset = db.execute('SELECT * FROM maintenance_assets WHERE id=?', (asset_id,)).fetchone()
            if not asset:
                raise KeyError('register the fictional asset first')
            if at < timestamp(asset['registered_at']):
                raise ValueError('work order precedes asset registration')
            if db.execute('SELECT id FROM maintenance_orders WHERE id=?', (order_id,)).fetchone():
                raise Conflict('synthetic work order already exists')
            db.execute('INSERT INTO maintenance_orders VALUES (?,?,?,1)', (order_id, asset_id, condition))
            db.execute('INSERT INTO maintenance_events VALUES (?,1,?,?,?,?,NULL,NULL)',
                       (order_id, 'REPORTED', at.isoformat(), actor, evidence))
            self.store.log(db, actor, 'create_synthetic_work_order', order_id, data)
            return self.order(order_id, db)

    def advance(self, order_id, data):
        fields(data, 'version stage at actor evidence priority team')
        if type(data['version']) is not int:
            raise ValueError('integer version required')
        stage = text(data['stage'], 'stage', 100)
        actor, evidence = text(data['actor'], 'actor', 200), text(data['evidence'], 'stage evidence')
        at = timestamp(data['at'])
        priority, team = data['priority'], data['team']
        if stage == 'TRIAGED' and (not isinstance(priority, str) or priority not in PRIORITIES):
            raise ValueError('triage requires ROUTINE, URGENT or SAFETY_REVIEW priority and evidence rationale')
        if stage != 'TRIAGED' and priority is not None:
            raise ValueError('priority is recorded only during triage')
        if stage == 'SCHEDULED':
            team = text(team, 'assigned fictional team', 200)
        elif team is not None:
            raise ValueError('team assignment is recorded only during scheduling')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            order = self.order(order_id, db)
            if order['version'] != data['version']:
                raise Conflict('Work order changed. Reload before saving.')
            if stage not in STAGES[order['stage']]:
                raise ValueError('invalid synthetic maintenance transition')
            if at < timestamp(order['events'][-1]['at']):
                raise ValueError('event precedes previous stage')
            if order['checks'] and at < timestamp(order['checks'][-1]['at']):
                raise ValueError('event precedes latest verification')
            if stage == 'CLOSED':
                check = order['checks'][-1] if order['checks'] else None
                if not check or check['event_sequence'] != len(order['events']) or not check['passed'] or timestamp(check['at']) > at:
                    raise ValueError('closure requires a passing verification for the current verification stage, at or before closure')
            db.execute('INSERT INTO maintenance_events VALUES (?,?,?,?,?,?,?,?)',
                       (order_id, len(order['events'])+1, stage, at.isoformat(), actor, evidence, priority, team))
            db.execute('UPDATE maintenance_orders SET version=version+1 WHERE id=?', (order_id,))
            self.store.log(db, actor, 'advance_synthetic_work_order', order_id, data)
            return self.order(order_id, db)

    def verify(self, order_id, data):
        fields(data, 'version at verifier passed evidence')
        if type(data['version']) is not int or type(data['passed']) is not bool:
            raise ValueError('integer version and boolean passed required')
        actor, evidence = text(data['verifier'], 'verifier', 200), text(data['evidence'], 'verification evidence')
        at = timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            order = self.order(order_id, db)
            if order['version'] != data['version']:
                raise Conflict('Work order changed. Reload before verification.')
            if order['stage'] != 'VERIFICATION' or at < timestamp(order['events'][-1]['at']):
                raise ValueError('verification must follow the current verification stage')
            workers = [e['actor'] for e in order['events'] if e['stage'] == 'IN_PROGRESS']
            if workers and actor == workers[-1]:
                raise ValueError('use a distinct verifier identifier from the latest work actor')
            if order['checks'] and at < timestamp(order['checks'][-1]['at']):
                raise ValueError('verification precedes previous check')
            db.execute('INSERT INTO maintenance_checks VALUES (?,?,?,?,?,?,?)',
                       (order_id, len(order['checks'])+1, len(order['events']), at.isoformat(), actor, int(data['passed']), evidence))
            db.execute('UPDATE maintenance_orders SET version=version+1 WHERE id=?', (order_id,))
            self.store.log(db, actor, 'verify_synthetic_work_order', order_id, data)
            return self.order(order_id, db)

    def report(self, as_of=None, area=None):
        at = timestamp(as_of or now())
        assets = [a for a in self.assets() if timestamp(a['registered_at']) <= at and (not area or a['area'] == area)]
        reported = closed = reopened = failed = 0
        ages, repairs = [], []
        priorities, areas = {}, {a['area']: {'assets': 0, 'reported_orders': 0, 'open_orders': 0} for a in assets}
        for asset in assets:
            areas[asset['area']]['assets'] += 1
        for order in self.orders():
            if area and order['area'] != area:
                continue
            events = [e for e in order['events'] if timestamp(e['at']) <= at]
            if not events:
                continue
            reported += 1
            areas[order['area']]['reported_orders'] += 1
            last = events[-1]
            triages = [e for e in events if e['priority']]
            priority = triages[-1]['priority'] if triages else 'UNTRIAGED'
            reopened += sum(events[i-1]['stage'] == 'CLOSED' for i in range(1,len(events)))
            failed += sum(not c['passed'] and timestamp(c['at']) <= at for c in order['checks'])
            if last['stage'] == 'CLOSED':
                closed += 1
                repairs.append((timestamp(last['at'])-timestamp(events[0]['at'])).total_seconds()/3600)
            else:
                ages.append((at-timestamp(events[0]['at'])).total_seconds()/3600)
                priorities[priority] = priorities.get(priority,0)+1
                areas[order['area']]['open_orders'] += 1
        return {'kind': 'SYNTHETIC', 'as_of': at.isoformat(), 'area': area, 'assets': len(assets),
                'reported_orders': reported, 'closed_orders': closed, 'open_orders': len(ages),
                'verified_elapsed_calendar_hours': statistic(repairs),
                'backlog_age_calendar_hours': statistic(ages), 'open_by_priority': priorities,
                'reopen_events': reopened, 'failed_verifications': failed, 'area_inventory': areas,
                'execution_authorized': False,
                'method': 'UTC calendar hours from original report; reopened orders remain open until reverified and closed. Closed-order statistics use the latest closure and include all correction/reopen intervals. Open orders are censored and reported separately. P90 uses nearest rank. Area counts are inventory context, not service equity or population coverage. Recorded checks and identities are user assertions; no real safety finding or repair dispatch occurs.'}
