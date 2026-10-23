import {handleCompatibility} from './compatibility.mjs';
// SPDX-License-Identifier: GPL-2.0-or-later
const MAX_BYTES = 131072;
const TOP_LEVEL = new Set('schema_version tool tool_version scan_id created_at runtime scan_mode rm_connections i2c_transactions adapters driver_bundles events errors privacy lighting_configuration configuration_fingerprint led_availability development_assessment submission_id app_session_events community_notes setup lighting_evidence'.split(' '));
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function validateReport(report) {
  if (!report || Array.isArray(report) || typeof report !== 'object') return false;
  if (Object.keys(report).some(key => !TOP_LEVEL.has(key))) return false;
  if (report.tool !== 'HackinFX' || report.schema_version !== 1 || !uuid.test(report.submission_id || '')) return false;
  if (!Array.isArray(report.adapters) || report.adapters.length > 16 || !Array.isArray(report.events) || report.events.length > 128) return false;
  if ((report.lighting_evidence || []).length > 12 || (report.app_session_events || []).length > 100) return false;
  const notes = report.community_notes || {};
  if (typeof notes !== "object" || Array.isArray(notes)) return false;
  if (Object.values(notes).some(value => typeof value !== 'string' || value.length > 8000)) return false;
  function allowed(value, depth = 0) {
    if (depth > 12) return false;
    if (typeof value === 'string') return value.length <= 16000;
    if (typeof value === 'number') return Number.isFinite(value);
    if (value === null || typeof value === 'boolean') return true;
    if (Array.isArray(value)) return value.length <= 128 && value.every(item => allowed(item, depth + 1));
    if (typeof value !== 'object') return false;
    return Object.entries(value).every(([key, child]) => !/serial|hostname|IORegistryEntryChildren|IORegistryEntryID|password|token|kernel_address/i.test(key) && allowed(child, depth + 1));
  }
  return allowed(report);
}
function reply(status, value) {
  return Response.json(value, {status, headers: {'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff'}});
}
async function readBounded(request) {
  if (Number(request.headers.get('content-length')) > MAX_BYTES) throw new Error('too-large');
  if (!request.body) throw new Error('invalid');
  const reader = request.body.getReader(); const chunks = []; let length = 0;
  while (true) {
    const {done, value} = await reader.read(); if (done) break;
    length += value.byteLength;
    if (length > MAX_BYTES) { await reader.cancel(); throw new Error('too-large'); }
    chunks.push(value);
  }
  const bytes = new Uint8Array(length); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk,offset); offset += chunk.byteLength; }
  return JSON.parse(new TextDecoder().decode(bytes));
}
export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (path === '/health' && request.method === 'GET') return reply(200,{service:'HackinFX report inbox'});
    if (path === '/compatibility' || path === '/verifications') return handleCompatibility(request,env,{readBounded,reply});
    if (path !== '/reports') return reply(404,{error:'not-found'});
    if (request.method !== 'POST') return reply(405,{error:'method-not-allowed'});
    if (!request.headers.get('content-type')?.toLowerCase().startsWith('application/json')) return reply(415,{error:'json-required'});
    if (!env.DB || !env.REPORT_LIMITER) return reply(503,{error:'inbox-not-configured'});
    try {
      const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
      const hash = await crypto.subtle.digest('SHA-256',new TextEncoder().encode(ip));
      const key = Array.from(new Uint8Array(hash),value=>value.toString(16).padStart(2,'0')).join('');
      if (!(await env.REPORT_LIMITER.limit({key})).success) return reply(429,{error:'rate-limited'});
      let report;
      try { report = await readBounded(request); }
      catch (error) { return reply(error.message === 'too-large' ? 413 : 400,{error:'invalid-report'}); }
      if (!validateReport(report)) return reply(400,{error:'invalid-report'});
      const id = crypto.randomUUID();
      await env.DB.prepare('INSERT OR IGNORE INTO reports (id, submission_id, created_at, fingerprint, outcome, payload_json) VALUES (?, ?, ?, ?, ?, ?)')
        .bind(id,report.submission_id,new Date().toISOString(),String(report.configuration_fingerprint || '').slice(0,64),String(report.setup?.outcome || 'unknown').slice(0,40),JSON.stringify(report)).run();
      const stored = await env.DB.prepare('SELECT id FROM reports WHERE submission_id = ?').bind(report.submission_id).first();
      if (!stored?.id) return reply(503,{error:'storage-unavailable'});
      return reply(201,{report_id:stored.id});
    } catch { return reply(503,{error:'inbox-unavailable'}); }
  },
  async scheduled(_controller, env) {
    await env.DB.prepare("DELETE FROM reports WHERE created_at < ?").bind(new Date(Date.now()-90*86400000).toISOString()).run();
  }
};
