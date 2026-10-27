#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Authenticated, loopback-only Core process owned by the HackinFX app."""
import argparse
import fcntl
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import socketserver
import signal
import threading
from center_core import Center, atomic_json


class LocalServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,center,token):
        self.center,self.token=center,token;self.remote=None
        super().__init__(('127.0.0.1',0),Handler)
    def server_bind(self):
        # The API is loopback-only. HTTPServer's reverse DNS can stall startup
        # on hosts without a working resolver; no hostname lookup is needed.
        socketserver.TCPServer.server_bind(self)
        self.server_name='localhost';self.server_port=self.server_address[1]


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup();self.connection.settimeout(5)
    def log_message(self,*args):pass  # Never log bearer credentials or device data.
    def reply(self,status,payload):
        body=json.dumps(payload,allow_nan=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
    def authenticated(self):
        if self.headers.get('Origin') is not None:
            self.reply(403,dict(error='Browser origins are not allowed'));return False
        if self.headers.get('Host') not in ('127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port)):
            self.reply(403,dict(error='Loopback Host required'));return False
        if not hmac.compare_digest(self.headers.get('Authorization','').encode(),('Bearer '+self.server.token).encode()):
            self.reply(401,dict(error='Core authorization required'));return False
        return True
    def do_GET(self):
        if not self.authenticated():return
        if self.path=='/v1/remote/status' and self.server.remote:self.reply(200,self.server.remote.status());return
        if self.path!='/v1/status':self.reply(404,dict(error='Unknown endpoint'));return
        self.reply(200,self.server.center.status())
    def do_POST(self):
        if not self.authenticated():return
        try:
            self.connection.settimeout(5)
            if self.headers.get('Transfer-Encoding') is not None:raise ValueError('Chunked requests are not accepted')
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON required')
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=65536:raise ValueError('Request size outside allowed range')
            raw=self.rfile.read(size)
            if len(raw)!=size:raise ValueError('Incomplete request')
            value=json.loads(raw)
            if not isinstance(value,dict):raise ValueError('JSON object required')
            core=self.server.center
            if self.path.startswith('/v1/remote/'):
                remote=self.server.remote
                if remote is None:raise ValueError('Remote service is unavailable')
                if self.path=='/v1/remote/enable':result=remote.enable(value.get('enabled'))
                elif self.path=='/v1/remote/pair':result=remote.open_pairing()
                elif self.path=='/v1/remote/revoke':result=remote.revoke(value.get('id'))
                else:raise ValueError('Unknown Remote action')
            elif self.path=='/v1/initialize':result=core.initialize()
            elif self.path=='/v1/discover':result=core.refresh()
            elif self.path=='/v1/ram/probe':result=core.probe_ram()
            elif self.path=='/v1/nanoleaf/scan':result=core.scan_nanoleaf()
            elif self.path=='/v1/nanoleaf/pair':result=core.pair_nanoleaf(value)
            elif self.path=='/v1/scene/start':result=core.start(value)
            elif self.path=='/v1/scene/stop':result=core.pause()
            elif self.path=='/v1/devices/brightness':result=core.set_device_brightness(value.get('levels'))
            elif self.path=='/v1/layout':result=core.set_layout(value)
            elif self.path=='/v1/scenes/save':result=core.save_scene(value)
            elif self.path=='/v1/shutdown':
                result=dict(stopping=True)
                threading.Thread(target=self.server.shutdown,daemon=True).start()
            else:self.reply(404,dict(error='Unknown endpoint'));return
            self.reply(200,result)
        except (ValueError,KeyError,TypeError) as exc:self.reply(400,dict(error=str(exc)[:300]))
        except Exception as exc:self.reply(503,dict(error=str(exc)[:300] or type(exc).__name__))


def serve(directory,discovery,profiles,scenes,owner_pid=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);os.chmod(directory,0o700)
    discovery=Path(discovery)
    if discovery.parent.resolve()!=directory.resolve():raise ValueError('Discovery file must be inside the private Core directory')
    with (directory/'core.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        token=secrets.token_urlsafe(32);core=Center(scenes,profiles);server=LocalServer(core,token)
        from remote_control import RemoteManager
        from widget_bridge import WidgetBridge
        remote=RemoteManager(directory/'Remote',core);server.remote=remote;widget=None
        try:widget=WidgetBridge(core)
        except OSError:core.errors.append('Widget bridge unavailable: close other HackinFX instances.')
        if remote.config['enabled']:
            try:remote.enable(True)
            except Exception:core.errors.append('Remote could not start; review Settings.')
        atomic_json(discovery,dict(schema=1,port=server.server_port,credential=token,pid=os.getpid()))
        def stop(*_):threading.Thread(target=server.shutdown,daemon=True).start()
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        from hotplug import HotplugMonitor
        hotplug=HotplugMonitor(core)
        finished=threading.Event()
        if owner_pid is not None:
            def watch_owner():
                while not finished.wait(1):
                    if os.getppid()!=owner_pid:stop();return
            threading.Thread(target=watch_owner,daemon=True).start()
        try:server.serve_forever(poll_interval=0.2)
        finally:
            finished.set();hotplug.close();remote.close();widget.close() if widget else None;core.close();server.server_close()
            try:discovery.unlink()
            except FileNotFoundError:pass


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--discovery',type=Path,required=True)
    parser.add_argument('--profiles',type=Path,required=True);parser.add_argument('--scenes',type=Path,required=True)
    parser.add_argument('--owner-pid',type=int)
    args=parser.parse_args();serve(args.directory,args.discovery,args.profiles,args.scenes,args.owner_pid)
