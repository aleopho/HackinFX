# SPDX-License-Identifier: GPL-2.0-or-later
"""Opt-in LAN-only TLS control. Scoped phone credentials never authorize setup/probes."""
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler
import hashlib,hmac,ipaddress,json,os,re,secrets,ssl,subprocess,threading,time
from pathlib import Path
from center_core import atomic_json
from widget_bridge import BoundedServer

def private_ip(value):
    try:
        ip=ipaddress.IPv4Address(value)
        return any(ip in ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','127.0.0.0/8'))
    except ValueError:return False

def addresses():
    try:
        output=subprocess.check_output(['/sbin/ifconfig'],text=True,timeout=3)
        return sorted({v for v in re.findall(r'\binet (\d+\.\d+\.\d+\.\d+)',output) if private_ip(v) and not v.startswith('127.')})
    except (OSError,subprocess.SubprocessError):return []

class RemoteManager:
    def __init__(self,directory,core,port=49735):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True);os.chmod(self.directory,0o700)
        self.core=core;self.port=port;self.lock=threading.RLock();self.server=None;self.thread=None;self.code=None;self.deadline=0;self.attempts=0;self.rate={};self.fingerprint='';self.config=dict(enabled=False,clients=[]);self.hosts=[]
        self.path=self.directory/'phones.json'
        try:
            if self.path.stat().st_size<=32768:
                saved=json.loads(self.path.read_text())
                if saved.get('schema')==1 and isinstance(saved.get('clients'),list) and len(saved['clients'])<=16:
                    clients=[c for c in saved['clients'] if isinstance(c,dict) and re.fullmatch('[a-f0-9]{64}',c.get('hash','')) and re.fullmatch('[a-f0-9]{24}',c.get('id','')) and isinstance(c.get('name'),str) and len(c['name'])<=60]
                    self.config=dict(enabled=saved.get('enabled') is True,clients=clients)
        except (OSError,ValueError):pass
    def persist(self):atomic_json(self.path,dict(schema=1,**self.config))
    def certificate(self):
        cert=self.directory/'certificate.pem';key=self.directory/'key.pem'
        if not cert.exists() or not key.exists():
            if cert.exists() or key.exists():raise ValueError('Remote TLS identity is incomplete; disable Remote and repair its local files')
            subprocess.run(['/usr/bin/openssl','req','-x509','-newkey','rsa:2048','-nodes','-sha256','-days','3650','-subj','/CN=HackinFX Local Remote','-keyout',str(key),'-out',str(cert)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
        os.chmod(key,0o600);os.chmod(cert,0o600)
        self.fingerprint=hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text())).hexdigest()
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2;context.load_cert_chain(cert,key);return context
    def enable(self,enabled):
        if type(enabled)is not bool:raise ValueError('Enabled must be a boolean')
        if not enabled:
            self.close();self.config['enabled']=False;self.persist();return self.status()
        with self.lock:
            if not self.server:
                context=self.certificate();server=BoundedServer(('0.0.0.0',self.port),RemoteHandler);server.manager=self
                server.socket=context.wrap_socket(server.socket,server_side=True,do_handshake_on_connect=False)
                self.server=server;self.thread=threading.Thread(target=server.serve_forever,kwargs=dict(poll_interval=.2),daemon=True);self.thread.start();self.hosts=addresses()
            self.config['enabled']=True;self.persist()
        return self.status()
    def open_pairing(self):
        if not self.server:raise ValueError('Enable Remote first')
        with self.lock:self.code='%06d'%secrets.randbelow(1000000);self.deadline=time.monotonic()+120;self.attempts=0
        return self.status()
    def status(self):
        with self.lock:
            seconds=max(0,int(self.deadline-time.monotonic()))
            return dict(enabled=self.server is not None,port=self.server.server_port if self.server else 49735,addresses=self.hosts,fingerprint=self.fingerprint,pairCode=self.code if seconds and self.attempts<5 else None,pairSeconds=seconds if self.attempts<5 else 0,clients=[dict(id=c['id'],name=c['name']) for c in self.config['clients']])
    def pair(self,code,name):
        if not isinstance(name,str) or not 1<=len(name.strip())<=60 or any(ord(c)<32 for c in name):raise ValueError('Invalid phone name')
        with self.lock:
            if not self.code or time.monotonic()>self.deadline or self.attempts>=5:raise PermissionError('Pairing is closed; open a new code on the Mac')
            self.attempts+=1
            if not isinstance(code,str) or not hmac.compare_digest(code,self.code):raise PermissionError('Pairing code does not match')
            if len(self.config['clients'])>=16:raise ValueError('Remove an old phone before pairing another')
            token=secrets.token_urlsafe(32);client=dict(id=secrets.token_hex(12),name=name.strip(),hash=hashlib.sha256(token.encode()).hexdigest());self.config['clients'].append(client);self.persist();self.code=None;self.deadline=0
            return dict(schema=1,token=token,clientId=client['id'],appName='HackinFX')
    def authorize(self,header):
        if not isinstance(header,str) or not header.startswith('Bearer ') or len(header)>160:return None
        digest=hashlib.sha256(header[7:].encode()).hexdigest()
        with self.lock:return next((c['id'] for c in self.config['clients'] if hmac.compare_digest(c['hash'],digest)),None)
    def allowed_rate(self,client):
        now=time.monotonic()
        with self.lock:
            history=[t for t in self.rate.get(client,[]) if now-t<1]
            if len(history)>=20:return False
            self.rate[client]=history+[now];return True
    def revoke(self,client):
        with self.lock:self.config['clients']=[c for c in self.config['clients'] if c['id']!=client];self.persist()
        return self.status()
    def public_status(self):
        state=self.core.status()
        fields=('id','name','vendor','category','backend','led_count','direct','controllable','status','detail','color_scope','layout','static_modes')
        return dict(schema=1,appName='HackinFX',devices=[{k:d[k] for k in fields if k in d} for d in state['devices']],device_brightness=state.get('device_brightness',{}),scene=state['scene'],running=state['running'],selected_devices=state.get('selected_devices',[]),active_devices=state.get('active_devices',[]),scene_revision=state.get('scene_revision',0),scenes=state['scenes'])
    def close(self):
        with self.lock:server=self.server;thread=self.thread;self.server=None;self.code=None;self.deadline=0
        if server:server.shutdown();server.server_close()
        if thread:thread.join(timeout=4)

