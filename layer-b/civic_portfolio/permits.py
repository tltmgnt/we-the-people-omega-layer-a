"""Synthetic permit lifecycle and reproducible measurement, not live approvals."""
from datetime import datetime, timezone
import math
import re
from statistics import median

from .store import Conflict, now, text

STAGES = {
    'RECEIVED': {'IN_REVIEW', 'WITHDRAWN'},
    'IN_REVIEW': {'AWAITING_CORRECTION', 'INSPECTION', 'WITHDRAWN'},
    'AWAITING_CORRECTION': {'IN_REVIEW', 'WITHDRAWN'},
    'INSPECTION': {'AWAITING_CORRECTION', 'DECIDED', 'WITHDRAWN'},
    'DECIDED': set(), 'WITHDRAWN': set(),
}
TERMINAL = {'DECIDED', 'WITHDRAWN'}


def timestamp(value):
    value = text(value, 'timestamp', 100)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value):
        raise ValueError('timestamp requires RFC3339 date/time with timezone')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None:
        raise ValueError('timestamp requires a timezone')
    return parsed.astimezone(timezone.utc)


def hours(value):
    if value is None:
        return None
    if type(value) not in {int, float} or not math.isfinite(value) or not 0 <= value <= 1_000_000:
        raise ValueError('effort must be null or a finite nonnegative number of person-hours')
    return value


def statistic(values):
    ordered = sorted(values)
    return {'sample_size': len(ordered), 'median': median(ordered) if ordered else None,
            'p90_nearest_rank': ordered[math.ceil(.9 * len(ordered)) - 1] if ordered else None}


