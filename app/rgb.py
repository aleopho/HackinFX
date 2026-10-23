#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# PNY effect packet adaptation: OpenRGB / yufan (2023), GPL-2.0-or-later.
# Python adaptation developed 2026-10-23; see LICENSE.md and COPYING.
"""Experimental PNY RGB test. Defaults to metadata only; --apply sends one write per selected LED.

Protocol evidence: SOURCES-RGB.md. NVIDIA ABI notice: NOTICE.txt.
"""
import argparse
import ctypes as C
import json
import platform
from pathlib import Path
import sys
import probe as p
import profiles

U8, U16 = C.c_uint8, C.c_uint16


class Indexed(C.Structure):
    _fields_ = [('port', U8), ('write', U8), ('address', U16),
                ('flags', p.U32), ('index_length', p.U32), ('index', U8 * 4),
                ('length', p.U32), ('message', p.U64)]


class TableEntry(C.Structure):
    _fields_ = [('type', U8), ('address', U16), ('port', U8), ('device_index', U8)]


class Table(C.Structure):
    _fields_ = [('count', U8), ('entries', TableEntry * 32)]


def check_abi():
    p.check_abi()
    if (C.sizeof(Indexed), Indexed.message.offset, C.sizeof(TableEntry),
            C.sizeof(Table), Table.entries.offset) != (32, 24, 6, 194, 2):
        raise p.ProbeError('RGB ABI mismatch')


