import test from 'node:test';
import assert from 'node:assert/strict';
import worker, {validateReport} from './worker.mjs';
const report=()=>({tool:'HackinFX',schema_version:1,submission_id:'12345678-1234-1234-1234-123456789012',adapters:[],events:[],community_notes:{observed_behavior:'No light'},setup:{outcome:'failed'}});
const request=body=>new Request('https://example.invalid/reports',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});
function environment({rate=true,fail=false}={}) {
 const stored=new Map();
 return {REPORT_LIMITER:{limit:async()=>({success:rate})},DB:{prepare(sql){let values;return{bind(...args){values=args;return this},async run(){if(fail)throw Error();if(sql.startsWith('INSERT')&&!stored.has(values[1]))stored.set(values[1],values[0]);return{}},async first(){return stored.has(values[0])?{id:stored.get(values[0])}:null}}}},stored};
}
test('accepts valid report; rejects unknown and sensitive fields',()=>{
 assert.equal(validateReport(report()),true);
 assert.equal(validateReport({...report(),hostname:'secret'}),false);
 assert.equal(validateReport({...report(),adapters:[{serial_number:'secret'}]}),false);
 assert.equal(validateReport({...report(),submission_id:'bad'}),false);
});
test('receipt confirms storage and retries are idempotent',async()=>{
 const env=environment();let a=await worker.fetch(request(report()),env);let b=await worker.fetch(request(report()),env);
 assert.equal(a.status,201);assert.equal(b.status,201);assert.deepEqual(await a.json(),await b.json());assert.equal(env.stored.size,1);
});
test('storage error never reports successful receipt',async()=>assert.equal((await worker.fetch(request(report()),environment({fail:true}))).status,503));
test('rate limit and missing bindings',async()=>{
 assert.equal((await worker.fetch(request(report()),environment({rate:false}))).status,429);
 assert.equal((await worker.fetch(request(report()),{})).status,503);
});
test('rejects oversized payload and invalid json',async()=>{
 assert.equal((await worker.fetch(request({...report(),community_notes:{observed_behavior:'x'.repeat(140000)}}),environment())).status,413);
 assert.equal((await worker.fetch(new Request('https://example.invalid/reports',{method:'POST',headers:{'content-type':'application/json'},body:'{'}),environment())).status,400);
});
test('no public reports endpoint; scheduled retention removes old rows',async()=>{
 assert.equal((await worker.fetch(new Request('https://example.invalid/reports'),environment())).status,405);
 let sql='';await worker.scheduled(null,{DB:{prepare(value){sql=value;return{bind(){return this},async run(){}}}}});assert.match(sql,/DELETE FROM reports/);
});
