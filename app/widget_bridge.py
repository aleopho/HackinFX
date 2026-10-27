# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only loopback bridge for a sandboxed WidgetKit extension. No control API."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json,socketserver,threading
from datetime import datetime,timezone
PORTS=range(49731,49735)
class BoundedServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,handler):self.slots=threading.BoundedSemaphore(8);super().__init__(address,handler)
    def server_bind(self):
        socketserver.TCPServer.server_bind(self);self.server_name='localhost';self.server_port=self.server_address[1]
    def process_request(self,request,address):
        if not self.slots.acquire(False):request.close();return
        try:super().process_request(request,address)
        except Exception:self.slots.release();raise
    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.slots.release()
    def handle_error(self,*args):pass
class WidgetHandler(BaseHTTPRequestHandler):
    def setup(self):super().setup();self.connection.settimeout(2)
    def log_message(self,*args):pass
    def do_GET(self):
        if self.headers.get('Origin') is not None or self.headers.get('Host') not in ('localhost:'+str(self.server.server_port),'127.0.0.1:'+str(self.server.server_port)):
            self.send_error(403);return
        if self.path!='/v1/widget':self.send_error(404);return
        state=self.server.core.status();catalog=self.server.catalog
        body=json.dumps(dict(schema=2,appName='HackinFX',effect=catalog.get(state['scene']['mode'],state['scene']['mode']),activeDevices=len(state.get('active_devices',[])),running=state['running'],colors=state['scene']['palette'],brightness=state['scene']['brightness'],updatedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers()
        try:self.wfile.write(body)
        except OSError:pass
    def do_POST(self):self.send_error(405)
class WidgetBridge:
    def __init__(self,core,ports=PORTS):
        self.server=None
        for port in ports:
            try:self.server=BoundedServer(('127.0.0.1',port),WidgetHandler);break
            except OSError:continue
        if self.server is None:raise OSError('Widget loopback ports are unavailable')
        from pathlib import Path
        catalog=json.loads(Path(__file__).with_name('effects_catalog.json').read_text())
        self.server.core=core;self.server.catalog={e['id']:e['name'] for e in catalog['effects']}
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs=dict(poll_interval=.2),daemon=True);self.thread.start()
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)
