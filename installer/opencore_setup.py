#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Installer-only OpenCore driver transaction. Never loaded by app discovery."""
import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import uuid
import zipfile

BUNDLE='macUSPCIO_Smbus.kext'
IDENTIFIER='com.sn-labs.macUSPCIO'
class SetupError(RuntimeError):pass

def plist_command(*args):
    return plistlib.loads(subprocess.check_output(list(args),stderr=subprocess.PIPE))

def boot_partition_guids(data):
    """Parse actual UEFI HardDrive media nodes, never scan for arbitrary UUIDs."""
    guids=set();offset=0
    while offset+4<=len(data):
        kind,sub=data[offset:offset+2];size=int.from_bytes(data[offset+2:offset+4],'little')
        if size<4 or offset+size>len(data):break
        node=data[offset:offset+size]
        if kind==4 and sub==1 and size==42 and node[41]==2:guids.add(str(uuid.UUID(bytes_le=node[24:40])).lower())
        offset+=size
    return guids

def choose_candidate(candidates,boot_guids):
    preferred=[c for c in candidates if c['uuid'].lower() in boot_guids]
    if len(preferred)==1:return preferred[0]
    if not boot_guids and len(candidates)==1:return candidates[0]
    raise SetupError('No unique OpenCore EFI found. Nothing was changed. Keep only the intended boot EFI connected and retry the RAM component.')

def edited_config(config,relative=BUNDLE):
    result=copy.deepcopy(config)
    if not isinstance(result,dict) or not all(k in result for k in ('ACPI','Booter','Kernel','Misc','NVRAM','PlatformInfo','UEFI')):raise SetupError('Not a complete OpenCore configuration')
    kernel=result.get('Kernel')
    if not isinstance(kernel,dict) or not isinstance(kernel.get('Add'),list):raise SetupError('Invalid Kernel/Add array')
    entries=kernel['Add'];matches=[]
    for i,item in enumerate(entries):
        if not isinstance(item,dict) or not isinstance(item.get('BundlePath'),str):raise SetupError('Invalid Kernel/Add entry')
        name=Path(item['BundlePath']).name.lower()
        if name in ('macuspcio.kext','macuspcio_smbus.kext'):
            if item['BundlePath']!=relative:raise SetupError('Existing macUSPCIO uses another bundle path; resolve it before automatic installation')
            matches.append(i)
    if len(matches)>1:raise SetupError('Duplicate macUSPCIO Kernel/Add entries')
    entry=dict(Arch='x86_64',BundlePath=relative,Comment='HackinFX SMBus transport',Enabled=True,ExecutablePath='Contents/MacOS/macUSPCIO',MinKernel='24.0.0',MaxKernel='',PlistPath='Contents/Info.plist')
    if matches:
        old=entries[matches[0]]
        # Keep explicit kernel bounds/comments and unknown keys; only activate/update paths.
        entry.update(old);entry.update(Enabled=True,Arch='x86_64',ExecutablePath='Contents/MacOS/macUSPCIO',PlistPath='Contents/Info.plist')
        entries[matches[0]]=entry
    else:entries.append(entry)
    return result

def atomic_bytes(path,data):
    temporary=path.with_name('.hackinfx-'+uuid.uuid4().hex)
    try:
        with temporary.open('xb') as out:out.write(data);out.flush();os.fsync(out.fileno())
        os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)

