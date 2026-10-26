import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import nanoleaf_control as nano

TOKEN='private_token_12345'
def info():return dict(model='NL42',name='Shapes Triangles',serialNo='PRIVATE',panelLayout=dict(layout=dict(positionData=[dict(panelId=1,x=0,y=0,shapeType=12),dict(panelId=700,x=0,y=0,shapeType=8),dict(panelId=900,x=10,y=20,shapeType=9)])))
class Sock:
    def __init__(self,*args):self.sent=[];self.closed=False
    def settimeout(self,value):pass
    def connect(self,value):self.address=value
    def send(self,value):self.sent.append(value);return len(value)
    def close(self):self.closed=True
class NanoleafTests(unittest.TestCase):
    def test_exact_big_endian_panel_frame_and_interpolation(self):
        self.assertEqual(nano.packet([700],[(1,2,3)]),bytes.fromhex('000102bc010203000001'))
        for ids,colors in [([700,700],[(1,2,3)]*2),([700],[(256,0,0)]),([0],[(1,2,3)])]:
            with self.assertRaises(ValueError):nano.packet(ids,colors)
    def test_layout_uses_real_ids_and_coordinates_not_controller(self):
        ids,positions=nano.layout(info());self.assertEqual(ids,[700,900]);self.assertEqual(positions,[dict(x=0,y=1),dict(x=1,y=0)])
        bad=info();bad['panelLayout']['layout']['positionData'][-1]['shapeType']=999
        with self.assertRaises(ValueError):nano.layout(bad)
        bad=info();bad['model']='NL22'
        with self.assertRaises(ValueError):nano.layout(bad)
    def test_local_address_and_token_bounds(self):
        for ip in ['127.0.0.1','0.0.0.0','8.8.8.8','224.0.0.1','http://192.168.1.4','192.168.1.4/path']:
            with self.assertRaises(ValueError):nano.local_ip(ip)
        self.assertEqual(nano.local_ip('192.168.1.4'),'192.168.1.4')
        for token in ['abc','bad/token',TOKEN+'?secret=1']:
            with self.assertRaises(ValueError):nano.token_value(token)
    def test_pair_reads_layout_without_color_then_explicit_activation_streams(self):
        calls=[]
        def http(ip,token,method,suffix='',body=None):
            calls.append((token,method,suffix,body));return dict(auth_token=TOKEN) if token is None else info()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'pairings.json';a=nano.NanoleafAdapter(path,http,Sock)
            self.assertEqual(a.discover(),[]);a.pair('192.168.1.4')
            self.assertEqual([v[1] for v in calls],['POST','GET']);self.assertEqual(path.stat().st_mode&0o777,0o600)
            row=a.discover()[0];self.assertNotIn(TOKEN,json.dumps(row));self.assertNotIn('PRIVATE',json.dumps(row));self.assertTrue(row['startup_excluded']);self.assertEqual(row['led_count'],2)
            a.activate(row);a.write_frame(row,[(1,2,3),(4,5,6)],'wave')
            sock=a.sockets[row['id']];self.assertEqual(sock.address,('192.168.1.4',60222));self.assertEqual(len(sock.sent),1)
            self.assertEqual(calls[-2][3]['write']['extControlVersion'],'v2');self.assertEqual(calls[-1][3]['brightness']['value'],100)
            a.close();self.assertTrue(sock.closed)
    def test_pairing_failure_does_not_replace_existing_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'pairings.json';path.write_text('original')
            a=nano.NanoleafAdapter(path,http=lambda *args:dict(auth_token=TOKEN,model='NL22'))
            with self.assertRaises(ValueError):a.pair('192.168.1.4')
            self.assertEqual(path.read_text(),'original')
    def test_pacing_limits_to_ten_hz_without_busy_wait(self):
        with tempfile.TemporaryDirectory() as folder:
            a=nano.NanoleafAdapter(Path(folder)/'p',http=lambda *args,**kwargs:info(),socket_factory=Sock)
            a.paired=[dict(ip='192.168.1.4',token=TOKEN)];row=a.discover()[0];a.activate(row)
            with patch.object(nano.time,'monotonic',side_effect=[10,10,10.02,10.1]),patch.object(nano.time,'sleep') as sleep:
                a.write_frame(row,[(1,2,3)]*2,'twinkle');a.write_frame(row,[(1,2,3)]*2,'twinkle')
                self.assertAlmostEqual(sleep.call_args.args[0],.08)
            a.close()

    def test_paired_network_panels_are_not_activated_at_startup(self):
        import center_core as core
        from test_center import FakeSDK,FakeNative,device
        row=device();row.update(category='light',startup_excluded=True,controllable=True,direct=True)
        with tempfile.TemporaryDirectory() as folder:
            sdk=FakeSDK([row]);center=core.Center(Path(folder)/'scene.json',folder,sdk=sdk,native=FakeNative())
            try:center.initialize(inventory=False);self.assertEqual(sdk.calls,[])
            finally:center.close()

    def test_bonjour_discovery_accepts_shapes_and_uses_stable_controller_id(self):
        calls=[]
        def run(args,seconds):
            calls.append(args)
            if args[0]=='-B':return '08:00:00 Add 2 7 local. _nanoleafapi._tcp. Shapes Living Room\n'
            if args[0]=='-L':return 'Shapes Living Room can be reached at shapes.local.:16021\nid=12:34:56:78:9A:BC md=NL42 srcvers=7.1.6\n'
            return '08:00:00 Add 2 7 shapes.local. 192.168.1.40 120\n'
        found=nano.discover_shapes(run)
        self.assertEqual(len(found),1);self.assertEqual(found[0]['name'],'Shapes Living Room');self.assertEqual(found[0]['address'],'192.168.1.40')
        self.assertEqual(len(found[0]['id']),24);self.assertEqual(len(calls),3)
    def test_address_change_rediscovers_identity_without_pairing_or_lighting(self):
        import hashlib
        service='a'*24;calls=[]
        def http(ip,token,method,suffix='',body=None):
            calls.append((ip,token,method,suffix))
            if ip=='192.168.1.4':raise ValueError('offline')
            return info()
        with tempfile.TemporaryDirectory() as folder:
            a=nano.NanoleafAdapter(Path(folder)/'p',http,Sock)
            a.paired=[dict(ip='192.168.1.4',token=TOKEN,service_id=service,serial_hash=hashlib.sha256(b'PRIVATE').hexdigest())]
            with patch.object(nano,'discover_shapes',return_value=[dict(id=service,address='192.168.1.40')]):row=a.discover()[0]
            self.assertTrue(row['controllable']);self.assertEqual(a.paired[0]['ip'],'192.168.1.40')
            self.assertEqual([v[2] for v in calls],['GET','GET']);self.assertFalse(a.sockets)
    def test_address_change_rejects_wrong_physical_controller(self):
        service='a'*24
        with tempfile.TemporaryDirectory() as folder:
            a=nano.NanoleafAdapter(Path(folder)/'p',http=lambda ip,*args:(_ for _ in ()).throw(ValueError()) if ip=='192.168.1.4' else info())
            a.paired=[dict(ip='192.168.1.4',token=TOKEN,service_id=service,serial_hash='0'*64)]
            with patch.object(nano,'discover_shapes',return_value=[dict(id=service,address='192.168.1.40')]):row=a.discover()[0]
            self.assertFalse(row['controllable']);self.assertEqual(a.paired[0]['ip'],'192.168.1.4')
