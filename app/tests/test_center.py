# SPDX-License-Identifier: GPL-2.0-or-later
import json
from pathlib import Path
import socket
import socketserver
import struct
import tempfile
import threading
import time
import types
import unittest
import urllib.request
from urllib.error import HTTPError
from unittest.mock import patch
import center_core as core
import center_sdk as sdk
from center_service import LocalServer


def text(value):
    data=value.encode()+b'\0';return struct.pack('<H',len(data))+data


def controller(name='Test Keyboard',category=5,leds=3,direct=True,serial='PRIVATE-SERIAL'):
    body=struct.pack('<I',category)+b''.join(text(v) for v in (name,'Test vendor','Fixture','1',serial,'PRIVATE-LOCATION'))
    body+=struct.pack('<HI',1,0)+text('Direct' if direct else 'Spectrum')
    body+=struct.pack('<12I',0,32 if direct else 0,0,100,0,100,0,leds,50,100,0,1)+struct.pack('<H',0)
    body+=struct.pack('<H',1)+text('Main')+struct.pack('<4I',1,leds,leds,leds)+struct.pack('<H',0)
    body+=struct.pack('<H',leds)+b''.join(text('LED '+str(i))+struct.pack('<I',i) for i in range(leds))
    body+=struct.pack('<H',leds)+b'\x00'*leds*4
    return struct.pack('<I',len(body)+4)+body


class SDKFixture(socketserver.ThreadingTCPServer):
    allow_reuse_address=True;daemon_threads=True
    def __init__(self):
        self.frames=[];self.commands=[];self.hotplug=False
        super().__init__(('127.0.0.1',0),SDKHandler)
        self.thread=threading.Thread(target=self.serve_forever,daemon=True);self.thread.start()
    def close(self):self.shutdown();self.server_close();self.thread.join()


class SDKHandler(socketserver.BaseRequestHandler):
    def handle(self):
        def exact(n):
            data=b''
            while len(data)<n:
                part=self.request.recv(n-len(data))
                if not part:raise EOFError
                data+=part
            return data
        def send(device,kind,payload):
            # Fragment headers and payloads to exercise exact-length reads.
            data=struct.pack('<4sIII',b'ORGB',device,kind,len(payload))+payload
            for offset in range(0,len(data),7):self.request.sendall(data[offset:offset+7])
        try:
            while True:
                magic,device,kind,size=struct.unpack('<4sIII',exact(16))
                data=exact(size);self.server.commands.append((device,kind,data))
                if magic!=b'ORGB':raise EOFError
                if kind==40:send(0,40,struct.pack('<I',6))
                elif kind==0:send(0,0,struct.pack('<I',2))
                elif kind==1:
                    if data!=struct.pack('<I',3):raise EOFError
                    send(device,1,controller('Keyboard' if device==0 else 'Light strip',5 if device==0 else 4))
                elif kind==1050:
                    self.server.frames.append((device,data))
                    if self.server.hotplug:send(0,100,b'')
        except (EOFError,OSError):pass


class FakeSDK:
    def __init__(self,rows=None):self.rows=rows or [];self.calls=[]
    def discover(self):return [dict(row) for row in self.rows]
    def activate(self,index):self.calls.append(('activate',index))
    def colors(self,index,colors):self.calls.append(('colors',index,colors))
    def close(self):pass


class FakeNative:
    def __init__(self,rows=None):self.rows=rows or [];self.writes=[]
    def discover(self):return [dict(row) for row in self.rows]
    def apply(self,device,colors,mode):self.writes.append((device['id'],colors,mode))


def device(index=0):
    result=sdk.parse_controller(controller());result['index']=index;return result


