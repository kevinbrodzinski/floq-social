#!/usr/bin/env python3
from __future__ import annotations
import io,json,os,time,urllib.error,urllib.parse,urllib.request,zipfile
from pathlib import Path

REPO=os.environ['GITHUB_REPOSITORY']
TOKEN=os.environ['GITHUB_TOKEN']
WORKFLOW='rgi-ext-02g2g3-triangulated-watch.yml'
LOCK_BRANCH='rgi-ext-02g2g1-atomic-consumed'
OUT=Path('inspection')
OUT.mkdir(exist_ok=True)

def request(path, accept='application/vnd.github+json'):
    url='https://api.github.com'+path
    req=urllib.request.Request(url,headers={
        'Authorization':f'Bearer {TOKEN}',
        'Accept':accept,
        'X-GitHub-Api-Version':'2022-11-28',
        'User-Agent':'rgi-ext-02g2g3-post-consumption-inspector/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            return r.status,r.read(),dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code,e.read(),dict(e.headers)

def get_json(path):
    code,raw,_=request(path)
    try: obj=json.loads(raw) if raw else {}
    except Exception: obj={'_raw':raw.decode(errors='replace')}
    return code,obj

def main():
    report={
      'artifact_type':'RGI_EXT_02G2G3_POST_CONSUMPTION_SCHEDULE_INSPECTION',
      'inspected_at_ns':time.time_ns(),
      'provider_request_sent_by_this_inspection':False,
      'runpod_secret_present':bool(os.environ.get('RUNPOD_API')),
    }
    code,wf=get_json(f'/repos/{REPO}/actions/workflows/{WORKFLOW}')
    report['workflow_http_status']=code
    report['workflow']={k:wf.get(k) for k in ['id','name','path','state','created_at','updated_at','html_url']}
    code,perms=get_json(f'/repos/{REPO}/actions/permissions')
    report['actions_permissions_http_status']=code
    report['actions_permissions']=perms
    code,lock=get_json(f'/repos/{REPO}/git/ref/heads/{LOCK_BRANCH}')
    report['lock_http_status']=code
    report['lock_exists']=(code==200)
    report['lock_object_sha']=((lock.get('object') or {}).get('sha') if isinstance(lock,dict) else None)
    if report['workflow'].get('id'):
        wid=report['workflow']['id']
        code,runs=get_json(f'/repos/{REPO}/actions/workflows/{wid}/runs?event=schedule&per_page=50')
        report['scheduled_runs_http_status']=code
        summaries=[]
        for run in (runs.get('workflow_runs') or []):
            rid=run['id']
            _,jobs=get_json(f'/repos/{REPO}/actions/runs/{rid}/jobs?per_page=100')
            _,arts=get_json(f'/repos/{REPO}/actions/runs/{rid}/artifacts?per_page=100')
            rs={k:run.get(k) for k in ['id','run_number','run_attempt','status','conclusion','event','head_sha','created_at','run_started_at','updated_at','html_url']}
            rs['jobs']=[{k:j.get(k) for k in ['id','name','status','conclusion','started_at','completed_at','html_url']} for j in (jobs.get('jobs') or [])]
            rs['artifacts']=[{k:a.get(k) for k in ['id','name','size_in_bytes','expired','digest','created_at','updated_at']} for a in (arts.get('artifacts') or [])]
            extracted=[]
            for a in (arts.get('artifacts') or []):
                if a.get('name')!='rgi-ext-02g2g3-triangulated-first-pass-execution-evidence' or a.get('expired'):
                    continue
                zcode,zraw,_=request(f"/repos/{REPO}/actions/artifacts/{a['id']}/zip",accept='application/vnd.github+json')
                if zcode!=200:
                    extracted.append({'artifact_id':a['id'],'download_http_status':zcode}); continue
                z=zipfile.ZipFile(io.BytesIO(zraw))
                dest=OUT/f'run_{rid}_artifact_{a["id"]}'
                dest.mkdir(parents=True,exist_ok=True)
                z.extractall(dest)
                parsed={}
                for name in z.namelist():
                    if name.endswith('.json'):
                        try: parsed[name]=json.loads((dest/name).read_text())
                        except Exception: pass
                extracted.append({'artifact_id':a['id'],'download_http_status':zcode,'parsed_json':parsed})
            rs['extracted_first_pass_evidence']=extracted
            summaries.append(rs)
        report['scheduled_run_count_returned']=len(summaries)
        report['scheduled_runs']=summaries
    (OUT/'POST_CONSUMPTION_INSPECTION.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    compact={
      'workflow':report.get('workflow'),
      'lock_exists':report.get('lock_exists'),
      'lock_object_sha':report.get('lock_object_sha'),
      'scheduled_run_count_returned':report.get('scheduled_run_count_returned'),
      'runs':[{'id':r['id'],'run_number':r['run_number'],'status':r['status'],'conclusion':r['conclusion'],'created_at':r['created_at'],'updated_at':r['updated_at'],'artifacts':r['artifacts']} for r in report.get('scheduled_runs',[])[:10]]
    }
    print(json.dumps(compact,indent=2,sort_keys=True))

if __name__=='__main__': main()
