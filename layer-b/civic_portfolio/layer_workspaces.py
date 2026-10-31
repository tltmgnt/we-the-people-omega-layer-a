"""Synthetic C/D/E records. Local checks never authorize live intervention."""
import hashlib
import json
from .maintenance import fields, identifier
from .permits import timestamp
from .store import Conflict, text
from .scenarios import fingerprint, bounded

STAGES = ('DRAFT', 'DESIGNED', 'BASELINE_RECORDED', 'REHEARSAL_RECORDED',
          'EVALUATION_RECORDED', 'LEARNING_RECORDED')
SCHEMAS = {
    'EVIDENCE': 'evidence_id expected_revision content origin confidence corroborating_refs verification_reference limitations',
    'EVIDENCE_REVIEW': 'evidence_id revision passed',
    'STUDY': 'study_id domain definition kind unit cohort exclusions uncertainty counter_definition counter_kind counter_unit owner',
    'OBSERVATION': 'study_id version phase group window_start window_end primary_numerator primary_denominator primary_missing counter_numerator counter_denominator counter_missing pins',
    'OUTCOME_REVIEW': 'study_id version observation_sequence passed',
    'TRIAL': 'trial_id study_ids scope owner resources continuity rollback',
    'TRIAL_EVENT': 'trial_id version action status target_sequence passed',
}


def measure(kind, numerator, denominator, missing):
    if numerator is None:
        if denominator is not None:
            raise ValueError('missing numerator requires null denominator')
        return dict(value=None, numerator=None, denominator=None,
                    missing_reason=text(missing, 'missing-data reason'))
    if missing is not None:
        raise ValueError('known measure must have null missing reason')
    bounded(numerator, 'numerator', 0, 1000000000)
    if kind == 'PROPORTION':
        bounded(denominator, 'denominator', 1, 1000000000)
        if numerator > denominator:
            raise ValueError('proportion numerator exceeds denominator')
        value = numerator / denominator
    else:
        if denominator is not None:
            raise ValueError('count must have null denominator')
        value = numerator
    return dict(value=value, numerator=numerator, denominator=denominator, missing_reason=None)


