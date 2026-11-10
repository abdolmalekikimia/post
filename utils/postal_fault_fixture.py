"""Scoped fault injection into an already-Mock Postal adapter on QA only.

Core stays connected. No expected response is stubbed in Python, no SQL is
written and no shared/global Postal scenario is changed. Failures belong only
to fresh test barcodes, are applied after inbound setup, and are restored.
This proves Edge fault handling, not delivery to the real Postal service.
"""
from __future__ import annotations
from contextvars import ContextVar
import copy
import base64
import json
import os
from pathlib import Path
import platform
import re
import shlex
from uuid import uuid4
from utils.inbound_completion import EdgeSqliteReader
from utils.step_report import ExecutionReport, UnverifiedPreconditionError, run_step

ACTIVE = ContextVar('postal_fault_fixture', default=None)
PREFIX = 'Integrations__PostalApi__Mock__'
LEASE_DIR=Path(__file__).resolve().parents[1]/'reports'/'postal_fault_leases'


def _process_alive(pid):
    if pid==os.getpid():return True
    if os.name!='nt':return Path('/proc',str(pid)).exists()
    import ctypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.restype=ctypes.c_void_p
    handle=kernel.OpenProcess(0x1000,False,int(pid))
    if not handle:return ctypes.get_last_error()==5
    try:
        code=ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code)):return True
        return code.value==259
    finally:kernel.CloseHandle(ctypes.c_void_p(handle))


def recover_abandoned_postal_fixture(run_settings):
    """Restore only leases owned by this machine whose Python process exited."""
    restored=[]
    if not LEASE_DIR.exists():return restored
    for path in LEASE_DIR.glob('*.json'):
        lease=json.loads(path.read_text(encoding='utf-8'))
        if lease['machine']!=platform.node() or _process_alive(lease['pid']):continue
        recovery=PostalFaultFixture.__new__(PostalFaultFixture)
        recovery.id=lease['id'];recovery.owned=set(lease['owned']);recovery.introduced=set(lease['introduced'])
        recovery.reader=EdgeSqliteReader(run_settings.ws_url)
        try:
            result=recovery._remote('restore')
            restored.append({'fixtureId':recovery.id,'restoration':result})
            path.unlink()
        finally:recovery.reader.close()
    return restored


# PC-02: same digits with and without a leading zero, to prove the exact code is kept.
FIDELITY_CODES={30:'0042',31:'42'}
# POSTAL_CONTRACTS: three different codes in one bag must each stay on their own parcel.
MIXED_CODES={40:'9001',41:'9002',42:'9003'}


def parcel_error_settings(barcode, description, code='9001'):
    if not re.fullmatch(r'[0-9]{24}',barcode):raise ValueError('Fault barcode must be 24 ASCII digits')
    return {PREFIX+'ParcelErrorOverrides__'+barcode+'__ErrorCode':code,
            PREFIX+'ParcelErrorOverrides__'+barcode+'__Description':description}


def fixture_barcode(prefix,slot):
    active=ACTIVE.get()
    if active:return active.barcode(prefix,slot)
    from utils.test_data import generate_dynamic_barcode_24
    return generate_dynamic_barcode_24(prefix=prefix,slot=slot)


def before_fault_close(context,report):
    active=ACTIVE.get()
    if active:active.before_close(context,report)


