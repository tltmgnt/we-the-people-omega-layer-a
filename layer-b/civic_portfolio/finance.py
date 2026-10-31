"""Synthetic category reconciliation, never payment or spending authority."""
import json
from .maintenance import fields, identifier
from .permits import timestamp, statistic
from .store import Conflict, text

CATEGORIES=('APPROPRIATION','ALLOCATION','OBLIGATION','EXPENDITURE','OUTLAY')

def amount(value):
    if type(value) is not int or abs(value)>10**12:
        raise ValueError('amount must be integer minor units within +/- 1000000000000')
    return value

class Finance:
    def __init__(self,store): self.store=store

    def ledger(self,key,db=None):
        if db is None:
            with self.store.connect() as c:return self.ledger(key,c)
        row=db.execute('SELECT * FROM finance_ledgers WHERE id=?',(key,)).fetchone()
        if not row:raise KeyError('synthetic ledger not found')
        result=dict(row)
        result['events']=[json.loads(r['body']) for r in db.execute('SELECT body FROM finance_events WHERE ledger_id=? ORDER BY sequence',(key,))]
        return result

    def ledgers(self):
        with self.store.connect() as db:return [self.ledger(r['id'],db) for r in db.execute('SELECT id FROM finance_ledgers ORDER BY id')]

    def create(self,data):
        fields(data,'ledger_id label currency minor_unit_digits period basis at actor')
        key=identifier(data['ledger_id'])
        values=[text(data[k],k,200) for k in ('label','currency','period','basis','actor')]
        if len(values[1])!=3 or not values[1].isascii() or not values[1].isupper() or not values[1].isalpha():raise ValueError('three uppercase currency letters required')
        digits=data['minor_unit_digits']
        if type(digits) is not int or digits not in range(5):raise ValueError('minor unit digits must be 0 through 4')
        at=timestamp(data['at']).isoformat()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM finance_ledgers WHERE id=?',(key,)).fetchone():raise Conflict('ledger exists')
            db.execute('INSERT INTO finance_ledgers VALUES (?,?,?,?,?,?,?,?,?,1)',(key,*values[:2],digits,*values[2:4],at,at,values[4]))
            self.store.log(db,values[4],'create_synthetic_finance_ledger',key,data)
            return self.ledger(key,db)

    def record(self,key,data):
        fields(data,'version kind category amount_minor reference note at actor')
        kind=text(data['kind'],'kind',100);category=data['category'];value=data['amount_minor']
        if kind not in {'ENTRY','RECONCILIATION','OUTCOME'}:raise ValueError('invalid record kind')
        if kind=='OUTCOME':
            if category is not None or value is not None:raise ValueError('outcome notes must not carry accounting amounts/categories')
        else:
            category=text(category,'category',100)
            if category not in CATEGORIES:raise ValueError('invalid accounting category')
            value=amount(value)
        reference=text(data['reference'],'fictional evidence reference',2000)
        note=text(data['note'],'evidence, discrepancy explanation or outcome limitation')
        actor=text(data['actor'],'actor',200);at=timestamp(data['at']).isoformat()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');ledger=self.ledger(key,db)
            if type(data['version']) is not int:raise ValueError('integer version required')
            if data['version']!=ledger['version']:raise Conflict('Ledger changed. Reload before saving.')
            if timestamp(at)<timestamp(ledger['last_at']):raise ValueError('record precedes latest ledger activity')
            entries=[e for e in ledger['events'] if e['kind']=='ENTRY' and e['category']==category]
            if kind=='ENTRY':amount(sum(e['amount_minor'] for e in entries)+value)
            if kind=='RECONCILIATION' and any(e['actor']==actor for e in entries):raise ValueError('use a reconciler distinct from all category entry recorders')
            event={**data,'at':at,'actor':actor,'category':category,'amount_minor':value,'reference':reference,'note':note,'sequence':len(ledger['events'])+1}
            event['entry_sequence']=max((e['sequence'] for e in entries),default=0) if kind=='RECONCILIATION' else None
            db.execute('INSERT INTO finance_events VALUES (?,?,?)',(key,event['sequence'],json.dumps(event)))
            db.execute('UPDATE finance_ledgers SET version=version+1,last_at=? WHERE id=?',(at,key))
            self.store.log(db,actor,'record_synthetic_finance_'+kind.lower(),key,event)
            return self.ledger(key,db)

    def report(self,key,as_of):
        at=timestamp(as_of);ledger=self.ledger(key)
        if at<timestamp(ledger['created_at']):raise ValueError('cutoff precedes ledger creation')
        events=[e for e in ledger['events'] if timestamp(e['at'])<=at];rows=[];ages=[]
        for category in CATEGORIES:
            entries=[e for e in events if e['kind']=='ENTRY' and e['category']==category]
            checks=[e for e in events if e['kind']=='RECONCILIATION' and e['category']==category]
            check=checks[-1] if checks else None;sequence=max((e['sequence'] for e in entries),default=0)
            total=sum(e['amount_minor'] for e in entries) if entries else None
            current=bool(check and check['entry_sequence']==sequence)
            delta=total-check['amount_minor'] if total is not None and current else None
            if entries and (not current or delta!=0):ages.append((at-timestamp(entries[0]['at'])).total_seconds()/3600)
            rows.append(dict(category=category,entry_count=len(entries),recorded_minor=total,comparison_minor=check['amount_minor'] if check else None,comparison_current=current,discrepancy_minor=delta,reconciliation_reference=check['reference'] if check else None))
        return dict(kind='SYNTHETIC',ledger_id=key,as_of=at.isoformat(),currency=ledger['currency'],minor_unit_digits=ledger['minor_unit_digits'],period=ledger['period'],basis=ledger['basis'],categories=rows,unresolved_category_age_hours=statistic(ages),outcome_notes=[e for e in events if e['kind']=='OUTCOME'],execution_authorized=False,institutional_acceptance='NOT_ESTABLISHED',method='Signed integer minor units. Categories are never added together. Missing entries/comparisons stay null. Latest comparison is current only for its exact category-entry sequence; later entries invalidate it even at the same timestamp. Discrepancy is recorded minus comparison, not proof of waste or misconduct. Unresolved age starts at first category entry, not a finding date. Period and basis are declared scenario labels; timestamps select recorded history. Outcome notes are unverified and separate from amounts. Identifiers are local assertions, not authenticated reviewers. No payments, tax calculation, budget approval or authoritative accounts.')
