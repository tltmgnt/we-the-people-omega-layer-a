"""Synthetic sanitation route runs, verification and anonymous service reports."""
from .maintenance import fields, identifier
from .permits import statistic, timestamp
from .store import Conflict, now, text

STREAMS = {'TRASH', 'RECYCLING', 'SANITATION'}


def count(value, name, minimum=0, maximum=1_000_000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be an integer from {minimum} to {maximum}')
    return value


class Sanitation:
    def __init__(self, store):
        self.store = store

    def routes(self):
        with self.store.connect() as db:
            return [{**dict(r), 'kind': 'SYNTHETIC'} for r in db.execute('SELECT * FROM sanitation_routes ORDER BY id')]

    def create_route(self, data):
        fields(data, 'route_id stream area expected_stops at actor evidence')
        route_id = identifier(data['route_id'])
        stream = text(data['stream'], 'service stream', 100)
        if stream not in STREAMS:
            raise ValueError('stream must be TRASH, RECYCLING or SANITATION')
        stops = count(data['expected_stops'], 'expected stops', 1)
        area, actor = text(data['area'], 'fictional area', 100), text(data['actor'], 'actor', 200)
        evidence, at = text(data['evidence'], 'route evidence'), timestamp(data['at']).isoformat()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM sanitation_routes WHERE id=?', (route_id,)).fetchone():
                raise Conflict('synthetic route already exists')
            db.execute('INSERT INTO sanitation_routes VALUES (?,?,?,?,?,?,?)', (route_id,stream,area,stops,at,actor,evidence))
            self.store.log(db,actor,'create_synthetic_route',route_id,data)
            return {**data,'id':route_id,'kind':'SYNTHETIC'}

    def run(self, run_id, db=None):
        if db is None:
            with self.store.connect() as connection:
                return self.run(run_id,connection)
        row=db.execute('''SELECT r.*, t.area,t.stream FROM sanitation_runs r
                         JOIN sanitation_routes t ON r.route_id=t.id WHERE r.id=?''',(run_id,)).fetchone()
        if not row:
            raise KeyError('synthetic service run not found')
        events=[dict(r) for r in db.execute('SELECT * FROM sanitation_events WHERE run_id=? ORDER BY sequence',(run_id,))]
        checks=[dict(r) for r in db.execute('SELECT * FROM sanitation_checks WHERE run_id=? ORDER BY sequence',(run_id,))]
        latest=events[-1];check=checks[-1] if checks else None
        verified=bool(check and check['event_sequence']==latest['sequence'] and check['observed_total']==latest['served_total'])
        status=latest['stage']
        if latest['served_total'] is not None:
            status=('VERIFIED_COMPLETE' if latest['served_total']==row['expected_stops'] else 'VERIFIED_SHORTFALL') if verified else 'AWAITING_VERIFICATION'
        return {**dict(row),'events':events,'checks':checks,'status':status,'verified':verified,
                'kind':'SYNTHETIC','execution_authorized':False}

    def runs(self):
        with self.store.connect() as db:
            return [self.run(r['id'],db) for r in db.execute('SELECT id FROM sanitation_runs ORDER BY id')]

    def create_run(self,data):
        fields(data,'run_id route_id at actor evidence')
        run_id,route_id=identifier(data['run_id']),identifier(data['route_id'])
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'schedule evidence')
        at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            route=db.execute('SELECT * FROM sanitation_routes WHERE id=?',(route_id,)).fetchone()
            if not route:raise KeyError('register the fictional route first')
            if at<timestamp(route['at']):raise ValueError('run precedes route registration')
            if db.execute('SELECT id FROM sanitation_runs WHERE id=?',(run_id,)).fetchone():raise Conflict('synthetic run already exists')
            db.execute('INSERT INTO sanitation_runs VALUES (?,?,?,1)',(run_id,route_id,route['expected_stops']))
            db.execute('INSERT INTO sanitation_events VALUES (?,1,?,?,?,?,?)',(run_id,'SCHEDULED',at.isoformat(),actor,None,evidence))
            self.store.log(db,actor,'create_synthetic_service_run',run_id,data)
            return self.run(run_id,db)

    def advance(self,run_id,data):
        fields(data,'version stage at actor served_total evidence')
        if type(data['version']) is not int:raise ValueError('integer version required')
        stage=text(data['stage'],'stage',100);actor=text(data['actor'],'actor',200)
        evidence=text(data['evidence'],'service evidence');at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');run=self.run(run_id,db);last=run['events'][-1]
            if run['version']!=data['version']:raise Conflict('Run changed. Reload before saving.')
            allowed={'SCHEDULED':{'STARTED'},'STARTED':{'SERVICE_RECORDED'},'SERVICE_RECORDED':{'CORRECTION_RECORDED'},'CORRECTION_RECORDED':{'CORRECTION_RECORDED'}}
            if stage not in allowed[last['stage']]:raise ValueError('invalid synthetic service transition')
            if at<timestamp(last['at']) or (run['checks'] and at<timestamp(run['checks'][-1]['at'])):raise ValueError('event precedes latest service event or verification')
            served=data['served_total']
            if stage=='STARTED':
                if served is not None:raise ValueError('service count is unknown at STARTED')
            else:served=count(served,'cumulative served stops',0,run['expected_stops'])
            db.execute('INSERT INTO sanitation_events VALUES (?,?,?,?,?,?,?)',(run_id,len(run['events'])+1,stage,at.isoformat(),actor,served,evidence))
            db.execute('UPDATE sanitation_runs SET version=version+1 WHERE id=?',(run_id,))
            self.store.log(db,actor,'record_synthetic_sanitation_service',run_id,data)
            return self.run(run_id,db)

    def verify(self,run_id,data):
        fields(data,'version at verifier observed_total evidence')
        if type(data['version']) is not int:raise ValueError('integer version required')
        actor,evidence=text(data['verifier'],'verifier',200),text(data['evidence'],'verification evidence')
        at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');run=self.run(run_id,db);last=run['events'][-1]
            if run['version']!=data['version']:raise Conflict('Run changed. Reload before verification.')
            if last['served_total'] is None:raise ValueError('record service before verification')
            observed=count(data['observed_total'],'observed served stops',0,run['expected_stops'])
            if actor==last['actor']:raise ValueError('use a distinct verifier identifier from the current service recorder')
            if at<timestamp(last['at']) or (run['checks'] and at<timestamp(run['checks'][-1]['at'])):raise ValueError('verification precedes latest event or check')
            db.execute('INSERT INTO sanitation_checks VALUES (?,?,?,?,?,?,?)',(run_id,len(run['checks'])+1,last['sequence'],at.isoformat(),actor,observed,evidence))
            db.execute('UPDATE sanitation_runs SET version=version+1 WHERE id=?',(run_id,))
            self.store.log(db,actor,'verify_synthetic_sanitation_service',run_id,data)
            return self.run(run_id,db)

    def issue(self,issue_id,db=None):
        if db is None:
            with self.store.connect() as connection:return self.issue(issue_id,connection)
        row=db.execute('SELECT * FROM sanitation_issues WHERE id=?',(issue_id,)).fetchone()
        if not row:raise KeyError('synthetic missed-service report not found')
        events=[dict(r) for r in db.execute('SELECT * FROM sanitation_issue_events WHERE issue_id=? ORDER BY sequence',(issue_id,))]
        return {**dict(row),'events':events,'status':events[-1]['status'],'kind':'SYNTHETIC'}

    def issues(self):
        with self.store.connect() as db:return [self.issue(r['id'],db) for r in db.execute('SELECT id FROM sanitation_issues ORDER BY id')]

    def create_issue(self,data):
        fields(data,'issue_id run_id description at actor evidence')
        issue_id,run_id=identifier(data['issue_id']),identifier(data['run_id'])
        description=text(data['description'],'anonymous scenario');actor=text(data['actor'],'actor',200)
        evidence=text(data['evidence'],'report evidence');at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');run=self.run(run_id,db)
            service=[e for e in run['events'] if e['served_total'] is not None]
            if not service or at<timestamp(service[0]['at']):raise ValueError('missed-service report must follow the first recorded service')
            if db.execute('SELECT id FROM sanitation_issues WHERE id=?',(issue_id,)).fetchone():raise Conflict('synthetic report already exists')
            db.execute('INSERT INTO sanitation_issues VALUES (?,?,?,1)',(issue_id,run_id,description))
            db.execute('INSERT INTO sanitation_issue_events VALUES (?,1,?,?,?,?)',(issue_id,'OPEN',at.isoformat(),actor,evidence))
            self.store.log(db,actor,'create_synthetic_missed_service_report',issue_id,data)
            return self.issue(issue_id,db)

    def update_issue(self,issue_id,data):
        fields(data,'version status at actor evidence')
        if type(data['version']) is not int:raise ValueError('integer version required')
        status=text(data['status'],'report status',100);actor=text(data['actor'],'actor',200)
        evidence=text(data['evidence'],'response evidence');at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');issue=self.issue(issue_id,db)
            if issue['version']!=data['version']:raise Conflict('Report changed. Reload before saving.')
            if status!=('RESOLVED' if issue['status']=='OPEN' else 'OPEN'):raise ValueError('report must alternate OPEN and RESOLVED')
            if at<timestamp(issue['events'][-1]['at']):raise ValueError('response precedes previous report event')
            db.execute('INSERT INTO sanitation_issue_events VALUES (?,?,?,?,?,?)',(issue_id,len(issue['events'])+1,status,at.isoformat(),actor,evidence))
            db.execute('UPDATE sanitation_issues SET version=version+1 WHERE id=?',(issue_id,))
            self.store.log(db,actor,'respond_to_synthetic_service_report',issue_id,data)
            return self.issue(issue_id,db)

    def report(self,as_of=None,area=None,stream=None):
        at=timestamp(as_of or now());expected=missed=verified=unverified=scheduled=0
        included=set();service_revisions=0;recoveries=[]
        for run in self.runs():
            if (area and run['area']!=area) or (stream and run['stream']!=stream):continue
            events=[e for e in run['events'] if timestamp(e['at'])<=at]
            if not events:continue
            included.add(run['id']);last=events[-1]
            service_revisions+=sum(e['stage']=='CORRECTION_RECORDED' for e in events)
            if last['served_total'] is None:scheduled+=1;continue
            checks=[c for c in run['checks'] if c['event_sequence']==last['sequence'] and timestamp(c['at'])<=at]
            if checks and checks[-1]['observed_total']==last['served_total']:
                verified+=1;expected+=run['expected_stops'];missed+=run['expected_stops']-last['served_total']
                shortfalls=[e for e in events if e['served_total'] is not None and e['served_total']<run['expected_stops']]
                if shortfalls and last['served_total']==run['expected_stops']:
                    recoveries.append((timestamp(checks[-1]['at'])-timestamp(shortfalls[0]['at'])).total_seconds()/3600)
            else:unverified+=1
        resolved=[];open_ages=[];repeat=reports=0
        for issue in self.issues():
            if issue['run_id'] not in included:continue
            events=[e for e in issue['events'] if timestamp(e['at'])<=at]
            if not events:continue
            reports+=1;repeat+=sum(e['status']=='OPEN' for e in events[1:])
            start=timestamp(events[0]['at']);last=events[-1]
            if last['status']=='RESOLVED':resolved.append((timestamp(last['at'])-start).total_seconds()/3600)
            else:open_ages.append((at-start).total_seconds()/3600)
        return {'kind':'SYNTHETIC','as_of':at.isoformat(),'area':area,'stream':stream,'runs':len(included),
                'verified_runs':verified,'unverified_recorded_runs':unverified,'runs_without_service_record':scheduled,
                'verified_expected_stop_visits':expected,'verified_missed_stop_visits':missed,
                'verified_missed_service_rate':missed/expected if expected else None,
                'service_correction_records':service_revisions,'anonymous_reports':reports,'repeat_report_events':repeat,
                'verified_recovery_hours':statistic(recoveries),
                'open_reports':len(open_ages),'resolved_report_hours':statistic(resolved),'open_report_age_hours':statistic(open_ages),
                'execution_authorized':False,
                'method':'Latest service record per run at cutoff, with a matching current-version check. Denominator is scheduled stop-visits for verified runs only, not households; unverified runs are excluded explicitly. Reports may duplicate observations and never determine the missed-service denominator. Response time uses original report to latest recorded resolution; open reports are censored. Counts and verifier identities are local assertions. No household-level data, actual collection, dispatch or independent service finding.'}
