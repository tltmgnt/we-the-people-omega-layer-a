"""Synthetic utility interruptions, restoration checks and aggregate burden."""
from .maintenance import fields,identifier
from .permits import statistic,timestamp
from .sanitation import count
from .store import Conflict,now,text

STAGES={'REPORTED':{'ASSESSED'},'ASSESSED':{'ASSESSED','WORK_IN_PROGRESS'},
        'WORK_IN_PROGRESS':{'WORK_IN_PROGRESS','RESTORATION_RECORDED'},
        'RESTORATION_RECORDED':{'WORK_IN_PROGRESS','CLOSED'},
        'CLOSED':{'REOPENED'},'REOPENED':{'ASSESSED'}}


def optional_count(value,name,maximum=1_000_000):
    return None if value is None else count(value,name,0,maximum)


class Utilities:
    def __init__(self,store):self.store=store

    def assets(self):
        with self.store.connect() as db:return [{**dict(r),'kind':'SYNTHETIC'} for r in db.execute('SELECT * FROM utility_assets ORDER BY id')]

    def create_asset(self,data):
        fields(data,'asset_id utility area connection_count at actor evidence');asset_id=identifier(data['asset_id'])
        utility=text(data['utility'],'utility category',100)
        if utility not in {'WATER','SEWER','POWER','OTHER'}:raise ValueError('invalid utility category')
        area=text(data['area'],'fictional area',100);connections=optional_count(data['connection_count'],'asset connection count')
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'fictional asset evidence');at=timestamp(data['at']).isoformat()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM utility_assets WHERE id=?',(asset_id,)).fetchone():raise Conflict('synthetic utility asset already exists')
            db.execute('INSERT INTO utility_assets VALUES (?,?,?,?,?,?,?)',(asset_id,utility,area,connections,at,actor,evidence))
            self.store.log(db,actor,'register_synthetic_utility_asset',asset_id,data)
            return {**data,'id':asset_id,'kind':'SYNTHETIC'}

    def incident(self,incident_id,db=None):
        if db is None:
            with self.store.connect() as connection:return self.incident(incident_id,connection)
        row=db.execute('''SELECT i.*,a.utility,a.area,a.connection_count FROM utility_incidents i
                          JOIN utility_assets a ON i.asset_id=a.id WHERE i.id=?''',(incident_id,)).fetchone()
        if not row:raise KeyError('synthetic utility incident not found')
        events=[dict(r) for r in db.execute('SELECT * FROM utility_events WHERE incident_id=? ORDER BY sequence',(incident_id,))]
        checks=[dict(r) for r in db.execute('SELECT * FROM utility_checks WHERE incident_id=? ORDER BY sequence',(incident_id,))]
        return {**dict(row),'events':events,'checks':checks,'stage':events[-1]['stage'],
                'allowed_next_stages':sorted(STAGES[events[-1]['stage']]),'kind':'SYNTHETIC','execution_authorized':False}

    def incidents(self):
        with self.store.connect() as db:return [self.incident(r['id'],db) for r in db.execute('SELECT id FROM utility_incidents ORDER BY id')]

    def create_incident(self,data):
        fields(data,'incident_id asset_id started_at at affected_connections severity escalation_reference actor evidence')
        incident_id,asset_id=identifier(data['incident_id']),identifier(data['asset_id'])
        started,at=timestamp(data['started_at']),timestamp(data['at'])
        if started>at:raise ValueError('interruption start follows report time')
        severity=text(data['severity'],'scenario severity',100)
        if severity not in {'ROUTINE','URGENT','SAFETY_REVIEW'}:raise ValueError('invalid scenario severity')
        escalation=data['escalation_reference']
        if escalation is not None:escalation=text(escalation,'fictional escalation-route reference',2000)
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'interruption and initial-count evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');asset=db.execute('SELECT * FROM utility_assets WHERE id=?',(asset_id,)).fetchone()
            if not asset:raise KeyError('register the fictional utility asset first')
            if started<timestamp(asset['registered_at']):raise ValueError('interruption predates asset registration in this prototype')
            affected=optional_count(data['affected_connections'],'affected connections',asset['connection_count'] if asset['connection_count'] is not None else 1_000_000)
            if db.execute('SELECT id FROM utility_incidents WHERE id=?',(incident_id,)).fetchone():raise Conflict('synthetic incident already exists')
            db.execute('INSERT INTO utility_incidents VALUES (?,?,?,?,?,1)',(incident_id,asset_id,started.isoformat(),severity,escalation))
            db.execute('INSERT INTO utility_events VALUES (?,1,?,?,?,?,?,?,?)',(incident_id,'REPORTED',at.isoformat(),affected,None,escalation,actor,evidence))
            self.store.log(db,actor,'report_synthetic_utility_interruption',incident_id,data)
            return self.incident(incident_id,db)

    def advance(self,incident_id,data):
        fields(data,'version stage at affected_connections work_order_reference escalation_reference actor evidence')
        if type(data['version']) is not int:raise ValueError('integer version required')
        stage=text(data['stage'],'stage',100);at=timestamp(data['at'])
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'stage and count evidence')
        work=data['work_order_reference']
        if stage=='WORK_IN_PROGRESS':work=text(work,'fictional work-order reference',2000)
        elif work is not None:raise ValueError('work-order reference is recorded only during WORK_IN_PROGRESS')
        escalation=data['escalation_reference']
        if escalation is not None:
            if stage!='ASSESSED':raise ValueError('escalation-route updates belong only to ASSESSED')
            escalation=text(escalation,'fictional escalation-route reference',2000)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');incident=self.incident(incident_id,db)
            if incident['version']!=data['version']:raise Conflict('Incident changed. Reload before saving.')
            if stage not in STAGES[incident['stage']]:raise ValueError('invalid synthetic utility transition')
            if at<timestamp(incident['events'][-1]['at']) or (incident['checks'] and at<timestamp(incident['checks'][-1]['at'])):raise ValueError('stage precedes latest event or quality check')
            affected=optional_count(data['affected_connections'],'affected connections',incident['connection_count'] if incident['connection_count'] is not None else 1_000_000)
            if stage in {'RESTORATION_RECORDED','CLOSED'} and affected!=0:raise ValueError('restoration/closure requires explicit zero affected connections, not an unknown count')
            if stage=='CLOSED':
                matching=[c for c in incident['checks'] if c['restoration_sequence']==incident['events'][-1]['sequence']]
                if not matching or not matching[-1]['passed'] or matching[-1]['quality_status']!='MEETS_SCENARIO':raise ValueError('closure requires a passing quality-evidence check meeting declared scenario criteria for this restoration record')
            db.execute('INSERT INTO utility_events VALUES (?,?,?,?,?,?,?,?,?)',(incident_id,len(incident['events'])+1,stage,at.isoformat(),affected,work,escalation,actor,evidence))
            db.execute('UPDATE utility_incidents SET version=version+1 WHERE id=?',(incident_id,))
            self.store.log(db,actor,'advance_synthetic_utility_incident',incident_id,data)
            return self.incident(incident_id,db)

    def verify(self,incident_id,data):
        fields(data,'version at verifier passed quality_status criteria_reference evidence')
        if type(data['version']) is not int or type(data['passed']) is not bool:raise ValueError('integer version and boolean passed required')
        at=timestamp(data['at']);actor=text(data['verifier'],'verifier',200)
        quality=text(data['quality_status'],'scenario quality assertion',100)
        if quality not in {'MEETS_SCENARIO','DOES_NOT_MEET','UNKNOWN'}:raise ValueError('invalid quality assertion')
        criteria=text(data['criteria_reference'],'declared fictional criteria reference',2000)
        evidence=text(data['evidence'],'quality-evidence check')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');incident=self.incident(incident_id,db)
            if incident['version']!=data['version']:raise Conflict('Incident changed. Reload before checking.')
            if incident['stage']!='RESTORATION_RECORDED':raise ValueError('record the current restoration before its quality check')
            last=incident['events'][-1]
            if actor==last['actor']:raise ValueError('use a distinct verifier identifier from the restoration recorder')
            if at<timestamp(last['at']) or (incident['checks'] and at<timestamp(incident['checks'][-1]['at'])):raise ValueError('quality check precedes latest event or check')
            db.execute('INSERT INTO utility_checks VALUES (?,?,?,?,?,?,?,?,?)',(incident_id,len(incident['checks'])+1,last['sequence'],at.isoformat(),actor,int(data['passed']),quality,criteria,evidence))
            db.execute('UPDATE utility_incidents SET version=version+1 WHERE id=?',(incident_id,))
            self.store.log(db,actor,'check_synthetic_utility_restoration_quality',incident_id,data)
            return self.incident(incident_id,db)

    def report(self,as_of=None,area=None,utility=None):
        at=timestamp(as_of or now());assets=[a for a in self.assets() if timestamp(a['registered_at'])<=at and (not area or a['area']==area) and (not utility or a['utility']==utility)]
        t=dict(assets=len(assets),incidents=0,open_incidents=0,closed_incidents=0,closed_restoration_cycles=0,
               reopen_events=0,unclosed_restoration_records=0,failed_or_unknown_quality_checks=0,
               missing_safety_escalation_references=0,known_burden_intervals=0,unknown_burden_intervals=0)
        durations=[];verification_lags=[];cycle_ages=[];original_ages=[];known_burden=0
        for incident in self.incidents():
            if (area and incident['area']!=area) or (utility and incident['utility']!=utility):continue
            events=[e for e in incident['events'] if timestamp(e['at'])<=at]
            if not events:continue
            t['incidents']+=1;last=events[-1];checks=[c for c in incident['checks'] if timestamp(c['at'])<=at]
            t['closed_incidents' if last['stage']=='CLOSED' else 'open_incidents']+=1
            escalation_refs=[e['escalation_reference'] for e in events if e['escalation_reference']]
            if incident['severity']=='SAFETY_REVIEW' and not escalation_refs:t['missing_safety_escalation_references']+=1
            t['failed_or_unknown_quality_checks']+=sum(not c['passed'] or c['quality_status']!='MEETS_SCENARIO' for c in checks)
            if last['stage']=='RESTORATION_RECORDED':t['unclosed_restoration_records']+=1
            cycle_start=timestamp(incident['started_at']);restoration=None
            for index,event in enumerate(events):
                if event['stage']=='REOPENED':cycle_start=timestamp(event['at']);t['reopen_events']+=1;restoration=None
                elif event['stage']=='RESTORATION_RECORDED':restoration=event
                elif event['stage']=='WORK_IN_PROGRESS':restoration=None
                elif event['stage']=='CLOSED' and restoration:
                    matching=[c for c in checks if c['restoration_sequence']==restoration['sequence'] and timestamp(c['at'])<=timestamp(event['at'])]
                    if matching and matching[-1]['passed'] and matching[-1]['quality_status']=='MEETS_SCENARIO':
                        t['closed_restoration_cycles']+=1;durations.append((timestamp(restoration['at'])-cycle_start).total_seconds()/3600)
                        verification_lags.append((timestamp(matching[-1]['at'])-timestamp(restoration['at'])).total_seconds()/3600)
                start=timestamp(incident['started_at']) if index==0 else timestamp(event['at'])
                end=timestamp(events[index+1]['at']) if index+1<len(events) else at
                hours=(end-start).total_seconds()/3600
                if hours>0:
                    if event['affected_connections'] is None:t['unknown_burden_intervals']+=1
                    else:t['known_burden_intervals']+=1;known_burden+=hours*event['affected_connections']
            if last['stage']!='CLOSED':
                cycle_ages.append((at-cycle_start).total_seconds()/3600)
                original_ages.append((at-timestamp(incident['started_at'])).total_seconds()/3600)
        return {'kind':'SYNTHETIC','as_of':at.isoformat(),'area':area,'utility':utility,**t,
                'checked_restoration_cycle_hours':statistic(durations),'quality_verification_lag_hours':statistic(verification_lags),
                'open_cycle_age_hours':statistic(cycle_ages),'open_incident_original_age_hours':statistic(original_ages),
                'reported_incident_connection_hours':known_burden if not t['unknown_burden_intervals'] and t['incidents'] else None,
                'known_interval_connection_hours':known_burden if t['known_burden_intervals'] else None,'execution_authorized':False,
                'method':'UTC scenario times. Completed cycle duration runs from initial interruption or explicit reopening to its recorded restoration, only after a passing scenario-quality check and closure. Prior completed cycles remain visible after reopening. Open-cycle and original-incident ages are censored separately. Reported connection-hours integrate asserted counts over each incident; the initial count applies from declared start. Unknown intervals prevent a complete burden total. Concurrent incidents may overlap: incident-associated connection-hours are not unique customers, SAIDI/SAIFI or network availability. Quality, criteria and verifier identities are local assertions, not real safety certification. No utility control, repair dispatch or escalation message occurs.'}
