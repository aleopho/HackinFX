# SPDX-License-Identifier: GPL-2.0-or-later
import hashlib,json,ssl,tempfile,time,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
from remote_control import RemoteManager,private_ip
from widget_bridge import WidgetBridge
class Core:
    def __init__(self):self.commands=[]
    def status(self):return dict(schema=1,devices=[dict(id='test',name='Keyboard',controllable=True,usb_id='PRIVATE-ID',hardware_state={'private':'PRIVATE'})],scene=dict(mode='twinkle',palette=['9bed4b'],brightness=70),running=True,selected_devices=['test'],active_devices=['test'],scene_revision=2,scenes=[],credential='PRIVATE-CREDENTIAL')
    def start(self,v):self.commands.append(v)
    def pause(self):self.commands.append('pause')
class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.core=Core();self.manager=RemoteManager(self.temp.name,self.core,port=0)
        with patch('remote_control.addresses',return_value=['192.168.1.20']):self.manager.enable(True)
        self.context=ssl.create_default_context(cafile=str(Path(self.temp.name)/'certificate.pem'));self.context.check_hostname=False
        self.url='https://127.0.0.1:'+str(self.manager.server.server_port)
    def tearDown(self):self.manager.close();self.temp.cleanup()
    def request(self,path,body=None,token=None,origin=None):
        headers={}
        if token:headers['Authorization']='Bearer '+token
        if body is not None:headers['Content-Type']='application/json'
        if origin:headers['Origin']=origin
        r=urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        with urllib.request.urlopen(r,context=self.context,timeout=3) as response:return json.load(response)
    def paired(self):
        code=self.manager.open_pairing()['pairCode'];return self.request('/v1/pair',dict(code=code,name='Test phone'))['token']
    def test_unpaired_client_has_no_status_and_browser_origin_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/v1/status')
        self.assertEqual(e.exception.code,401)
        code=self.manager.open_pairing()['pairCode']
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/v1/pair',dict(code=code,name='Browser'),origin='http://evil.invalid')
        self.assertEqual(e.exception.code,403)
    def test_one_time_pairing_tls_identity_and_no_plaintext_token_on_disk(self):
        token=self.paired();self.assertEqual(len(self.manager.status()['clients']),1)
        self.assertNotIn(token,(Path(self.temp.name)/'phones.json').read_text());self.assertIsNone(self.manager.status()['pairCode'])
        cert=ssl.PEM_cert_to_DER_cert((Path(self.temp.name)/'certificate.pem').read_text());self.assertEqual(self.manager.fingerprint,hashlib.sha256(cert).hexdigest())
        status=self.request('/v1/status',token=token);self.assertNotIn('PRIVATE',json.dumps(status));self.assertEqual(status['active_devices'],['test'])
    def test_revoke_prevents_status_and_control_immediately(self):
        token=self.paired();self.manager.revoke(self.manager.status()['clients'][0]['id'])
        for path,body in [('/v1/status',None),('/v1/scene/start',{'devices':['test']})]:
            with self.assertRaises(urllib.error.HTTPError) as e:self.request(path,body,token)
            self.assertEqual(e.exception.code,401)
        self.assertEqual(self.core.commands,[])
    def test_phone_cannot_probe_flash_shutdown_or_enable_pairing(self):
        token=self.paired()
        for path in ['/v1/ram/probe','/v1/discover','/v1/shutdown','/v1/remote/pair','/v1/nanoleaf/pair']:
            with self.assertRaises(urllib.error.HTTPError) as e:self.request(path,{},token)
            self.assertEqual(e.exception.code,404)
        self.assertEqual(self.core.commands,[])
    def test_expiry_and_five_wrong_attempts_close_pairing(self):
        code=self.manager.open_pairing()['pairCode'];self.manager.deadline=time.monotonic()-1
        with self.assertRaises(PermissionError):self.manager.pair(code,'Phone')
        self.manager.open_pairing()
        for _ in range(5):
            with self.assertRaises(PermissionError):self.manager.pair('invalid','Phone')
        self.assertIsNone(self.manager.status()['pairCode'])
    def test_scene_control_and_catalog_remain_scoped_to_paired_phone(self):
        token=self.paired();self.request('/v1/scene/start',dict(devices=['test'],config=dict(mode='twinkle')),token);self.request('/v1/scene/stop',{},token)
        self.assertEqual(len(self.core.commands),2);self.assertEqual(len(self.request('/v1/effects',token=token)['effects']),41)
    def test_credentials_survive_restart_but_service_is_not_implicitly_started(self):
        token=self.paired();self.manager.close();restored=RemoteManager(self.temp.name,self.core,port=0)
        self.assertIsNotNone(restored.authorize('Bearer '+token));self.assertIsNone(restored.server);restored.close()
    def test_public_addresses_are_rejected(self):
        self.assertFalse(private_ip('8.8.8.8'));self.assertFalse(private_ip('192.168.1.1.evil.invalid'));self.assertTrue(private_ip('192.168.1.20'))
class WidgetBridgeTests(unittest.TestCase):
    def test_read_only_widget_feed_excludes_credentials_and_hardware_inventory(self):
        bridge=WidgetBridge(Core(),ports=[0]);url='http://127.0.0.1:'+str(bridge.server.server_port)
        try:
            with urllib.request.urlopen(url+'/v1/widget',timeout=3) as response:data=json.load(response)
            self.assertEqual(data['appName'],'HackinFX');self.assertEqual(data['effect'],'Twinkle');self.assertEqual(data['activeDevices'],1);self.assertNotIn('PRIVATE',json.dumps(data));self.assertNotIn('devices',data)
            with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(urllib.request.Request(url+'/v1/widget',data=b'{}'),timeout=3)
            self.assertEqual(e.exception.code,405)
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(url+'/v1/scene/start',timeout=3)
        finally:bridge.close()