_REMOTE = r'''
import base64,json,subprocess,os,re,time,hashlib,sqlite3,random,fcntl
p=json.loads(base64.b64decode(INPUTS))
def run(args):return subprocess.check_output(args,text=True,stderr=subprocess.PIPE)
container=p['container'];m=json.loads(run(['docker','inspect',container]))[0];labels=m['Config']['Labels']
if labels.get('com.docker.compose.project')!='edge-compose-project' or labels.get('com.docker.compose.service')!='api':raise RuntimeError('Not the selected QA API')
work=os.path.realpath(labels['com.docker.compose.project.working_dir'])
if not re.fullmatch('[a-f0-9]{32}',p['id']):raise RuntimeError('Invalid fixture identity')
baseline=os.path.join(work,'qa-postal-baseline-'+p['id']+'.json');overlay=os.path.join(work,'docker-compose.qa-postal-fault.json');lock=os.path.join(work,'.qa-postal-fault.lock')
operation_lock=open(os.path.join(work,'.qa-postal-operation.lock'),'a')
os.chmod(operation_lock.name,0o600);fcntl.flock(operation_lock,fcntl.LOCK_EX)
def save(path,value):
 fd=os.open(path,os.O_CREAT|os.O_TRUNC|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w') as f:json.dump(value,f)
 os.chmod(path,0o600)
env=dict(x.split('=',1) for x in m['Config']['Env'] if '=' in x)
if p['operation']=='capture':
 if env.get('Integrations__PostalApi__Mode','').lower()!='mock':raise RuntimeError('Postal adapter is not Mock; no mode switch is allowed')
 if env.get('Integrations__CoreApi__Mode','').lower()!='connected':raise RuntimeError('Core is not Connected')
 fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w') as f:f.write(p['id'])
 try:
  bases=[os.path.realpath(x) for x in labels['com.docker.compose.project.config_files'].split(',') if os.path.realpath(x)!=overlay]
  if os.path.exists(overlay):raise RuntimeError('A prior Postal fixture was not restored')
  if any('ParcelErrorOverrides' in k or 'ScenarioOverride' in k for k in env):raise RuntimeError('Postal fault settings are already present in the running API; clean the QA environment before capturing a baseline')
  if any(os.path.commonpath([work,x])!=work for x in bases):raise RuntimeError('Unexpected Compose path')
  mounts=[x for x in m['Mounts'] if x['Destination']=='/app/data']
  if len(mounts)!=1:raise RuntimeError('No unique SQLite data volume')
  db=sqlite3.connect('file:'+os.path.join(mounts[0]['Source'],'edge.db')+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON')
  try:
   configs=db.execute('SELECT PostalCodes FROM ConfigurationSnapshots WHERE IsActive=1').fetchall()
   if len(configs)!=1:raise RuntimeError('No unique source of valid destinations')
   codes=[x for x in configs[0][0].split('\x1f') if re.fullmatch('[0-9]{5}',x)]
   random.Random(p['id']).shuffle(codes)
   destination=next((code for code in codes if db.execute("SELECT 1 FROM Parcels WHERE DestinationCenterCode=? AND State<>'Bagged' LIMIT 1",(code,)).fetchone() is None),None)
   if destination is None:raise RuntimeError('No empty valid destination is available; no data was drained')
  finally:db.close()
  save(baseline,{'env':env,'image':m['Image'],'bases':bases,'dataVolume':mounts[0]['Name'],'destination':destination})
 except Exception:os.remove(lock);raise
 print(json.dumps({'operation':'capture','image':m['Image'],'coreMode':'Connected','postalMode':'Mock','dataVolume':mounts[0]['Name'],'emptyDestination':destination,'eligibleBaselineCount':0,'destinationSource':'selected Edge active configuration + read-only Parcels query'}))
elif p['operation']=='marker':
 if not os.path.isfile(lock) or open(lock).read()!=p['id']:raise RuntimeError('Fixture ownership was lost')
 b=json.load(open(baseline));mount=next(x['Source'] for x in m['Mounts'] if x['Destination']=='/app/data')
 db=sqlite3.connect('file:'+os.path.join(mount,'edge.db')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
 try:rows=[dict(x) for x in db.execute('SELECT Id,DestinationCenterCode,RecordedBagBarcode FROM BagCloseAttempts WHERE DestinationCenterCode=?',(b['destination'],))]
 finally:db.close()
 print(json.dumps({'operation':'marker','source':'selected Edge SQLite / read-only BagCloseAttempts','destination':b['destination'],'attempts':rows,'checkedBeforeRestart':True}))
else:
 if p['operation']=='restore' and not os.path.exists(lock) and not os.path.exists(baseline):
  print(json.dumps({'operation':'restore','alreadyRestored':True}));raise SystemExit(0)
 if not os.path.isfile(lock) or open(lock).read()!=p['id']:raise RuntimeError('Fixture ownership was lost')
 b=json.load(open(baseline));command=['docker','compose','-p',labels['com.docker.compose.project']]
 for f in b['bases']:command+=['-f',f]
 extras=p.get('settings',{});owned=p.get('owned',[])
 for k,v in extras.items():
  match=re.fullmatch(r'Integrations__PostalApi__Mock__(?:ParcelErrorOverrides__([0-9]{24})__(?:ErrorCode|Description)|ScenarioOverrides__([0-9]{24}))',k)
  if not match or (match[1] or match[2]) not in owned or k in b['env']:raise RuntimeError('Fault setting is not owned by this fixture')
  if match[2] and v not in ('Rejected','Timeout'):raise RuntimeError('Unsupported batch scenario')
 if p['operation']=='restore':
  if not os.path.exists(overlay) and overlay not in labels['com.docker.compose.project.config_files'].split(','):
   os.remove(baseline);os.remove(lock)
   print(json.dumps({'operation':'restore','introducedFaults':0,'restartNeeded':False}));raise SystemExit(0)
  if os.path.exists(overlay):os.remove(overlay)
 else:
  save(overlay,{'services':{'api':{'image':b['image'],'environment':{**b['env'],**extras}}}});command+=['-f',overlay]
 # Base configuration must reproduce the captured deployment on restore. It
 # includes the root-only QA sync override installed during the sync review.
 cfg=json.loads(subprocess.check_output(command+['config','--format','json'],cwd=work,text=True,stderr=subprocess.PIPE))
 api=cfg['services']['api'];desired={**b['env'],**extras} if p['operation']!='restore' else b['env']
 if any(api['environment'].get(k)!=v for k,v in desired.items()):raise RuntimeError('Another API environment setting would change')
 if run(['docker','image','inspect',api['image'],'--format','{{.Id}}']).strip()!=b['image']:raise RuntimeError('API image would change')
 alias=next(x['source'] for x in api['volumes'] if x.get('target')=='/app/data')
 if cfg['volumes'][alias]['name']!=b['dataVolume']:raise RuntimeError('SQLite volume would change')
 recreate=['--force-recreate'] if p['operation']=='restore' else []
 subprocess.run(command+['up','-d','--no-deps','--pull','never']+recreate+['api'],cwd=work,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
 deadline=time.monotonic()+60
 while True:
  after=json.loads(run(['docker','inspect',container]))[0]
  if after['State'].get('Health',{}).get('Status')=='healthy':break
  if not after['State']['Running'] or time.monotonic()>deadline:raise RuntimeError('QA API did not become healthy')
  time.sleep(2)
 actual=dict(x.split('=',1) for x in after['Config']['Env'] if '=' in x)
 if after['Image']!=b['image'] or any(actual.get(k)!=v for k,v in desired.items()):raise RuntimeError('Effective deployment did not match the scoped fixture')
 if p['operation']=='restore':
  if any(k in actual for k in p.get('introducedKeys',[])):raise RuntimeError('Owned fault settings remain after restoration')
  os.remove(baseline);os.remove(lock)
 print(json.dumps({'operation':p['operation'],'effectiveFaultSettings':extras,'imageUnchanged':True,'dataVolumeUnchanged':True,'coreMode':'Connected','postalMode':'Mock','healthy':True}))
'''


