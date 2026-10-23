import test from 'node:test';
import assert from 'node:assert/strict';
import worker from './worker.mjs';
import {validateVerification,aggregateCompatibility} from './compatibility.mjs';
const hardware={vendor_id:'10de',device_id:'2704',subsystem_vendor_id:'196e',subsystem_id:'13bc',gpu_name:'GeForce RTX 4080',gpu_vendor:'NVIDIA',board_vendor:'PNY',profile:'pny-4080-196e-13bc'};
const sample=()=>({schema_version:1,kind:'hardware-verification',verification_id:'12345678-1234-1234-1234-123456789012',installation_id:'87654321-1234-1234-1234-123456789012',hardware,macos:'26.7.1',arch:'x86_64',driver_version:'2.5.2',confirmed_effects:['static','gradient','cycle','breath','wave'],basic_rgb_confirmed:true,user_confirmed:true,transport_test_completed:true,tested_steps:7,app_version:'0.8.0',confirmed_at:'2026-10-23T10:00:00Z'});
const req=value=>new Request('https://example.invalid/verifications',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(value)});
test('confirmation requires user observation, transport success and enough tests',()=>{
 assert.equal(validateVerification(sample()),true);
 for(const patch of [{user_confirmed:false},{transport_test_completed:false},{tested_steps:3},{confirmed_effects:['static','made-up']},{notes:'private text'}])assert.equal(validateVerification({...sample(),...patch}),false);
});
test('public aggregate omits installation IDs and private runtime details',()=>{
 const row={hardware_key:'10de:2704:196e:13bc',...hardware,confirmed_effects:JSON.stringify(['static','wave']),updated_at:'2026-10-23',installation_id:'PRIVATE-ID',driver_version:'PRIVATE-DRIVER'};
 const result=aggregateCompatibility([row,row]);assert.equal(result.entries[0].reports,2);assert.deepEqual(result.entries[0].confirmed_effects,['static','wave']);assert.doesNotMatch(JSON.stringify(result),/PRIVATE/);
});
test('verification is acknowledged only after persistence',async()=>{
 let called=false;
 const env={REPORT_LIMITER:{limit:async()=>({success:true})},DB:{prepare(sql){assert.match(sql,/ON CONFLICT/);return{bind(...values){assert.equal(values[2],'10de:2704:196e:13bc');return this},async run(){called=true}}}}};
 const response=await worker.fetch(req(sample()),env);assert.equal(response.status,201);assert.equal(called,true);assert.equal((await response.json()).verification_id,sample().verification_id);
 env.DB.prepare=()=>({bind(){return this},async run(){throw Error('storage unavailable')}});
 assert.equal((await worker.fetch(req(sample()),env)).status,503);
});
test('public catalog and rejected submissions',async()=>{
 const env={DB:{prepare(){return{async all(){return{results:[]}}}}},REPORT_LIMITER:{limit:async()=>({success:true})}};
 const catalog=await worker.fetch(new Request('https://example.invalid/compatibility'),env);assert.equal(catalog.status,200);assert.deepEqual((await catalog.json()).entries,[]);
 env.REPORT_LIMITER.limit=async()=>({success:false});
 assert.equal((await worker.fetch(req(sample()),env)).status,429);
});

test('preserves manual identity metadata while keeping public catalog minimal',()=>{
 const value={...sample(),identity_source:'user-supplied',detected_gpu_name:'Generic display adapter'};
 assert.equal(validateVerification(value),true);
 assert.equal(validateVerification({...value,identity_source:'audited'}),false);
 assert.equal(validateVerification({...value,detected_gpu_name:'x'.repeat(161)}),false);
});