class ProtocolTests(unittest.TestCase):
    def test_parser_discards_serial_location_and_bounds_payload(self):
        result=sdk.parse_controller(controller())
        self.assertTrue(result['direct']);self.assertEqual(result['category'],'keyboard')
        self.assertNotIn('PRIVATE',json.dumps(result))
        for data in (b'',controller()[:-1],b'\xff'*100):
            with self.assertRaises(sdk.ProtocolError):sdk.parse_controller(data)
        self.assertFalse(sdk.parse_controller(controller(direct=False))['direct'])
    def test_real_socket_negotiation_and_rgbx_frame(self):
        server=SDKFixture();client=sdk.SDKClient(server.server_address[1])
        try:
            rows=client.discover();self.assertEqual(len(rows),2)
            client.activate(0);client.colors(0,[(255,1,2)]*3)
            deadline=time.monotonic()+2
            while not server.frames and time.monotonic()<deadline:time.sleep(.01)
            self.assertEqual(server.frames[0],(0,struct.pack('<IH',18,3)+bytes([255,1,2,0])*3))
            self.assertFalse(any(kind in (1102,1000,151,140) for _,kind,_ in server.commands))
        finally:client.close();server.close()
    def test_hotplug_forces_refresh_before_more_writes(self):
        server=SDKFixture();server.hotplug=True;client=sdk.SDKClient(server.server_address[1])
        try:
            client.discover();client.activate(0);client.colors(0,[(1,2,3)]*3)
            time.sleep(.15)
            with self.assertRaises(sdk.ProtocolError):client.colors(0,[(4,5,6)]*3)
            self.assertTrue(client.dirty)
        finally:client.close();server.close()
    def test_invalid_ports_and_frames(self):
        for value in (True,0,65536,'6742'):
            with self.assertRaises(ValueError):sdk.SDKClient(value)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.sdk=FakeSDK([device(0),device(1)]);self.native=FakeNative()
        self.core=core.Center(Path(self.tmp.name)/'scenes.json',self.tmp.name,self.sdk,self.native)
        self.core.refresh(inventory=False)
    def tearDown(self):self.core.close();self.tmp.cleanup()
    def test_discovery_never_activates_or_writes(self):self.assertEqual(self.sdk.calls,[])
    def test_shared_gradient_uses_global_layout_and_exact_targets(self):
        ids=[d['id'] for d in self.core.devices]
        self.core.set_layout({ids[0]:dict(x=.1,y=.5,width=.1),ids[1]:dict(x=.9,y=.5,width=.1)})
        self.core.start(dict(config=dict(mode='gradient',palette=['ff0000','0000ff'],brightness=100),devices=ids))
        self.core.worker.join(2)
        calls=[v for v in self.sdk.calls if v[0]=='colors']
        self.assertEqual(len(calls),2);self.assertGreater(calls[0][2][0][0],calls[1][2][0][0])
    def test_validation_precedes_hardware_activation(self):
        for ids in ([],['missing'],[self.core.devices[0]['id']]*2):
            with self.assertRaises(ValueError):self.core.start(dict(config={},devices=ids))
        self.assertEqual(self.sdk.calls,[])
    def test_animation_stops_without_more_frames_and_refresh_invalidates_targets(self):
        ids=[self.core.devices[0]['id']]
        self.core.start(dict(config=dict(mode='wave'),devices=ids));time.sleep(.12);self.core.stop()
        count=len(self.sdk.calls);time.sleep(.08);self.assertEqual(count,len(self.sdk.calls))
        self.core.refresh(inventory=False)
        with self.assertRaises(ValueError):self.core.start(dict(config={},devices=ids))
    def test_native_gpu_cannot_join_streaming_scene(self):
        row=dict(id='native:test',name='GPU',vendor='PNY',category='gpu',backend='native',led_count=3,direct=False,controllable=True,static_modes=['static','gradient'],status='ready',detail='',fingerprint='test',owns_gpu=True)
        self.native.rows=[row];self.core.refresh(inventory=False)
        with self.assertRaises(ValueError):self.core.start(dict(config=dict(mode='wave'),devices=['native:test']))
        self.assertEqual(self.native.writes,[])
        self.core.start(dict(config={},devices=['native:test']));self.core.worker.join(2);self.assertEqual(len(self.native.writes),1)
    def test_native_ownership_blocks_duplicate_openrgb_gpu(self):
        self.sdk.rows=[dict(device(),category='gpu')]
        self.native.rows=[dict(id='native:test',backend='native',category='gpu',controllable=False,owns_gpu=True)]
        self.core.refresh(inventory=False)
        self.assertFalse(self.core.devices[0]['controllable'])
        self.assertEqual(self.core.devices[0]['status'],'native-owned')
    def test_scene_persistence_is_private_and_has_no_auto_apply_or_device_binding(self):
        self.core.save_scene(dict(name='Evening',config=dict(mode='wave')))
        other=core.Center(self.core.store,self.tmp.name,FakeSDK(),FakeNative())
        self.assertEqual(other.scenes[0]['name'],'Evening');self.assertFalse(other.running)
        self.assertEqual(self.core.store.stat().st_mode&0o777,0o600)
        self.assertNotIn('devices',json.loads(self.core.store.read_text())['scenes'][0])
        other.close()
    def test_unique_layout_persists_but_duplicate_devices_are_not_guessed(self):
        self.sdk.rows=[device(0)];self.core.refresh(inventory=False)
        first=self.core.devices[0]['id'];self.core.set_layout({first:dict(x=.88,y=.25,width=.3)})
        self.core.refresh(inventory=False)
        self.assertAlmostEqual(self.core.layout[self.core.devices[0]['id']]['x'],.88)
        self.sdk.rows=[device(0),device(1)];self.core.refresh(inventory=False)
        self.assertNotEqual(self.core.layout[self.core.devices[0]['id']]['x'],.88)

    def test_additional_adapter_requires_no_engine_dispatch_changes(self):
        class ExtraAdapter:
            name='fixture-usb'
            def __init__(self):self.writes=[]
            def discover(self):return [device()]
            def activate(self,device):pass
            def write_frame(self,device,colors,mode):self.writes.append(colors)
            def close(self):pass
        adapter=ExtraAdapter()
        other=core.Center(Path(self.tmp.name)/'other.json',self.tmp.name,adapters=[adapter])
        other.refresh(inventory=False)
        self.assertEqual(other.devices[0]['backend'],'fixture-usb')
        other.start(dict(config={},devices=[other.devices[0]['id']]));other.worker.join(2)
        self.assertEqual(len(adapter.writes),1);other.close()

    def test_invalid_config_layout_and_nonfinite_values(self):
        for value in ({'brightness':float('nan')},{'speed':True},{'palette':['oops']},{'mode':'firmware'}):
            with self.assertRaises(ValueError):core.scene_config(value)
        with self.assertRaises(ValueError):self.core.set_layout({'missing':dict(x=0,y=0)})
    def test_failed_device_does_not_stop_other_device(self):
        def write(index,colors):
            if index==0:raise ConnectionError('Unplugged')
            self.sdk.calls.append(('survivor',index))
        self.sdk.colors=write
        self.core.start(dict(config={},devices=[d['id'] for d in self.core.devices]));self.core.worker.join(2)
        self.assertIn(('survivor',1),self.sdk.calls);self.assertIn('Unplugged',self.core.errors[0])
    def test_usb_inventory_excludes_serials_and_cannot_imply_controller_access(self):
        rows=core.project_usb({'items':[{'_name':'RGB Keyboard','vendor_id':'0x1234 (Vendor)','product_id':'0xabcd','manufacturer':'Vendor','serial_num':'SECRET'}]})
        self.assertEqual(rows[0]['category'],'keyboard');self.assertEqual(rows[0]['usb_id'],'1234:abcd');self.assertNotIn('SECRET',json.dumps(rows))
    def test_common_clock_produces_matching_spectrum_and_bounded_wave(self):
        scene=core.scene_config(dict(mode='spectrum'))
        self.assertEqual(core.frame(scene,1,dict(x=0),2),core.frame(scene,1,dict(x=1),2))
        scene=core.scene_config(dict(mode='wave',brightness=100,palette=['ff0000','0000ff']))
        self.assertNotEqual(core.frame(scene,1,dict(x=0),0),core.frame(scene,1,dict(x=.5),0))


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.core=core.Center(Path(self.tmp.name)/'scenes.json',self.tmp.name,FakeSDK(),FakeNative())
        self.server=LocalServer(self.core,'private-test-credential');self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.core.close();self.tmp.cleanup()
    def request(self,path='/v1/status',headers=None,body=None):
        url='http://127.0.0.1:'+str(self.server.server_port)+path
        request=urllib.request.Request(url,data=None if body is None else json.dumps(body).encode(),headers=headers or {})
        return urllib.request.urlopen(request,timeout=2)
    def test_no_auth_browser_origin_and_rebinding_host_are_rejected(self):
        for headers,expected in (({},401),({'Authorization':'Bearer private-test-credential','Origin':'https://example.com'},403),({'Authorization':'Bearer private-test-credential','Host':'evil.example'},403)):
            with self.assertRaises(HTTPError) as caught:self.request(headers=headers)
            self.assertEqual(caught.exception.code,expected)
    def test_authorized_status_has_no_credential_and_local_bind_only(self):
        response=self.request(headers={'Authorization':'Bearer private-test-credential'})
        value=json.load(response);self.assertTrue(value['local_only']);self.assertNotIn('private-test-credential',str(value))
        self.assertEqual(self.server.server_address[0],'127.0.0.1')
    def test_post_requires_json_and_validated_scene(self):
        headers={'Authorization':'Bearer private-test-credential','Content-Type':'application/json'}
        with self.assertRaises(HTTPError) as caught:self.request('/v1/scene/start',headers,dict(devices=['missing'],config={}))
        self.assertEqual(caught.exception.code,400)
        response=self.request('/v1/scenes/save',headers,dict(name='Local',config={}))
        self.assertEqual(json.load(response)['scenes'][0]['name'],'Local')