class PostalFaultFixture:
    def __init__(self,eps,case,run_settings):
        self.eps,self.case,self.original=eps,case,run_settings
        self.id=uuid4().hex;self.codes={};self.owned=set();self.introduced=set();self.attempt=0
        self.report=ExecutionReport(f'{eps} {case.case_id} — controlled Postal adapter fault / not real Postal')
        self.reader=None;self.captured=False;self.deployed=False

    def _save_lease(self):
        LEASE_DIR.mkdir(parents=True,exist_ok=True)
        self.lease_path=LEASE_DIR/(self.id+'.json')
        value={'id':self.id,'pid':os.getpid(),'machine':platform.node(),
               'owned':sorted(self.owned),'introduced':sorted(self.introduced)}
        temporary=self.lease_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value),encoding='utf-8');temporary.replace(self.lease_path)

    def _remote(self,operation,settings=None):
        inputs=base64.b64encode(json.dumps({'container':self.reader.container,'id':self.id,'operation':operation,
            'settings':settings or {},'owned':sorted(self.owned),'introducedKeys':sorted(self.introduced)}).encode()).decode()
        script=_REMOTE.replace('INPUTS',repr(inputs))
        stdin,stdout,stderr=self.reader.client.exec_command("sudo -S -p '' python3 -c "+shlex.quote(script),timeout=180)
        stdin.write(self.reader.password+'\n');stdin.flush();raw=stdout.read();error=stderr.read()
        if stdout.channel.recv_exit_status()!=0:
            if operation=='capture':
                last=error.decode(errors='replace').splitlines()
                reason=last[-1] if last and last[-1].startswith('RuntimeError:') else 'Read-only QA baseline capture failed'
                raise UnverifiedPreconditionError('QA fault baseline unavailable: '+reason)
            raise RuntimeError('Scoped QA Postal fixture operation failed; restoration is required')
        return json.loads(raw)

    def barcode(self,prefix,slot):
        from utils.test_data import generate_dynamic_barcode_24
        key=(prefix,slot)
        if key not in self.codes:
            self.codes[key]=generate_dynamic_barcode_24(prefix=prefix,slot=slot);self.owned.add(self.codes[key])
        return self.codes[key]

    def __enter__(self):
        if os.getenv('QA_POSTAL_FAULT_FIXTURES','false').lower()!='true':
            raise UnverifiedPreconditionError('Controlled QA Postal adapter faults are disabled; no automatic switch to Mock is permitted')
        recover_abandoned_postal_fixture(self.original)
        self.reader=EdgeSqliteReader(self.original.ws_url)
        self._save_lease()
        try:
            baseline=run_step(self.report,'Capture owned QA fault baseline',lambda:self._remote('capture'),detail=lambda value:{'evidence':value})
            self.captured=True;self.context_token=ACTIVE.set(self)
            chute=f'QA-PF-{self.eps}-{self.case.case_id}-{self.id[:8]}'
            changes={'export_before_container_chute':chute,'physical_audit_chute':chute,'label_chute':chute,
                     'export_before_container_destination_code':baseline['emptyDestination'],
                     'physical_audit_destination_code':baseline['emptyDestination'],
                     'label_destination_code':baseline['emptyDestination']}
            if self.eps=='export before container':changes['export_before_container_partial_failure_barcode']=self.barcode('790000',1)
            # Settings.__post_init__ rewrites destinations outside a historical
            # three-code list. Preserve this independently validated live code
            # in a separate immutable copy; never modify the shared profile.
            self.settings=copy.copy(self.original)
            for field,value in changes.items():object.__setattr__(self.settings,field,value)
            return self
        except Exception:
            if not self.captured:self.lease_path.unlink(missing_ok=True)
            self.reader.close();self.report.print();raise

    def failure_barcode(self,index=1):return self.barcode('890000',index)

    def _label_faults(self,cat):
        # Same typed adapter faults as export before container/89, on label's own fresh barcodes.
        if cat in ('disconnection','lock_release_verify'):
            if self.attempt>1:return {}
            scenario='Timeout' if cat=='disconnection' else 'Rejected'
            return {PREFIX+'ScenarioOverrides__'+self.barcode('830000',70):scenario}
        if cat=='error_code_mixed':
            return {k:v for slot,code in MIXED_CODES.items()
                    for k,v in parcel_error_settings(self.barcode('830000',slot),'QA scoped fault '+self.id,code).items()}
        if cat=='error_code_fidelity':
            return {k:v for slot,code in FIDELITY_CODES.items()
                    for k,v in parcel_error_settings(self.barcode('830000',slot),'QA scoped fault '+self.id,code).items()}
        if cat=='mixed_deferred_label' and self.attempt>1:return {}
        slots={'partial_label':(1,),'mixed_deferred_label':(10,),'all_failed':(20,21,22)}[cat]
        return {k:v for slot in slots for k,v in parcel_error_settings(self.barcode('830000',slot),'QA scoped fault '+self.id).items()}

    def faults(self):
        cat=self.case.category
        if self.eps=='label':return self._label_faults(cat)
        if cat in ('postal_rejected','postal_ambiguous'):
            if self.attempt>1:return {}
            code=self.barcode('790000',70)
            return {PREFIX+'ScenarioOverrides__'+code:'Rejected' if cat=='postal_rejected' else 'Timeout'}
        if cat in ('deferred_success','retry_success') and self.attempt>1:return {}
        if self.eps=='export before container':
            slots={'partial':(1,),'deferred_success':(10,),'deferred_failure':(11,),'all_failed':(20,21,22)}[cat]
            codes=[self.barcode('790000',slot) for slot in slots]
        else:codes=[self.failure_barcode(i) for i in ((1,2,3) if cat=='all_failed' else (1,))]
        return {k:v for code in codes for k,v in parcel_error_settings(code,'QA scoped fault '+self.id).items()}

    def before_close(self,context,report):
        self.attempt+=1;faults=self.faults()
        # Only the first attempt and an explicit transient recovery change the
        # process configuration. Repeated permanent failures need no restart.
        if getattr(self,'last_faults',None)!=faults:
            self.introduced.update(faults);self.deployed=True
            self._save_lease()
            run_step(report,f'[PRECONDITION] Apply owned Postal fault / attempt {self.attempt}',
                     lambda:self._remote('apply',faults),detail=lambda value:{'evidence':value})
            self.last_faults=faults
            context.ws.close();context.ws.connect()
            from flows.bag.bag_flow_support import refresh_business_session
            refresh_business_session(report,context.device,self.settings,'Postal fixture reconnect')

    def verify_error_marker_cleared(self,report):
        def check():
            proof=self._remote('marker')
            assert proof['attempts']==[], 'Failed Postal operation retained an unresolved bag attempt before any fixture restart'
            return proof
        return run_step(report,'Verify failed attempt marker cleared before recovery/restart',check,
                        detail=lambda value:{'evidence':value})

    def __exit__(self,typ,error,tb):
        try:
            if self.captured:
                run_step(self.report,'Restore QA Postal baseline and verify removal of owned faults',
                         lambda:self._remote('restore'),detail=lambda value:{'evidence':value})
                self.lease_path.unlink(missing_ok=True)
        finally:
            ACTIVE.reset(self.context_token);self.reader.close();self.report.print()
        return False
