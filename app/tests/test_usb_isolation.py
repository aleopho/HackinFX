import threading,unittest
from usb_devices import IsolatedHIDTransport,HIDError
class IsolationTests(unittest.TestCase):
    def test_slow_device_cannot_hold_fast_device_rpc_lock(self):
        entered=threading.Event();release=threading.Event();fast_done=threading.Event();created=[]
        class Channel:
            def __init__(self):self.calls=[];self.closed=False
            def call(self,value,timeout=None):
                self.calls.append(value)
                if value['handle']=='slow':entered.set();release.wait(2)
                else:fast_done.set()
                return {'ok':True}
            def close(self):self.closed=True
        def factory():
            c=Channel();created.append(c);return c
        t=IsolatedHIDTransport(channel_factory=factory)
        slow=threading.Thread(target=lambda:t.call(dict(command='output',handle='slow')));slow.start();self.assertTrue(entered.wait(1))
        fast=threading.Thread(target=lambda:t.call(dict(command='output',handle='fast')));fast.start()
        try:self.assertTrue(fast_done.wait(.5));self.assertEqual(len(created),2)
        finally:release.set();slow.join();fast.join();t.close()
        self.assertTrue(all(c.closed for c in created))
    def test_same_collection_reuses_channel_and_has_bounded_count(self):
        class Channel:
            def call(self,value,timeout=None):return {'ok':True}
            def close(self):pass
        t=IsolatedHIDTransport(channel_factory=Channel)
        t.call({'handle':'a'});first=t.channels['a'];t.call({'handle':'a'});self.assertIs(t.channels['a'],first)
        for n in range(63):t.call({'handle':str(n)})
        with self.assertRaises(HIDError):t.call({'handle':'overflow'})
        t.close();self.assertFalse(t.channels)