class LayerWorkspaces:
    def __init__(self, store):
        self.store = store

    def events(self, db, kind, key):
        return [json.loads(r['body']) for r in db.execute(
            'SELECT body FROM layer_activity WHERE kind=? AND object_id=? ORDER BY sequence', (kind, key))]

    def append(self, db, kind, key, body):
        seq = db.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM layer_activity WHERE kind=? AND object_id=?',
                         (kind, key)).fetchone()[0]
        event = {**body, 'sequence': seq}
        db.execute('INSERT INTO layer_activity VALUES (?,?,?,?)', (kind, key, seq, json.dumps(event)))
        return event

    def evidence(self, key, db):
        rows = [json.loads(r['body']) for r in db.execute(
            'SELECT body FROM layer_documents WHERE id=? ORDER BY revision', (key,))]
        if not rows:
            raise KeyError('Layer D evidence not found')
        reviews = self.events(db, 'D_REVIEW', key)
        checks = [r for r in reviews if r['revision'] == rows[-1]['revision']]
        return dict(evidence_id=key, revisions=rows, reviews=reviews, current_revision=rows[-1]['revision'],
                    locally_reviewed=bool(checks and checks[-1]['passed']), source_truth_verified=False)

    def entity(self, key, db, kind):
        table, event_kind = {'study': ('layer_studies', 'C'), 'trial': ('layer_trials', 'E')}[kind]
        row = db.execute('SELECT body,version FROM '+table+' WHERE id=?', (key,)).fetchone()
        if not row:
            raise KeyError('Layer '+kind+' not found')
        return {**json.loads(row['body']), 'version': row['version'], 'events': self.events(db, event_kind, key)}

    @staticmethod
    def check_version(current, supplied):
        if type(supplied) is not int:
            raise ValueError('integer version required')
        if current != supplied:
            raise Conflict('Record changed; refresh before saving')

    @staticmethod
    def chronology(at, events, created):
        if timestamp(at) < max(timestamp(e['at']) for e in [*events, {'at': created}]):
            raise ValueError('timestamp precedes latest activity')

    def pin_status(self, pin, db):
        source = self.evidence(pin['evidence_id'], db)
        return (source['current_revision'] == pin['revision'] and
                source['revisions'][-1]['sha256'] == pin['sha256'] and source['locally_reviewed'])

    def report_study(self, key, db=None):
        if db is None:
            with self.store.connect() as conn:
                return self.report_study(key, conn)
        study = self.entity(key, db, 'study')
        observations = [e for e in study['events'] if e['kind'] == 'OBSERVATION']
        groups = sorted({o['group'] for o in observations})
        pairs = []
        for group in groups:
            selected = {o['phase']: o for o in observations if o['group'] == group}
            reasons, checks = [], {}
            for phase in ('BASELINE', 'FOLLOW_UP'):
                observation = selected.get(phase)
                if not observation:
                    reasons.append(phase+': observation missing')
                    continue
                reviews = [e for e in study['events'] if e['kind'] == 'OUTCOME_REVIEW' and
                           e['observation_sequence'] == observation['sequence']]
                checked = bool(reviews and reviews[-1]['passed'])
                current = all(self.pin_status(p, db) for p in observation['pins'])
                checks[phase] = dict(locally_checked=checked, evidence_current_and_reviewed=current)
                if not checked:
                    reasons.append(phase+': passing current observation check missing')
                if not current:
                    reasons.append(phase+': evidence revised or lacks a passing local review')
                if observation['primary']['value'] is None or observation['counter']['value'] is None:
                    reasons.append(phase+': primary or counter-measure unknown')
            baseline, follow = selected.get('BASELINE'), selected.get('FOLLOW_UP')
            if baseline and follow and timestamp(follow['window_start']) < timestamp(baseline['window_end']):
                reasons.append('baseline/follow-up windows overlap or are reversed')
            ready = not reasons
            pairs.append(dict(group=group, baseline=baseline, follow_up=follow, checks=checks,
                              comparable=ready, withheld_reasons=reasons,
                              primary_delta=follow['primary']['value']-baseline['primary']['value'] if ready else None,
                              counter_delta=follow['counter']['value']-baseline['counter']['value'] if ready else None))
        return dict(study_id=key, version=study['version'],
                    contract={k: v for k, v in study.items() if k not in {'events', 'version'}}, groups=pairs,
                    ready_for_rehearsal=bool(pairs) and all(p['comparable'] for p in pairs),
                    causal_effect_estimated=False, case_mix_controlled=False, execution_authorized=False,
                    layer_a_status='LEGAL_REVIEW_REQUIRED', institutional_acceptance='NOT_ESTABLISHED',
                    method='Fictional aggregate records only. Delta is follow-up minus baseline; it is not causal attribution, statistical significance or evidence of human benefit. Local checks do not authenticate sources or qualified acceptance.')

    def dependencies_at(self, trial, db):
        dates = []
        for key in trial['study_ids']:
            study = self.entity(key, db, 'study')
            dates.extend([study['at'], *[e['at'] for e in study['events']]])
            for event in study['events']:
                if event['kind'] == 'OBSERVATION':
                    for pin in event['pins']:
                        source = self.evidence(pin['evidence_id'], db)
                        dates.extend([source['revisions'][-1]['at'], *[r['at'] for r in source['reviews']]])
        return max(dates, key=timestamp)

    def context(self, trial, db):
        studies, evidence = [], {}
        for key in trial['study_ids']:
            study = self.entity(key, db, 'study')
            studies.append(dict(study_id=key, version=study['version']))
            for event in study['events']:
                if event['kind'] == 'OBSERVATION':
                    for pin in event['pins']:
                        source = self.evidence(pin['evidence_id'], db)
                        evidence[pin['evidence_id']] = dict(revision=source['current_revision'],
                            reviews=len(source['reviews']), locally_reviewed=source['locally_reviewed'])
        return dict(studies=studies, evidence=evidence)

    @staticmethod
    def stage(events):
        records = [e for e in events if e['action'] in {'RECORD', 'REOPEN', 'ROLLBACK'}]
        if not records:
            return 'DRAFT', None
        last = records[-1]
        if last['action'] == 'REOPEN':
            return 'DRAFT', None
        return ('ROLLED_BACK' if last['action'] == 'ROLLBACK' else last['status']), last

    def report_trial(self, key, db=None):
        if db is None:
            with self.store.connect() as conn:
                return self.report_trial(key, conn)
        trial = self.entity(key, db, 'trial')
        context = self.context(trial, db)
        digest = fingerprint(context)
        stage, current = self.stage(trial['events'])
        checks = [e for e in trial['events'] if e['action'] == 'CHECK' and current and
                  e['target_sequence'] == current['sequence']]
        return dict(trial_id=key, version=trial['version'], contract={k:v for k,v in trial.items() if k not in {'version', 'events'}}, stage=stage, context=context, context_sha256=digest,
                    study_readiness={s: self.report_study(s, db)['ready_for_rehearsal'] for s in trial['study_ids']},
                    stage_checked=bool(checks and checks[-1]['passed'] and checks[-1]['context_sha256'] == digest),
                    stale_event_sequences=[e['sequence'] for e in trial['events'] if e['context_sha256'] != digest],
                    events=trial['events'], execution_authorized=False, layer_a_status='LEGAL_REVIEW_REQUIRED',
                    live_transition_authorized=False, institutional_adoption_established=False,
                    notice='Rehearsal/learning records only. Source/outcome changes invalidate earlier context. Reopen and recheck; no local pass clears Layer A or authorizes a live intervention.')

    def bootstrap(self):
        with self.store.connect() as db:
            return dict(evidence=[self.evidence(r['id'], db) for r in db.execute('SELECT DISTINCT id FROM layer_documents ORDER BY id')],
                        studies=[self.entity(r['id'], db, 'study') for r in db.execute('SELECT id FROM layer_studies ORDER BY id')],
                        trials=[self.entity(r['id'], db, 'trial') for r in db.execute('SELECT id FROM layer_trials ORDER BY id')],
                        schemas=SCHEMAS, stages=STAGES)

    def record(self, kind, data):
        if kind not in SCHEMAS:
            raise ValueError('unknown C/D/E record kind')
        fields(data, SCHEMAS[kind]+' actor note at')
        actor, note = text(data['actor'], 'actor', 200), text(data['note'], 'evidence/reason/limitations')
        at = timestamp(data['at']).isoformat()
        common = dict(actor=actor, note=note, at=at)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if kind == 'EVIDENCE':
                key = identifier(data['evidence_id'])
                rows = [json.loads(r['body']) for r in db.execute('SELECT body FROM layer_documents WHERE id=? ORDER BY revision', (key,))]
                self.check_version(rows[-1]['revision'] if rows else 0, data['expected_revision'])
                text(data['content'], 'exact evidence text', 100000)
                origin = text(data['origin'], 'origin', 2000)
                confidence = text(data['confidence'], 'confidence', 1)
                if confidence not in {'A', 'B', 'C'}:
                    raise ValueError('confidence must be A/B/C')
                refs = data['corroborating_refs']
                if not isinstance(refs, list) or len(refs) > 20:
                    raise ValueError('bounded corroborating reference list required')
                refs = [text(r, 'corroborating reference', 2000) for r in refs]
                if len(set(refs)) != len(refs):
                    raise ValueError('duplicate corroborating reference')
                verification = data['verification_reference']
                if verification is not None:
                    verification = text(verification, 'asserted verification reference', 2000)
                if confidence == 'A' and not verification:
                    raise ValueError('A needs an asserted verification reference')
                if confidence == 'B' and len(set([origin, *refs])) < 2:
                    raise ValueError('B needs distinct corroborating references')
                self.chronology(at, [*rows, *self.events(db, 'D_REVIEW', key)], at)
                revision = len(rows)+1
                body = dict(evidence_id=key, revision=revision, content=data['content'], origin=origin,
                    confidence=confidence, corroborating_refs=refs, verification_reference=verification,
                    limitations=text(data['limitations'], 'limitations'),
                    sha256=hashlib.sha256(data['content'].encode()).hexdigest(), **common)
                db.execute('INSERT INTO layer_documents VALUES (?,?,?)', (key, revision, json.dumps(body)))
                result = self.evidence(key, db)
            elif kind == 'EVIDENCE_REVIEW':
                key = identifier(data['evidence_id'])
                source = self.evidence(key, db)
                self.check_version(source['current_revision'], data['revision'])
                if type(data['passed']) is not bool:
                    raise ValueError('boolean passed required')
                if actor == source['revisions'][-1]['actor']:
                    raise ValueError('evidence reviewer must differ from current recorder')
                self.chronology(at, source['reviews'], source['revisions'][-1]['at'])
                self.append(db, 'D_REVIEW', key, dict(revision=data['revision'], passed=data['passed'], **common))
                result = self.evidence(key, db)
            elif kind in {'STUDY', 'TRIAL'}:
                is_study = kind == 'STUDY'
                id_field, table = ('study_id', 'layer_studies') if is_study else ('trial_id', 'layer_trials')
                key = identifier(data[id_field])
                if db.execute('SELECT id FROM '+table+' WHERE id=?', (key,)).fetchone():
                    raise Conflict('record exists; use a new ID for a new contract')
                body = {k: text(data[k], k, 2000) for k in SCHEMAS[kind].split() if k not in {id_field, 'study_ids'}}
                body.update({id_field: key}, **common)
                if is_study:
                    if body['kind'] not in {'COUNT', 'PROPORTION'} or body['counter_kind'] not in {'COUNT', 'PROPORTION'}:
                        raise ValueError('measure kinds are COUNT/PROPORTION')
                else:
                    ids = data['study_ids']
                    if not isinstance(ids, list) or not 1 <= len(ids) <= 20 or any(not isinstance(s, str) for s in ids) or len(set(ids)) != len(ids):
                        raise ValueError('one through twenty distinct study IDs required')
                    for sid in ids:
                        self.entity(identifier(sid), db, 'study')
                    body['study_ids'] = ids
                    self.chronology(at, [], self.dependencies_at(body, db))
                db.execute('INSERT INTO '+table+' VALUES (?,?,1)', (key, json.dumps(body)))
                result = self.entity(key, db, 'study') if is_study else self.report_trial(key, db)
            elif kind in {'OBSERVATION', 'OUTCOME_REVIEW'}:
                key = identifier(data['study_id'])
                study = self.entity(key, db, 'study')
                self.check_version(study['version'], data['version'])
                self.chronology(at, study['events'], study['at'])
                if kind == 'OBSERVATION':
                    phase, group = text(data['phase'], 'phase', 100), text(data['group'], 'aggregate group', 200)
                    if phase not in {'BASELINE', 'FOLLOW_UP'}:
                        raise ValueError('phase must be BASELINE/FOLLOW_UP')
                    start, end = timestamp(data['window_start']), timestamp(data['window_end'])
                    if end <= start or end > timestamp(at):
                        raise ValueError('observation window must end after start and not after recording time')
                    primary = measure(study['kind'], data['primary_numerator'], data['primary_denominator'], data['primary_missing'])
                    counter = measure(study['counter_kind'], data['counter_numerator'], data['counter_denominator'], data['counter_missing'])
                    pins = data['pins']
                    if not isinstance(pins, list) or not 1 <= len(pins) <= 20:
                        raise ValueError('one through twenty evidence pins required')
                    resolved, seen = [], set()
                    for pin in pins:
                        fields(pin, 'evidence_id revision')
                        pid = identifier(pin['evidence_id'])
                        source = self.evidence(pid, db)
                        self.check_version(source['current_revision'], pin['revision'])
                        self.chronology(at, source['reviews'], source['revisions'][-1]['at'])
                        if pid in seen:
                            raise ValueError('duplicate evidence pin')
                        seen.add(pid)
                        resolved.append(dict(evidence_id=pid, revision=pin['revision'], sha256=source['revisions'][-1]['sha256']))
                    self.append(db, 'C', key, dict(kind=kind, phase=phase, group=group,
                        window_start=start.isoformat(), window_end=end.isoformat(), primary=primary, counter=counter,
                        pins=resolved, **common))
                else:
                    bounded(data['observation_sequence'], 'observation sequence', 1, 1000000)
                    if type(data['passed']) is not bool:
                        raise ValueError('boolean passed required')
                    observation = next((e for e in study['events'] if e['kind'] == 'OBSERVATION' and e['sequence'] == data['observation_sequence']), None)
                    if not observation:
                        raise ValueError('observation not found')
                    latest = [e for e in study['events'] if e['kind'] == 'OBSERVATION' and e['phase'] == observation['phase'] and e['group'] == observation['group']][-1]
                    if latest['sequence'] != observation['sequence']:
                        raise Conflict('observation was superseded')
                    if actor == observation['actor']:
                        raise ValueError('outcome reviewer must differ from observation recorder')
                    for pin in observation['pins']:
                        source = self.evidence(pin['evidence_id'], db)
                        self.chronology(at, source['reviews'], source['revisions'][-1]['at'])
                    if data['passed'] and not all(self.pin_status(p, db) for p in observation['pins']):
                        raise ValueError('passing outcome review requires current locally reviewed evidence')
                    self.append(db, 'C', key, dict(kind=kind, observation_sequence=observation['sequence'], passed=data['passed'], **common))
                db.execute('UPDATE layer_studies SET version=version+1 WHERE id=?', (key,))
                result = self.report_study(key, db)
            else:
                key = identifier(data['trial_id'])
                trial = self.entity(key, db, 'trial')
                self.check_version(trial['version'], data['version'])
                self.chronology(at, trial['events'], trial['at'])
                self.chronology(at, [], self.dependencies_at(trial, db))
                action = text(data['action'], 'trial action', 100)
                stage, current = self.stage(trial['events'])
                context = self.context(trial, db)
                digest = fingerprint(context)
                if action == 'CHECK':
                    if type(data['target_sequence']) is not int or type(data['passed']) is not bool or data['status'] is not None:
                        raise ValueError('CHECK requires sequence/boolean and null status')
                    if not current or current['action'] != 'RECORD' or current['sequence'] != data['target_sequence']:
                        raise Conflict('check must reference current recorded stage')
                    if current['context_sha256'] != digest:
                        raise Conflict('stage context is stale; reopen')
                    if current['actor'] == actor:
                        raise ValueError('trial checker must differ from stage recorder')
                elif action == 'RECORD':
                    if data['target_sequence'] is not None or data['passed'] is not None:
                        raise ValueError('RECORD has null check fields')
                    if stage == 'ROLLED_BACK' or STAGES.index(stage) == len(STAGES)-1 or data['status'] != STAGES[STAGES.index(stage)+1]:
                        raise ValueError('record the next rehearsal stage')
                    if current:
                        checks = [e for e in trial['events'] if e['action'] == 'CHECK' and e['target_sequence'] == current['sequence']]
                        if current['context_sha256'] != digest or not checks or not checks[-1]['passed'] or checks[-1]['context_sha256'] != digest:
                            raise ValueError('prior phase needs a separate passing check for current context')
                    if STAGES.index(data['status']) >= STAGES.index('REHEARSAL_RECORDED') and not all(self.report_study(s, db)['ready_for_rehearsal'] for s in trial['study_ids']):
                        raise ValueError('rehearsal requires complete current checked outcome/counter-measure pairs')
                elif action in {'REOPEN', 'ROLLBACK'}:
                    if any(data[k] is not None for k in ('status', 'target_sequence', 'passed')):
                        raise ValueError('reopen/rollback has null stage/check fields')
                    if action == 'ROLLBACK' and stage not in STAGES[3:]:
                        raise ValueError('rollback applies only to a recorded rehearsal or later phase')
                else:
                    raise ValueError('trial action must be RECORD/CHECK/REOPEN/ROLLBACK')
                self.append(db, 'E', key, dict(action=action, status=data['status'], target_sequence=data['target_sequence'],
                    passed=data['passed'], context=context, context_sha256=digest, **common))
                db.execute('UPDATE layer_trials SET version=version+1 WHERE id=?', (key,))
                result = self.report_trial(key, db)
            self.store.log(db, actor, 'synthetic_layer_'+kind.lower(), key, common)
            return result
