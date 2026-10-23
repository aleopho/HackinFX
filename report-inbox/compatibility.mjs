// SPDX-License-Identifier: GPL-2.0-or-later
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const effects = new Set(['static','gradient','cycle','breath','wave']);
export function validateVerification(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const keys = new Set('schema_version kind verification_id installation_id hardware macos arch driver_version confirmed_effects basic_rgb_confirmed user_confirmed transport_test_completed tested_steps app_version confirmed_at identity_source detected_gpu_name'.split(' '));
  if (Object.keys(value).some(key=>!keys.has(key))) return false;
  if (value.schema_version!==1 || value.kind!=='hardware-verification' || !uuid.test(value.verification_id||'') || !uuid.test(value.installation_id||'')) return false;
  if (value.user_confirmed!==true || value.basic_rgb_confirmed!==true || value.transport_test_completed!==true) return false;
  if (!Array.isArray(value.confirmed_effects) || !value.confirmed_effects.includes('static') || value.confirmed_effects.some(effect=>!effects.has(effect)) || new Set(value.confirmed_effects).size!==value.confirmed_effects.length) return false;
  if (!Number.isInteger(value.tested_steps) || value.tested_steps<value.confirmed_effects.length+2 || value.tested_steps>32) return false;
  if (value.identity_source !== undefined && !["detected","user-supplied"].includes(value.identity_source)) return false;
  if (value.detected_gpu_name !== undefined && (typeof value.detected_gpu_name !== "string" || value.detected_gpu_name.length > 160)) return false;
  const hardware=value.hardware;
  if (!hardware || typeof hardware!=='object' || Array.isArray(hardware)) return false;
  const fields=['vendor_id','device_id','subsystem_vendor_id','subsystem_id','gpu_name','gpu_vendor','board_vendor','profile'];
  if (Object.keys(hardware).length!==fields.length || fields.some(key=>typeof hardware[key]!=='string' || !hardware[key].length || hardware[key].length>160 || /[\x00-\x1f]/.test(hardware[key]))) return false;
  if (fields.slice(0,4).some(key=>!/^[0-9a-f]{4}$/i.test(hardware[key]))) return false;
  if (!/^[\w.-]{1,80}$/.test(hardware.profile)) return false;
  if (['macos','arch','driver_version','app_version','confirmed_at'].some(key=>typeof value[key]!=='string' || value[key].length>80)) return false;
  return Number.isFinite(Date.parse(value.confirmed_at));
}
export function aggregateCompatibility(rows) {
  const entries=new Map();
  for (const row of rows) {
    let confirmed;try {confirmed=JSON.parse(row.confirmed_effects);}catch{continue;}
    if (!Array.isArray(confirmed)) continue;
    const old=entries.get(row.hardware_key);
    if (old) {old.reports++;old.confirmed_effects=[...new Set([...old.confirmed_effects,...confirmed])].filter(value=>effects.has(value)).sort();}
    else entries.set(row.hardware_key,{hardware_key:row.hardware_key,gpu_name:row.gpu_name,gpu_vendor:row.gpu_vendor,board_vendor:row.board_vendor,profile:row.profile,confirmed_effects:confirmed.filter(value=>effects.has(value)),reports:1,source:'Community user confirmations',last_confirmed:row.updated_at});
  }
  return {schema_version:1,entries:[...entries.values()]};
}
export async function handleCompatibility(request,env,{readBounded,reply}) {
  const path=new URL(request.url).pathname;
  if (!env.DB) return reply(503,{error:'inbox-not-configured'});
  try {
    if (path==='/compatibility' && request.method==='GET') {
      if (!env.REPORT_LIMITER) return reply(503,{error:'inbox-not-configured'});
      if (!(await env.REPORT_LIMITER.limit({key:'catalog:'+(request.headers.get('CF-Connecting-IP')||'unknown')})).success) return reply(429,{error:'rate-limited'});
      const rows=await env.DB.prepare('SELECT hardware_key, gpu_name, gpu_vendor, board_vendor, profile, confirmed_effects, updated_at FROM verified_hardware ORDER BY updated_at DESC LIMIT 5000').all();
      return Response.json(aggregateCompatibility(rows.results||[]),{headers:{'Cache-Control':'public, max-age=300','X-Content-Type-Options':'nosniff'}});
    }
    if (path!=='/verifications' || request.method!=='POST') return reply(405,{error:'method-not-allowed'});
    if (!request.headers.get('content-type')?.startsWith('application/json')) return reply(415,{error:'json-required'});
    if (!env.REPORT_LIMITER) return reply(503,{error:'inbox-not-configured'});
    if (!(await env.REPORT_LIMITER.limit({key:'verification:'+(request.headers.get('CF-Connecting-IP')||'unknown')})).success) return reply(429,{error:'rate-limited'});
    let value;try{value=await readBounded(request);}catch{return reply(400,{error:'invalid-verification'});}
    if (!validateVerification(value)) return reply(400,{error:'invalid-verification'});
    const h=value.hardware;
    const confirmedAt=new Date(value.confirmed_at).toISOString();
    const hardwareKey=[h.vendor_id,h.device_id,h.subsystem_vendor_id,h.subsystem_id].map(item=>item.toLowerCase()).join(':');
    const vendor={'10de':'NVIDIA','1002':'AMD','8086':'Intel'}[h.vendor_id.toLowerCase()]||h.gpu_vendor;
    const saved = await env.DB.prepare(`INSERT INTO verified_hardware (id, installation_id, hardware_key, gpu_name, gpu_vendor, board_vendor, profile, confirmed_effects, macos, arch, driver_version, confirmed_at, updated_at, identity_source, detected_gpu_name)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(installation_id, hardware_key) DO UPDATE SET id=excluded.id, gpu_name=excluded.gpu_name, gpu_vendor=excluded.gpu_vendor, board_vendor=excluded.board_vendor, profile=excluded.profile, confirmed_effects=excluded.confirmed_effects, macos=excluded.macos, arch=excluded.arch, driver_version=excluded.driver_version, confirmed_at=excluded.confirmed_at, updated_at=excluded.updated_at, identity_source=excluded.identity_source, detected_gpu_name=excluded.detected_gpu_name
      WHERE excluded.confirmed_at >= verified_hardware.confirmed_at`).bind(value.verification_id,value.installation_id,hardwareKey,h.gpu_name,vendor,h.board_vendor,h.profile,JSON.stringify(value.confirmed_effects),value.macos,value.arch,value.driver_version,confirmedAt,new Date().toISOString(),value.identity_source || "detected",value.detected_gpu_name || h.gpu_name).run();
    if (saved?.success === false) return reply(503,{error:"storage-unavailable"});
    return reply(201,{verification_id:value.verification_id});
  } catch {return reply(503,{error:'compatibility-unavailable'});}
}