class CoreLifecycleTests(unittest.TestCase):
    def test_real_process_private_discovery_and_graceful_shutdown(self):
        import os,subprocess,sys
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);discovery=root/'session.json'
            process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve().parents[1]/'center_service.py'),'--directory',temp,'--discovery',str(discovery),'--profiles',str(root/'profiles'),'--scenes',str(root/'scenes.json'),'--owner-pid',str(os.getpid())],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                deadline=time.monotonic()+5
                while not discovery.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(discovery.exists())
                info=json.loads(discovery.read_text());self.assertEqual(info['pid'],process.pid)
                self.assertEqual(discovery.stat().st_mode&0o777,0o600)
                request=urllib.request.Request('http://127.0.0.1:'+str(info['port'])+'/v1/status',headers={'Authorization':'Bearer '+info['credential']})
                self.assertEqual(json.load(urllib.request.urlopen(request,timeout=2))['devices'],[])
                process.terminate();process.wait(timeout=5)
                self.assertEqual(process.returncode,0);self.assertFalse(discovery.exists())
            finally:
                if process.poll() is None:process.kill();process.wait()
                process.communicate()


class NativeAdapterTests(unittest.TestCase):
    def test_only_bound_confirmed_gpu_is_controllable_and_twin_ids_are_unique(self):
        import scanner
        fp='a'*64
        adapter=dict(pci={'vendor-id':0x10de,'device-id':0x2704,'subsystem-vendor-id':0x196e,'subsystem-id':0x13bc},verified_profile='pny-4080-196e-13bc',nvrm_bound=True)
        report=dict(configuration_fingerprint=fp,lighting_configuration={'status':'supported'},adapters=[adapter,dict(adapter,nvrm_bound=False)])
        with tempfile.TemporaryDirectory() as temp:
            Path(temp,'profile-'+fp+'.json').write_text(json.dumps(dict(schema=1,fingerprint=fp,userConfirmed=True,successfulSteps=3,verifiedEffects=['static','gradient','cycle','breath','wave'])))
            with patch.object(scanner,'collect',return_value=report):rows=core.NativeGPU(temp).discover()
            self.assertTrue(rows[0]['controllable']);self.assertFalse(rows[1]['controllable'])
            self.assertNotEqual(rows[0]['id'],rows[1]['id']);self.assertEqual(rows[0]['fingerprint'],rows[1]['fingerprint'])