def effect_packets(effect, color, led, speed=50, brightness=255, colors=None):
    """Bounded PNY lighting payloads; hardware effects need no host animation loop."""
    if effect not in ('static', 'gradient', 'cycle', 'breath', 'wave', 'off'):
        raise p.ProbeError('Unknown effect')
    if type(speed) is not int or not 0 <= speed <= 100 or type(brightness) is not int or not 0 <= brightness <= 255:
        raise p.ProbeError('Invalid speed or brightness')
    def scale(rgb):
        if len(rgb) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in rgb):
            raise p.ProbeError('Invalid RGB components')
        return tuple((v * brightness + 127) // 255 for v in rgb)
    if effect == 'off':
        return [(0,) * 7]
    if effect == 'cycle':
        return [(3, brightness, 0xb2 - round(speed * 0xb2 / 100), 0, 0xaa, 0, 0)]
    if effect == 'wave':
        return [(4, brightness, 0xbf - round(speed * 0xbf / 100), 0, 0xaa, 0, 0)]
    if effect == 'breath':
        return [(2, 255, 0x19 - round(speed * 0x19 / 100), 1, *scale(color))]
    if effect == 'gradient':
        if colors is None or len(colors) != 3:
            raise p.ProbeError('Gradient requires three zone colors')
        return [(6, 255, index, 0, *scale(value)) for index, value in enumerate(colors)]
    return [(6, 255, index, 0, *scale(color)) for index in ((0, 1, 2) if led == 'all' else (led,))]


def controller_transactions(profile, effect, color, led, speed=50, brightness=255, colors=None):
    if effect != 'off' and effect not in profile.effects:
        raise p.ProbeError('Effect unavailable on this controller')
    if profile.controller == 'PNYLovelaceGPUController':
        return [(profile.address,profile.register,packet) for packet in effect_packets(effect,color,led,speed,brightness,colors)]
    if profile.controller == 'AsusAuraGPUController':
        scaled = effect_packets('static',color,0,speed,0 if effect == 'off' else brightness)[0][-3:]
        mode = {'off':1,'static':1,'cycle':4,'breath':2}[effect]
        return [(profile.address,register,(value,)) for register,value in zip((4,5,6),scaled)] + [(profile.address,7,(mode,))]
    if profile.controller != 'EVGAPascalGPUController':
        raise p.ProbeError('Controller implementation unavailable')
    # OpenRGB EVGAGPUv1: three volatile RGB registers and mode. Never call
    # SaveSettings (0x23/0xe5); testing must not write controller flash.
    scaled = effect_packets('static',color,0,speed,brightness)[0][-3:]
    mode = {'off':0,'static':1,'cycle':2,'breath':5}[effect]
    return ([(profile.address,register,(value,)) for register,value in zip((9,10,11),scaled)] if effect in ('static','breath') else []) + [(profile.address,12,(mode,))]


class RGB(p.RM):
    def __init__(self, transport, report, port=None, color=(32, 0, 0), led=0, apply=False, effect='static', speed=50, brightness=255, colors=None, profile=None):
        super().__init__(transport, report)
        if port is not None and port not in (1, 2):
            raise p.ProbeError('Only experimental candidate ports 1 and 2 are supported')
        if led not in (0, 1, 2, 'all') or len(color) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in color):
            raise p.ProbeError('Invalid LED or RGB color')
        self.profile = profile
        self.port, self.color, self.led, self.apply = port, color, led, apply
        self.transactions = controller_transactions(profile,effect,color,led,speed,brightness,colors) if profile else [(0x60,2,packet) for packet in effect_packets(effect,color,led,speed,brightness,colors)]
        self.report['effect'] = effect

    def after_ports(self, obj, ports):
        table = Table()
        req = p.Control(self.client, obj, 0x402c0104, 0, C.addressof(table), C.sizeof(table), 0xffffffff)
        # Failure of this optional metadata command is recorded. No fallback write.
        self.call(0x2a, req)
        if table.count > 32:
            raise p.ProbeError('Invalid DCB device count')
        self.report['dcb_devices'] = [dict(type=e.type, address=e.address, port=e.port,
                                         device_index=e.device_index) for e in table.entries[:table.count]]
        self.report['port_mapping'] = 'unconfirmed: NvAPI port 1 is not an RM mapping'
        if not self.apply:
            return
        if self.port is None:
            raise p.ProbeError('--apply requires an explicit experimental --port 1 or 2')
        flags = ports[self.port]
        if flags & 0x15 != 0x11:
            raise p.ProbeError('Selected port must be implemented, validated and non-DDC')
        if self.profile and self.profile.controller == 'AsusAuraGPUController':
            magic = []
            for register in (0x20,0x21):
                payload = (U8 * 1)()
                request = Indexed(port=self.port,write=0,address=self.profile.address << 1,flags=0,index_length=1,index=(U8 * 4)(register,0,0,0),length=1,message=C.addressof(payload))
                req = p.Control(self.client,obj,0x402c0102,0,C.addressof(request),C.sizeof(request),0xffffffff)
                self.report['i2c_transactions_attempted'] = self.report.get('i2c_transactions_attempted',0) + 1
                self.call(0x2a,req)
                magic.append(payload[0])
            if magic != [0x15,0x89]:
                raise p.ProbeError('ASUS Aura controller signature mismatch; no lighting writes sent')
        self.report['write_plans'] = []
        self.report['writes_completed'] = 0
        for address, register, packet in self.transactions:
            payload = (U8 * len(packet))(*packet)
            request = Indexed(port=self.port, write=1, address=address << 1, flags=0,
                              index_length=1, index=(U8 * 4)(register, 0, 0, 0),
                              length=len(packet), message=C.addressof(payload))
            plan = dict(port=self.port, address_7bit='0x%02x' % address, register='0x%02x' % register,
                        payload=list(payload), speed_khz=100)
            self.report['write_plan'] = plan
            self.report['write_plans'].append(plan)
            self.report['i2c_transactions_attempted'] = self.report.get('i2c_transactions_attempted', 0) + 1
            req = p.Control(self.client, obj, 0x402c0102, 0, C.addressof(request), C.sizeof(request), 0xffffffff)
            self.call(0x2a, req)
            self.report['writes_completed'] += 1
        self.report['write_completed'] = True
        self.report['rgb_controller_reachable'] = 'write accepted; visible color change requires observation'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--port', type=int, choices=(1, 2))
    parser.add_argument('--color', default='200000', help='6-digit RGB hex; default dim red')
    parser.add_argument('--led', choices=('0', '1', '2', 'all'), default='0')
    parser.add_argument('--effect', choices=('static', 'gradient', 'cycle', 'breath', 'wave', 'off'), default='static')
    parser.add_argument('--speed', type=int, choices=range(101), default=50, metavar='0..100')
    parser.add_argument('--brightness', type=int, choices=range(256), default=255, metavar='0..255')
    parser.add_argument('--colors', help='Three comma-separated RGB hex colors for gradient')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if len(args.color) != 6:
            raise ValueError()
        color = tuple(bytes.fromhex(args.color))
        if len(color) != 3:
            raise ValueError()
    except ValueError:
        parser.error('--color requires exactly six hex digits')
    colors = None
    if args.colors is not None:
        try:
            colors = tuple(tuple(bytes.fromhex(value)) for value in args.colors.split(','))
            if len(colors) != 3 or any(len(value) != 3 for value in colors):
                raise ValueError()
        except ValueError:
            parser.error('--colors requires three comma-separated 6-digit RGB colors')
    if args.effect == 'gradient' and colors is None:
        parser.error('--effect gradient requires --colors')
    if args.apply and args.port is None:
        parser.error('--apply requires --port')
    try:
        handle = args.output.open('x', encoding='utf-8')
    except OSError as exc:
        parser.exit(2, 'No hardware access: %s\n' % exc)
    report = dict(tool_version='0.4.0', mode='rgb-test' if args.apply else 'dcb-metadata',
                  error=None, write_completed=False, i2c_transactions_attempted=0)
    native = None
    try:
        if sys.platform != 'darwin' or platform.machine() != 'x86_64':
            raise p.ProbeError('x86-64 macOS required')
        check_abi()
        report['pci_devices'] = devices = p.inventory()
        profile = profiles.select(devices)
        report['profile'] = profile.key
        if args.apply and args.port != profile.port:
            raise p.ProbeError('Port does not match the exact controller profile')
        native = p.Native()
        native.open()
        RGB(native, report, args.port, color, 'all' if args.led == 'all' else int(args.led), args.apply,
            args.effect, args.speed, args.brightness, colors, profile=profile).run()
    except Exception as exc:
        report['error'] = str(exc)
    finally:
        if native:
            report['connection_close_errors'] = native.close()
        with handle:
            json.dump(report, handle, indent=2)
            handle.write('\n')
        print(json.dumps(report, indent=2))
        print('Saved:', args.output.resolve())
    return int(bool(report['error'] or report.get('cleanup_error') or report.get('connection_close_errors')))


if __name__ == '__main__':
    sys.exit(main())