class RemoteHandler(BaseHTTPRequestHandler):
    def setup(self):super().setup();self.connection.settimeout(5)
    def log_message(self,*args):pass
    def reply(self,status,value):
        raw=json.dumps(value,allow_nan=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers()
        try:self.wfile.write(raw)
        except OSError:pass
    def gate(self,pair=False):
        if not private_ip(self.client_address[0]) or self.headers.get('Origin') is not None:self.reply(403,dict(error='Only native local-network clients are allowed'));return False
        host=self.headers.get('Host','').rsplit(':',1)
        if len(host)!=2 or host[1]!=str(self.server.server_port) or not private_ip(host[0]):self.reply(403,dict(error='Private IPv4 Host required'));return False
        if pair:return True
        manager=self.server.manager;client=manager.authorize(self.headers.get('Authorization',''))
        if not client:self.reply(401,dict(error='Pair this phone with HackinFX on your Mac'));return False
        if not manager.allowed_rate(client):self.reply(429,dict(error='Too many updates; wait a moment'));return False
        return True
    def body(self):
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('Bounded JSON request required')
        n=int(self.headers.get('Content-Length','0'))
        if not 0<n<=32768:raise ValueError('Request too large')
        raw=self.rfile.read(n)
        if len(raw)!=n:raise ValueError('Incomplete request')
        value=json.loads(raw)
        if not isinstance(value,dict):raise ValueError('JSON object required')
        return value
    def do_GET(self):
        if not self.gate():return
        if self.path=='/v1/status':self.reply(200,self.server.manager.public_status())
        elif self.path=='/v1/effects':self.reply(200,json.loads(Path(__file__).with_name('effects_catalog.json').read_text()))
        else:self.reply(404,dict(error='This endpoint is not available to Remote'))
    def do_POST(self):
        if not self.gate(pair=self.path=='/v1/pair'):return
        try:
            value=self.body();manager=self.server.manager
            if self.path=='/v1/pair':self.reply(200,manager.pair(value.get('code'),value.get('name')));return
            if self.path=='/v1/scene/start':manager.core.start(value)
            elif self.path=='/v1/scene/stop':manager.core.pause()
            elif self.path=='/v1/devices/brightness':manager.core.set_device_brightness(value.get('levels'))
            else:self.reply(404,dict(error='Remote cannot perform hardware setup or system operations'));return
            self.reply(200,manager.public_status())
        except PermissionError as e:self.reply(403,dict(error=str(e)))
        except (ValueError,KeyError,TypeError) as e:self.reply(400,dict(error=str(e)[:200]))
        except Exception:self.reply(503,dict(error='Lighting command failed. Check HackinFX on the Mac.'))