def install(efi,kext,backup_root):
    efi=Path(efi);kext=Path(kext);config=efi/'EFI/OC/config.plist';destination=efi/'EFI/OC/Kexts'/BUNDLE
    # Reject filesystem redirection and malformed binary before creating backups.
    for p in (efi/'EFI',efi/'EFI/OC',config,destination.parent,destination):
        if p.is_symlink():raise SetupError('Symlinked EFI paths are not supported')
    if not (efi/'EFI/OC/OpenCore.efi').is_file():raise SetupError('OpenCore.efi is missing')
    info=plistlib.loads((kext/'Contents/Info.plist').read_bytes())
    if info.get('CFBundleExecutable')!='macUSPCIO':raise SetupError('Unexpected driver executable')
    if info.get('CFBundleIdentifier')!=IDENTIFIER:raise SetupError('Unexpected driver identity')
    if not destination.parent.is_dir():raise SetupError('OpenCore Kexts directory is missing')
    # A renamed conflicting transport must not be installed twice.
    for existing in destination.parent.glob('*.kext'):
        try:other=plistlib.loads((existing/'Contents/Info.plist').read_bytes())
        except (OSError,ValueError):continue
        if other.get('CFBundleIdentifier')==IDENTIFIER and existing.name!=BUNDLE:raise SetupError('A renamed macUSPCIO driver already exists')
    original=config.read_bytes();before=hashlib.sha256(original).hexdigest()
    parsed=plistlib.loads(original);updated=edited_config(parsed)
    changed=plistlib.dumps(updated,fmt=plistlib.FMT_BINARY if original.startswith(b'bplist') else plistlib.FMT_XML,sort_keys=False)
    if plistlib.loads(changed)!=updated:raise SetupError('Config round-trip failed')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    backup=Path(backup_root)/stamp;backup.mkdir(parents=True,mode=0o700)
    shutil.copytree(efi/'EFI',backup/'EFI',symlinks=True)
    (backup/'transaction.json').write_text(json.dumps(dict(schema=1,original_config_sha256=before,target=str(efi),driver=info['CFBundleIdentifier'],status='backed-up'),indent=2))
    staged=destination.with_name('.hackinfx-stage-'+uuid.uuid4().hex)
    previous=destination.with_name('.hackinfx-old-'+uuid.uuid4().hex)
    installed=False;moved=False;config_written=False
    try:
        shutil.copytree(kext,staged,symlinks=False)
        if config.read_bytes()!=original:raise SetupError('Config changed during installation; retry after closing editors')
        if destination.exists():os.replace(destination,previous);moved=True
        os.replace(staged,destination);installed=True
        atomic_bytes(config,changed);config_written=True
        # Re-read persisted files before declaring success.
        if plistlib.loads(config.read_bytes())!=updated:raise SetupError('Persisted config validation failed')
        if (destination/'Contents/Info.plist').read_bytes()!=(kext/'Contents/Info.plist').read_bytes():raise SetupError('Persisted driver validation failed')
        (backup/'result.json').write_text(json.dumps(dict(status='installed',reboot_required=True,config_sha256=hashlib.sha256(changed).hexdigest()),indent=2))
    except Exception:
        if config_written and config.read_bytes()==changed:atomic_bytes(config,original)
        if installed:shutil.rmtree(destination)
        if moved:os.replace(previous,destination)
        raise
    finally:
        shutil.rmtree(staged,ignore_errors=True)
    shutil.rmtree(previous,ignore_errors=True)
    return backup

def automatically_install(kext,backup_root):
    if os.geteuid()!=0:raise SetupError('Run through the macOS installer with administrator authorization')
    disks=plist_command('/usr/sbin/diskutil','list','-plist');partitions=[]
    for disk in disks.get('AllDisksAndPartitions',[]):
        for part in disk.get('Partitions',[]):
            if part.get('Content')=='EFI':partitions.append(part['DeviceIdentifier'])
    boot=set()
    try:
        def visit(value):
            if isinstance(value,dict):
                for k,v in value.items():
                    if k in ('boot-device-path','boot-file','boot-device-data') and isinstance(v,bytes):boot.update(boot_partition_guids(v))
                    visit(v)
            elif isinstance(value,list):
                for v in value:visit(v)
        visit(plist_command('/usr/sbin/ioreg','-a','-r','-p','IODeviceTree','-n','chosen'))
    except (subprocess.CalledProcessError,ValueError):pass
    mounted=[];candidates=[]
    try:
        for identifier in partitions:
            info=plist_command('/usr/sbin/diskutil','info','-plist',identifier)
            point=info.get('MountPoint')
            if not point:
                subprocess.run(['/usr/sbin/diskutil','mount','readOnly',identifier],check=True,capture_output=True)
                mounted.append(identifier);info=plist_command('/usr/sbin/diskutil','info','-plist',identifier);point=info.get('MountPoint')
            if point and (Path(point)/'EFI/OC/config.plist').is_file() and (Path(point)/'EFI/OC/OpenCore.efi').is_file():
                candidates.append(dict(device=identifier,path=point,uuid=info.get('DiskUUID','')))
        candidate=choose_candidate(candidates,boot)
        # Remount only an EFI we mounted ourselves; do not disrupt a user-mounted volume.
        if candidate['device'] in mounted:
            subprocess.run(['/usr/sbin/diskutil','unmount',candidate['device']],check=True,capture_output=True)
            subprocess.run(['/usr/sbin/diskutil','mount',candidate['device']],check=True,capture_output=True)
            candidate['path']=plist_command('/usr/sbin/diskutil','info','-plist',candidate['device'])['MountPoint']
        backup=install(candidate['path'],kext,backup_root)
        print('OpenCore driver installed and enabled. Reboot required. EFI backup: '+str(backup))
    finally:
        for identifier in mounted:subprocess.run(['/usr/sbin/diskutil','unmount',identifier],capture_output=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--kext',required=True,type=Path);parser.add_argument('--backups',required=True,type=Path);args=parser.parse_args()
    try:automatically_install(args.kext,args.backups)
    except Exception as exc:raise SystemExit('HackinFX OpenCore setup failed: '+str(exc))
