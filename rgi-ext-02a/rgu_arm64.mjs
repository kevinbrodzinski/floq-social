import http from 'http';
import fs from 'fs';
import os from 'os';
import crypto from 'crypto';
import {execFileSync} from 'child_process';

const profilePath=process.env.PROFILE||'rgi-ext-02a/profile.json';
const vectorPath=process.env.VECTOR_RESULT||'evidence/vector.json';
const profileBytes=fs.readFileSync(profilePath); const profile=JSON.parse(profileBytes); const profileSha=crypto.createHash('sha256').update(profileBytes).digest('hex');
const vector=JSON.parse(fs.readFileSync(vectorPath));
const hardware={platform:os.platform(),release:os.release(),arch:os.arch(),cpu_count:os.cpus().length,cpus:os.cpus().map(x=>x.model),uname:execFileSync('uname',['-a'],{encoding:'utf8'}).trim(),lscpu:execFileSync('lscpu',[],{encoding:'utf8'})};
const envHash=crypto.createHash('sha256').update(JSON.stringify({profile_sha256:profileSha,hardware,vector})).digest('hex');
const subject=process.env.SUBJECT_ID||'ext02a-arm64-node';
const hash=crypto.createHash('sha256').update('rgi-ext02a:'+envHash).digest('hex');
const stateId=`${hash.slice(0,8)}-${hash.slice(8,12)}-5${hash.slice(13,16)}-a${hash.slice(17,20)}-${hash.slice(20,32)}`;
const state={spec_version:'0.1.0',state_id:stateId,observed_at:new Date().toISOString(),producer:{id:'rgu://ext02a/arm64-node','implementation':'rgi-ext02a-arm64-node','version':'1.0.0',conformance:['BS-CORE-PRODUCER-0.1','BS-RGU-PRODUCER-0.1','RGI-RGU-1.0']},subject:{id:subject,type:'compute-node',scope:'node'},status:'UNKNOWN',resources:{primary:{id:'bs.compute.cpu.capacity',unit:'{cpu}',boundary:'UPPER',role:'PRIMARY'},coupled:[]},observability:{status:'UNMEASURED',reason_code:'MEASUREMENT_NOT_EXECUTED'},measurement:{method_id:'bs.method.source_audit.v0.1',profile_id:'rgi.ext02a.hardware-source-audit.v1',decoder_fidelity:'NOT_APPLICABLE',outcome_interface:'NATIVE'},chart:{id:'rgi.ext02a.cpu.vector-concurrency',version:'1',source:'PROFILE_DEFINED',status:'CERTIFIED'},reason:{code:'MEASUREMENT_NOT_EXECUTED',message:'Real arm64 hardware source audit and native vector workload completed; no validated alpha/beta measurement profile exists for this target, so no Brodzinski Number is emitted.'},extensions:{'org.resourcegeometry.ext02a':{profile_sha256:profileSha,environment_sha256:envHash,architecture:'arm64',native_kernel:vector.kernel,native_vector_result:vector,hardware}}};
const caps={rgi_version:'1.0.0',implementation:{id:'rgi-ext02a-arm64-node',language:'Node.js'},operator:{organization_id:'github-hosted-ext02a-arm64'},bs_core_compatibility:'BS-CORE-1.0-COMPAT',conformance_claims:['BS-RGU-PRODUCER-0.1','RGI-RGU-1.0'],benchmark_profiles:[{profile_id:profile.profile_id,version:profile.version,sha256:profileSha}],certification_bundle_versions:['rgi-certification-bundle/1.0']};
function send(res,obj,code=200){const b=Buffer.from(JSON.stringify(obj));res.writeHead(code,{'content-type':'application/json','content-length':b.length});res.end(b)}
const server=http.createServer((req,res)=>{if(req.url==='/healthz')return send(res,{status:'ok'});if(req.url==='/rgi/v1/capabilities')return send(res,caps);if(req.url===`/rgi/v1/benchmark-profiles/${profile.profile_id}/${profile.version}`)return send(res,profile);if(req.url===`/rgi/v1/states/${subject}`)return send(res,state);return send(res,{error:'NOT_FOUND'},404)});
const port=Number(process.env.PORT||38192);console.log(JSON.stringify({profile_sha256:profileSha,environment_sha256:envHash,subject,state_id:state.state_id}));server.listen(port,'127.0.0.1');
