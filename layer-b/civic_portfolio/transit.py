"""Fictional scheduled-trip reliability and accessibility counter-measures."""
import math

from .maintenance import fields, identifier
from .permits import statistic, timestamp
from .sanitation import count
from .store import Conflict, now, text

ACCESS_NEEDS={'MOBILITY','VISUAL','HEARING','COGNITIVE','OTHER'}


def minutes(value,name):
    if type(value) not in {int,float} or not math.isfinite(value) or not 0<=value<=1_000_000:
        raise ValueError(name+' must be a finite nonnegative number')
    return value


class Transit:
    def __init__(self,store):self.store=store

    def trip(self,trip_id,db=None):
        if db is None:
            with self.store.connect() as connection:return self.trip(trip_id,connection)
        row=db.execute('SELECT * FROM transit_trips WHERE id=?',(trip_id,)).fetchone()
        if not row:raise KeyError('synthetic transit trip not found')
        observations=[dict(r) for r in db.execute('SELECT * FROM transit_observations WHERE trip_id=? ORDER BY sequence',(trip_id,))]
        checks=[dict(r) for r in db.execute('SELECT * FROM transit_checks WHERE trip_id=? ORDER BY sequence',(trip_id,))]
        verified=bool(observations and checks and checks[-1]['observation_sequence']==observations[-1]['sequence'] and checks[-1]['passed'])
        status='SCHEDULED' if not observations else ('VERIFIED_' if verified else 'UNVERIFIED_')+observations[-1]['result']
        return {**dict(row),'observations':observations,'checks':checks,'verified':verified,'status':status,
                'kind':'SYNTHETIC','execution_authorized':False}

    def trips(self):
        with self.store.connect() as db:return [self.trip(r['id'],db) for r in db.execute('SELECT id FROM transit_trips ORDER BY id')]

    def create_trip(self,data):
        fields(data,'trip_id service area scheduled_at at actor evidence')
        trip_id=identifier(data['trip_id']);service=text(data['service'],'fictional service',100)
        area=text(data['area'],'fictional area',100);actor=text(data['actor'],'actor',200)
        evidence=text(data['evidence'],'schedule evidence');at=timestamp(data['at']);scheduled=timestamp(data['scheduled_at'])
        if at>scheduled:raise ValueError('schedule registration must not follow the scheduled arrival')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM transit_trips WHERE id=?',(trip_id,)).fetchone():raise Conflict('synthetic trip already exists')
            db.execute('INSERT INTO transit_trips VALUES (?,?,?,?,?,?,?,1)',(trip_id,service,area,scheduled.isoformat(),at.isoformat(),actor,evidence))
            self.store.log(db,actor,'schedule_synthetic_transit_trip',trip_id,data)
            return self.trip(trip_id,db)

    def observe(self,trip_id,data):
        fields(data,'version result at actual_at actor evidence passenger_count passenger_delay')
        if type(data['version']) is not int:raise ValueError('integer version required')
        result=text(data['result'],'trip result',100)
        if result not in {'ARRIVED','CANCELLED'}:raise ValueError('result must be ARRIVED or CANCELLED')
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'observation/correction evidence')
        at=timestamp(data['at']);actual=timestamp(data['actual_at']) if result=='ARRIVED' else None
        if result=='CANCELLED' and data['actual_at'] is not None:raise ValueError('cancelled trips have no actual arrival')
        if actual and actual>at:raise ValueError('actual arrival cannot follow observation time')
        passenger_count,delay=data['passenger_count'],data['passenger_delay']
        if (passenger_count is None)!=(delay is None):raise ValueError('passenger count and aggregate person-minute delay must both be supplied or both unknown')
        if passenger_count is not None:
            passenger_count=count(passenger_count,'passenger observations');delay=minutes(delay,'aggregate passenger delay')
            if passenger_count==0 and delay!=0:raise ValueError('zero passenger observations require zero aggregate delay')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');trip=self.trip(trip_id,db)
            if trip['version']!=data['version']:raise Conflict('Trip changed. Reload before recording observation.')
            if at<timestamp(trip['registered_at']) or (actual and actual<timestamp(trip['registered_at'])):raise ValueError('observation/arrival precedes schedule registration')
            if trip['observations'] and at<timestamp(trip['observations'][-1]['at']):raise ValueError('observation precedes previous revision')
            if trip['checks'] and at<timestamp(trip['checks'][-1]['at']):raise ValueError('observation precedes latest check')
            db.execute('INSERT INTO transit_observations VALUES (?,?,?,?,?,?,?,?,?)',(trip_id,len(trip['observations'])+1,result,at.isoformat(),actual.isoformat() if actual else None,actor,evidence,passenger_count,delay))
            db.execute('UPDATE transit_trips SET version=version+1 WHERE id=?',(trip_id,))
            self.store.log(db,actor,'record_synthetic_transit_observation',trip_id,data)
            return self.trip(trip_id,db)

    def verify(self,trip_id,data):
        fields(data,'version at verifier passed evidence')
        if type(data['version']) is not int or type(data['passed']) is not bool:raise ValueError('integer version and boolean passed required')
        actor,evidence=text(data['verifier'],'verifier',200),text(data['evidence'],'verification evidence');at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');trip=self.trip(trip_id,db)
            if trip['version']!=data['version']:raise Conflict('Trip changed. Reload before verification.')
            if not trip['observations']:raise ValueError('record an observation before verification')
            last=trip['observations'][-1]
            if actor==last['actor']:raise ValueError('use a distinct verifier identifier from the current observation recorder')
            if at<timestamp(last['at']) or (trip['checks'] and at<timestamp(trip['checks'][-1]['at'])):raise ValueError('verification precedes current observation or previous check')
            db.execute('INSERT INTO transit_checks VALUES (?,?,?,?,?,?,?)',(trip_id,len(trip['checks'])+1,last['sequence'],at.isoformat(),actor,int(data['passed']),evidence))
            db.execute('UPDATE transit_trips SET version=version+1 WHERE id=?',(trip_id,))
            self.store.log(db,actor,'verify_synthetic_transit_observation',trip_id,data)
            return self.trip(trip_id,db)

    def finding(self,finding_id,db=None):
        if db is None:
            with self.store.connect() as connection:return self.finding(finding_id,connection)
        row=db.execute('SELECT * FROM transit_findings WHERE id=?',(finding_id,)).fetchone()
        if not row:raise KeyError('synthetic access finding not found')
        events=[dict(r) for r in db.execute('SELECT * FROM transit_finding_events WHERE finding_id=? ORDER BY sequence',(finding_id,))]
        return {**dict(row),'events':events,'status':events[-1]['status'],'kind':'SYNTHETIC'}

    def findings(self):
        with self.store.connect() as db:return [self.finding(r['id'],db) for r in db.execute('SELECT id FROM transit_findings ORDER BY id')]

    def create_finding(self,data):
        fields(data,'finding_id trip_id access_need description excluded_boardings at actor evidence')
        finding_id,trip_id=identifier(data['finding_id']),identifier(data['trip_id'])
        need=text(data['access_need'],'access need',100)
        if need not in ACCESS_NEEDS:raise ValueError('invalid access-need category')
        excluded=data['excluded_boardings']
        if excluded is not None:excluded=count(excluded,'reported excluded boarding observations')
        description=text(data['description'],'fictional non-identifying finding');actor=text(data['actor'],'actor',200)
        evidence=text(data['evidence'],'finding evidence');at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');trip=self.trip(trip_id,db)
            if at<timestamp(trip['registered_at']):raise ValueError('finding precedes schedule registration')
            if db.execute('SELECT id FROM transit_findings WHERE id=?',(finding_id,)).fetchone():raise Conflict('synthetic finding already exists')
            db.execute('INSERT INTO transit_findings VALUES (?,?,?,?,?,1)',(finding_id,trip_id,need,description,excluded))
            db.execute('INSERT INTO transit_finding_events VALUES (?,1,?,?,?,?)',(finding_id,'OPEN',at.isoformat(),actor,evidence))
            self.store.log(db,actor,'create_synthetic_transit_access_finding',finding_id,data)
            return self.finding(finding_id,db)

    def update_finding(self,finding_id,data):
        fields(data,'version status at actor evidence')
        if type(data['version']) is not int:raise ValueError('integer version required')
        status=text(data['status'],'finding status',100);actor=text(data['actor'],'actor',200)
        evidence=text(data['evidence'],'response evidence');at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');finding=self.finding(finding_id,db)
            if finding['version']!=data['version']:raise Conflict('Finding changed. Reload before saving.')
            if status!=('RESOLVED' if finding['status']=='OPEN' else 'OPEN'):raise ValueError('finding must alternate OPEN and RESOLVED')
            if at<timestamp(finding['events'][-1]['at']):raise ValueError('response precedes previous finding event')
            db.execute('INSERT INTO transit_finding_events VALUES (?,?,?,?,?,?)',(finding_id,len(finding['events'])+1,status,at.isoformat(),actor,evidence))
            db.execute('UPDATE transit_findings SET version=version+1 WHERE id=?',(finding_id,))
            self.store.log(db,actor,'respond_to_synthetic_transit_finding',finding_id,data)
            return self.finding(finding_id,db)

    def report(self,as_of=None,service=None,area=None,early_minutes=1,late_minutes=5):
        at=timestamp(as_of or now());early=minutes(early_minutes,'early tolerance');late=minutes(late_minutes,'late tolerance')
        registered=set();due=upcoming=unobserved=unverified=arrivals=cancelled=on_time=0
        deviations=[];delays=[];passenger_total=0;person_minutes=0;passenger_samples=0
        for trip in self.trips():
            if (service and trip['service']!=service) or (area and trip['area']!=area) or timestamp(trip['registered_at'])>at:continue
            registered.add(trip['id'])
            if timestamp(trip['scheduled_at'])>at:upcoming+=1;continue
            due+=1;observations=[o for o in trip['observations'] if timestamp(o['at'])<=at]
            if not observations:unobserved+=1;continue
            last=observations[-1];checks=[c for c in trip['checks'] if c['observation_sequence']==last['sequence'] and timestamp(c['at'])<=at]
            if not checks or not checks[-1]['passed']:unverified+=1;continue
            if last['result']=='CANCELLED':cancelled+=1
            else:
                arrivals+=1;deviation=(timestamp(last['actual_at'])-timestamp(trip['scheduled_at'])).total_seconds()/60
                deviations.append(deviation);delays.append(max(0,deviation));on_time+=-early<=deviation<=late
            if last['passenger_count'] is not None:
                passenger_samples+=1;passenger_total+=last['passenger_count'];person_minutes+=last['passenger_delay']
        access={};resolved=[];ages=[];reopened=0
        for finding in self.findings():
            if finding['trip_id'] not in registered:continue
            events=[e for e in finding['events'] if timestamp(e['at'])<=at]
            if not events:continue
            item=access.setdefault(finding['access_need'],dict(findings=0,open=0,resolved=0,known_exclusion_counts=0,reported_excluded_boarding_observations=None))
            item['findings']+=1;last=events[-1];reopened+=sum(e['status']=='OPEN' for e in events[1:])
            if finding['excluded_boardings'] is not None:
                item['known_exclusion_counts']+=1;item['reported_excluded_boarding_observations']=(item['reported_excluded_boarding_observations'] or 0)+finding['excluded_boardings']
            if last['status']=='OPEN':item['open']+=1;ages.append((at-timestamp(events[0]['at'])).total_seconds()/3600)
            else:item['resolved']+=1;resolved.append((timestamp(last['at'])-timestamp(events[0]['at'])).total_seconds()/3600)
        verified=arrivals+cancelled
        return {'kind':'SYNTHETIC','as_of':at.isoformat(),'service':service,'area':area,
                'on_time_window_minutes':{'early':early,'late':late},'due_scheduled_trips':due,'upcoming_scheduled_trips':upcoming,
                'unobserved_due_trips':unobserved,'unverified_due_observations':unverified,'verified_outcomes':verified,
                'verification_coverage':verified/due if due else None,'verified_arrivals':arrivals,'verified_cancellations':cancelled,
                'on_time_arrivals':on_time,'on_time_arrival_rate':on_time/arrivals if arrivals else None,
                'cancellation_rate_among_verified_outcomes':cancelled/verified if verified else None,
                'arrival_deviation_minutes':statistic(deviations),'positive_arrival_delay_minutes':statistic(delays),
                'passenger_delay':{'outcome_samples':passenger_samples,'missing_verified_outcomes':verified-passenger_samples,
                    'passenger_observations':passenger_total,'total_person_minutes':person_minutes if passenger_samples else None,
                    'mean_minutes_per_passenger_observation':person_minutes/passenger_total if passenger_total else None},
                'access_findings_by_need':access,'open_access_findings':len(ages),'reopen_events':reopened,
                'access_response_hours':statistic(resolved),'open_access_age_hours':statistic(ages),'execution_authorized':False,
                'method':'One declared arrival boundary per fictional trip; UTC. Due trips are scheduled by cutoff; upcoming trips are separate. Only latest observations with current passing checks enter outcome statistics. On-time uses inclusive caller-defined early/late tolerances (prototype defaults 1/5 minutes), arrivals only; cancellations have a separate denominator. Passenger delay uses reported aggregate person-minutes and passenger observations, never inferred from vehicle lateness. Access reports may overlap and are not unique riders or population coverage. Recorded checks and identities are user assertions; no dispatch or real service finding.'}