class Permits:
    def __init__(self, store):
        self.store = store

    def case(self, identifier, db=None):
        if db is None:
            with self.store.connect() as connection:
                return self.case(identifier, connection)
        row = db.execute('SELECT * FROM permit_cases WHERE id=?', (identifier,)).fetchone()
        if not row:
            raise KeyError('synthetic permit case not found')
        events = [dict(r) for r in db.execute('SELECT * FROM permit_events WHERE case_id=? ORDER BY sequence', (identifier,))]
        quality = [dict(r) for r in db.execute('SELECT * FROM permit_quality WHERE case_id=? ORDER BY sequence', (identifier,))]
        stage = events[-1]['stage']
        return {**dict(row), 'kind': 'SYNTHETIC', 'events': events, 'quality_reviews': quality,
                'stage': stage, 'allowed_next_stages': sorted(STAGES[stage]),
                'execution_authorized': False}

    def cases(self):
        with self.store.connect() as db:
            return [self.case(r['id'], db) for r in db.execute('SELECT id FROM permit_cases ORDER BY id')]

    def create(self, data):
        if not isinstance(data, dict) or set(data) != {'case_id', 'category', 'at', 'actor', 'evidence'}:
            raise ValueError('case requires case_id, category, at, actor and evidence')
        identifier = text(data['case_id'], 'case_id', 64)
        if not re.fullmatch(r'SYN-[A-Z0-9-]{1,60}', identifier):
            raise ValueError('synthetic case_id must start SYN- and use uppercase letters, digits or hyphens')
        category = text(data['category'], 'category', 100)
        actor = text(data['actor'], 'actor', 200)
        evidence = text(data['evidence'], 'synthetic evidence')
        at = timestamp(data['at']).isoformat()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM permit_cases WHERE id=?', (identifier,)).fetchone():
                raise Conflict('synthetic case ID already exists')
            db.execute('INSERT INTO permit_cases VALUES (?,?,1)', (identifier, category))
            db.execute('INSERT INTO permit_events VALUES (?,1,?,?,?,?,NULL,NULL)',
                       (identifier, 'RECEIVED', at, actor, evidence))
            self.store.log(db, actor, 'create_synthetic_permit', identifier, data)
            return self.case(identifier, db)

    def advance(self, identifier, data):
        if not isinstance(data, dict) or set(data) != {'version', 'stage', 'at', 'actor', 'evidence', 'staff_hours', 'public_hours'}:
            raise ValueError('event requires version, stage, at, actor, evidence, staff_hours and public_hours')
        if type(data['version']) is not int:
            raise ValueError('integer version required')
        actor, evidence = text(data['actor'], 'actor', 200), text(data['evidence'], 'synthetic evidence')
        at = timestamp(data['at'])
        stage = text(data['stage'], 'stage', 100)
        staff, public = hours(data['staff_hours']), hours(data['public_hours'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            case = self.case(identifier, db)
            if case['version'] != data['version']:
                raise Conflict('Case changed. Reload before adding an event.')
            if stage not in STAGES[case['stage']]:
                raise ValueError('stage transition is not allowed by this synthetic exercise')
            if at < timestamp(case['events'][-1]['at']):
                raise ValueError('event time precedes the previous stage')
            db.execute('INSERT INTO permit_events VALUES (?,?,?,?,?,?,?,?)',
                       (identifier, len(case['events'])+1, stage, at.isoformat(), actor, evidence, staff, public))
            db.execute('UPDATE permit_cases SET version=version+1 WHERE id=?', (identifier,))
            self.store.log(db, actor, 'advance_synthetic_permit', identifier, data)
            return self.case(identifier, db)

    def review(self, identifier, data):
        if not isinstance(data, dict) or set(data) != {'version', 'at', 'reviewer', 'passed', 'evidence'}:
            raise ValueError('quality review requires version, at, reviewer, passed and evidence')
        if type(data['version']) is not int or type(data['passed']) is not bool:
            raise ValueError('quality review requires an integer version and boolean passed')
        actor, evidence = text(data['reviewer'], 'reviewer', 200), text(data['evidence'], 'quality evidence')
        at = timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            case = self.case(identifier, db)
            if case['version'] != data['version']:
                raise Conflict('Case changed. Reload before recording quality review.')
            if case['stage'] != 'DECIDED' or at < timestamp(case['events'][-1]['at']):
                raise ValueError('quality review must follow a recorded synthetic decision')
            if case['quality_reviews'] and at < timestamp(case['quality_reviews'][-1]['at']):
                raise ValueError('quality review time precedes the previous review')
            db.execute('INSERT INTO permit_quality VALUES (?,?,?,?,?,?)',
                       (identifier, len(case['quality_reviews'])+1, at.isoformat(), actor, int(data['passed']), evidence))
            db.execute('UPDATE permit_cases SET version=version+1 WHERE id=?', (identifier,))
            self.store.log(db, actor, 'review_synthetic_permit_quality', identifier, data)
            return self.case(identifier, db)

    def report(self, as_of=None, category=None):
        at = timestamp(as_of or now())
        elapsed, ages, staff, public, quality = [], [], [], [], []
        included = withdrawn = corrections = decisions = 0
        stage_hours = {s: 0 for s in STAGES if s not in TERMINAL}
        for case in self.cases():
            if category and case['category'] != category:
                continue
            events = [e for e in case['events'] if timestamp(e['at']) <= at]
            if not events:
                continue
            included += 1
            last = events[-1]
            corrections += sum(e['stage'] == 'AWAITING_CORRECTION' for e in events)
            for index, event in enumerate(events):
                end = timestamp(events[index+1]['at']) if index+1 < len(events) else at
                if event['stage'] not in TERMINAL:
                    stage_hours[event['stage']] += (end-timestamp(event['at'])).total_seconds()/3600
            duration = (timestamp(last['at'])-timestamp(events[0]['at'])).total_seconds()/3600
            if last['stage'] == 'DECIDED':
                decisions += 1
                elapsed.append(duration)
                for field, values in [('staff_hours', staff), ('public_hours', public)]:
                    intervals = events[1:]
                    if all(e[field] is not None for e in intervals):
                        values.append(sum(e[field] for e in intervals))
                reviews = [r for r in case['quality_reviews'] if timestamp(r['at']) <= at]
                if reviews:
                    quality.append(reviews[-1]['passed'])
            elif last['stage'] == 'WITHDRAWN':
                withdrawn += 1
            else:
                ages.append((at-timestamp(events[0]['at'])).total_seconds()/3600)
        return {'kind': 'SYNTHETIC', 'as_of': at.isoformat(), 'category': category,
                'arrivals': included, 'decided': decisions, 'withdrawn': withdrawn, 'open': len(ages),
                'elapsed_calendar_hours': statistic(elapsed), 'open_age_calendar_hours': statistic(ages),
                'staff_person_hours': {**statistic(staff), 'missing_decided_cases': decisions-len(staff)},
                'public_person_hours': {**statistic(public), 'missing_decided_cases': decisions-len(public)},
                'quality_pass_rate': sum(quality)/len(quality) if quality else None,
                'quality_sample_size': len(quality), 'quality_unreviewed_decisions': decisions-len(quality),
                'correction_cycles': corrections, 'stage_calendar_hours': stage_hours,
                'execution_authorized': False,
                'method': 'Calendar hours in UTC; corrections/pauses stay in elapsed time. Open cases are censored and reported separately. Withdrawals are excluded from decision-time statistics. P90 uses nearest rank. Effort is reported separately and never inferred from stage duration. No causal or real-world performance claim.'}
