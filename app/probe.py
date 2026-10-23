#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Experimental macOS/NullMoth port-metadata probe. No I2C transactions.

ABI definitions: NVIDIA open-gpu-kernel-modules 610.57.04 (see SOURCES.md).
No third-party Python packages required. Run without sudo.
"""
import argparse
import ctypes as C
import json
import platform
import plistlib
from pathlib import Path
import subprocess
import sys

U32, U64 = C.c_uint32, C.c_uint64


class Alloc(C.Structure):
    _fields_ = [(n, U32) for n in ('root', 'parent', 'new', 'cls')] + [
        ('params', U64), ('size', U32), ('status', U32)]


class Control(C.Structure):
    _fields_ = [(n, U32) for n in ('client', 'obj', 'cmd', 'flags')] + [
        ('params', U64), ('size', U32), ('status', U32)]


class Free(C.Structure):
    _fields_ = [(n, U32) for n in ('root', 'parent', 'old', 'status')]


class Device(C.Structure):
    _fields_ = [(n, U32) for n in ('id', 'share', 'target_client', 'target_device', 'flags')] + [
        ('va_size', U64), ('va_start', U64), ('va_limit', U64), ('va_mode', U32)]


class IdInfo(C.Structure):
    _fields_ = [(n, U32) for n in ('gpu', 'flags', 'device', 'subdevice', 'sli', 'board', 'instance')] + [
        ('numa', C.c_int32)]


def check_abi():
    expected = [(Alloc, 32), (Control, 32), (Free, 16), (Device, 56), (IdInfo, 32)]
    if C.sizeof(C.c_void_p) != 8 or sys.byteorder != 'little':
        raise RuntimeError('Only a 64-bit little-endian process is supported')
    for cls, size in expected:
        if C.sizeof(cls) != size:
            raise RuntimeError('ABI size mismatch: ' + cls.__name__)
    if Alloc.params.offset != 16 or Control.params.offset != 16 or Device.va_size.offset != 24:
        raise RuntimeError('ABI alignment mismatch')


class ProbeError(RuntimeError):
    pass


class RM:
    """Only object lifecycle and three metadata commands are permitted."""
    def __init__(self, transport, report):
        self.transport, self.report = transport, report
        self.client = 0

    def call(self, escape, data):
        event = {'escape': hex(escape), 'size': C.sizeof(data)}
        if isinstance(data, Alloc):
            event['class'] = hex(data.cls)
        if isinstance(data, Control):
            event['command'] = hex(data.cmd)
        self.report.setdefault('calls', []).append(event)
        kr, size = self.transport(escape, data)
        event.update(ioreturn='0x%08x' % kr, returned_size=size, rm_status='0x%08x' % data.status)
        if kr or size != C.sizeof(data) or data.status:
            raise ProbeError('RM request failed: ' + json.dumps(event))

    def alloc(self, parent, handle, cls, params=None):
        if cls not in (0x41, 0x80, 0x2080, 0x402c):
            raise ProbeError('Allocation class outside metadata allowlist')
        req = Alloc(self.client, parent, handle, cls,
                    C.addressof(params) if params is not None else 0,
                    C.sizeof(params) if params is not None else 0, 0xffffffff)
        self.call(0x2b, req)
        if not req.new:
            raise ProbeError('RM returned a zero handle')
        return req.new

    def control(self, obj, command, params):
        allowed = {0x201: 128, 0x205: 32, 0x402c0101: 16}
        if allowed.get(command) != C.sizeof(params):
            raise ProbeError('Command/size outside metadata allowlist')
        req = Control(self.client, obj, command, 0, C.addressof(params), C.sizeof(params), 0xffffffff)
        self.call(0x2a, req)

    def run(self):
        try:
            self.client = self.alloc(0, 0, 0x41)
            ids = (U32 * 32)(*([0xffffffff] * 32))
            self.control(self.client, 0x201, ids)
            active = [int(x) for x in ids if x != 0xffffffff]
            self.report['attached_gpu_count'] = len(active)
            if len(active) != 1:
                raise ProbeError('Expected exactly one attached RM GPU; refusing to guess')
            info = IdInfo(gpu=active[0])
            self.control(self.client, 0x205, info)
            self.report['instances'] = {'device': info.device, 'subdevice': info.subdevice}
            device = self.alloc(self.client, 0x100, 0x80, Device(id=info.device, share=self.client))
            sub = self.alloc(device, 0x101, 0x2080, U32(info.subdevice))
            i2c = self.alloc(sub, 0x102, 0x402c)
            ports = (C.c_uint8 * 16)()
            self.control(i2c, 0x402c0101, ports)
            self.report['ports'] = [dict(index=i, flags=int(v), implemented=bool(v & 1),
                                         dcb_declared=bool(v & 2), ddc=bool(v & 4),
                                         crtc_mapped=bool(v & 8), validated=bool(v & 16))
                                    for i, v in enumerate(ports)]
            self.report['port_metadata_ok'] = True
            self.report['rgb_controller_reachable'] = 'not tested'
            self.after_ports(i2c, ports)
        finally:
            if self.client:
                # Freeing the root client releases its entire object tree.
                try:
                    self.call(0x29, Free(self.client, 0, self.client, 0xffffffff))
                except Exception as exc:
                    self.report['cleanup_error'] = str(exc)


    def after_ports(self, i2c, ports):
        pass


class Native:
    def __init__(self):
        self.io = C.CDLL('/System/Library/Frameworks/IOKit.framework/IOKit')
        self.system = C.CDLL('/usr/lib/libSystem.B.dylib')
        self.connections = []
        io = self.io
        io.IOServiceMatching.argtypes = [C.c_char_p]
        io.IOServiceMatching.restype = C.c_void_p
        io.IOServiceGetMatchingService.argtypes = [U32, C.c_void_p]
        io.IOServiceGetMatchingService.restype = U32
        io.IOServiceOpen.argtypes = [U32, U32, U32, C.POINTER(U32)]
        io.IOServiceOpen.restype = U32
        io.IOObjectRelease.argtypes = [U32]
        io.IOObjectRelease.restype = U32
        io.IOServiceClose.argtypes = [U32]
        io.IOServiceClose.restype = U32
        io.IOConnectCallMethod.argtypes = [U32, U32, C.POINTER(U64), U32,
            C.c_void_p, C.c_size_t, C.c_void_p, C.c_void_p, C.c_void_p, C.POINTER(C.c_size_t)]
        io.IOConnectCallMethod.restype = U32

    def open(self):
        service = self.io.IOServiceGetMatchingService(0, self.io.IOServiceMatching(b'NVRM'))
        if not service:
            raise ProbeError('No NVRM service found')
        try:
            task = U32.in_dll(self.system, 'mach_task_self_').value
            for kind in (0, 1):
                conn = U32()
                kr = self.io.IOServiceOpen(service, task, kind, C.byref(conn))
                if kr:
                    raise ProbeError('IOServiceOpen type %d: 0x%08x' % (kind, kr))
                self.connections.append(conn.value)
        finally:
            self.io.IOObjectRelease(service)

    def __call__(self, escape, data):
        if escape not in (0x29, 0x2a, 0x2b):
            raise ProbeError('Escape outside allowlist')
        code, length = U64(escape), C.c_size_t(C.sizeof(data))
        out = type(data)()
        kr = self.io.IOConnectCallMethod(self.connections[0], 1, C.byref(code), 1,
            C.byref(data), C.sizeof(data), None, None, C.byref(out), C.byref(length))
        if not kr and length.value == C.sizeof(data):
            C.memmove(C.addressof(data), C.addressof(out), C.sizeof(data))
        return int(kr), int(length.value)

    def close(self):
        errors = []
        for conn in reversed(self.connections):
            kr = self.io.IOServiceClose(conn)
            if kr:
                errors.append('0x%08x' % kr)
        self.connections.clear()
        return errors


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get('IORegistryEntryChildren', []))


def pci_value(node, key):
    value = node.get(key)
    if isinstance(value, bytes):
        return int.from_bytes(value, 'little')
    return value if isinstance(value, int) else None


def inventory():
    raw = subprocess.run(['/usr/sbin/ioreg', '-a', '-r', '-c', 'IOPCIDevice'],
                         capture_output=True, check=True, timeout=20).stdout
    roots = plistlib.loads(raw)
    selected = []
    seen = set()
    for node in walk(roots):
        if pci_value(node, 'vendor-id') != 0x10de:
            continue
        if not any(n.get('IOObjectClass') == 'NVRM' for n in walk([node])):
            continue
        ident = node.get('IORegistryEntryID')
        if ident in seen:
            continue
        seen.add(ident)
        selected.append({k: pci_value(node, k) for k in
                         ('vendor-id', 'device-id', 'subsystem-vendor-id', 'subsystem-id')})
    # Never save the raw IORegistry tree: it can contain unrelated private data.
    return selected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ports', action='store_true', help='query RM I2C port metadata; no bus transactions')
    parser.add_argument('--output', type=Path, default=Path('pny-macos-probe.json'))
    args = parser.parse_args(argv)
    # Reserve the report before any inventory or driver calls.
    try:
        output_handle = args.output.open('x', encoding='utf-8')
    except OSError as exc:
        parser.exit(2, 'Cannot create report; no diagnostic was started: %s\n' % exc)
    try:
        return run_diagnostic(args, output_handle)
    finally:
        output_handle.close()


def run_diagnostic(args, output_handle):
    report = {'tool_version': '0.1.1', 'os': platform.mac_ver()[0], 'arch': platform.machine(),
              'mode': 'port-metadata' if args.ports else 'inventory',
              'port_metadata_ok': False, 'error': None, 'i2c_transactions': 0}
    native = None
    try:
        if sys.platform != 'darwin' or platform.machine() != 'x86_64':
            raise ProbeError('Run this diagnostic on x86-64 macOS with NullMoth, not on Windows/Apple Silicon')
        check_abi()
        report['pci_devices'] = inventory()
        versions = subprocess.run(['/usr/sbin/kextstat', '-b', 'com.nullmoth.NVRM'],
                                  capture_output=True, text=True, timeout=20)
        report['loaded_nvrm'] = versions.stdout.strip()
        report['kextstat'] = {'returncode': versions.returncode, 'stderr': versions.stderr.strip()}
        if args.ports:
            devices = report['pci_devices']
            if len(devices) != 1 or devices[0]['device-id'] != 0x2704 or devices[0]['subsystem-vendor-id'] != 0x196e:
                raise ProbeError('Expected exactly one NVRM-backed PNY RTX 4080 (10de:2704 / 196e); inspect inventory')
            native = Native()
            native.open()
            RM(native, report).run()
    except Exception as exc:
        report['error'] = str(exc)
    finally:
        if native:
            errors = native.close()
            if errors:
                report['connection_close_errors'] = errors
    # Exclusive creation prevents overwriting a previous result by accident.
    json.dump(report, output_handle, indent=2)
    output_handle.write('\n')
    output_handle.flush()
    print(json.dumps(report, indent=2))
    print('Saved:', args.output.resolve())
    return 1 if report['error'] or report.get('cleanup_error') or report.get('connection_close_errors') else 0


if __name__ == '__main__':
    sys.exit(main())
