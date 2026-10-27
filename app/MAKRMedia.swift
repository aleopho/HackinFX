// SPDX-License-Identifier: GPL-3.0-or-later
// MAKR interface-2 dial event reference: OpenLinkHub / Nikola Jurkovic.
import Foundation
import IOKit
import IOKit.hid
import CoreAudio

enum MAKRKnob {
    static func direction(_ report:[UInt8])->Int {
        guard report.count>=5,report.count<=512,report[1]==5 else { return 0 }
        return report[4]==1 ? 1:report[4]==255 ? -1:0
    }
}
final class MAKRMedia {
    static let shared=MAKRMedia()
    var enabled=false { didSet { if enabled && manager==nil { start() } } }
    private var manager:IOHIDManager?
    private var channels=[UInt64:Channel]()
    private var retired=[Channel]()
    private final class Channel {
        let device:IOHIDDevice;let buffer=UnsafeMutablePointer<UInt8>.allocate(capacity:512)
        init(_ device:IOHIDDevice){self.device=device;buffer.initialize(repeating:0,count:512)}
        // Retained until process exit so queued input callbacks never outlive buffers.
    }
    private func start(){
        let m=IOHIDManagerCreate(kCFAllocatorDefault,IOOptionBits(kIOHIDOptionsTypeNone));manager=m
        IOHIDManagerSetDeviceMatching(m,[kIOHIDVendorIDKey:0x1b1c,kIOHIDProductIDKey:0x2b04] as CFDictionary)
        IOHIDManagerRegisterDeviceMatchingCallback(m,{context,_,_,device in
            guard let context=context else{return};Unmanaged<MAKRMedia>.fromOpaque(context).takeUnretainedValue().attach(device)
        },Unmanaged.passUnretained(self).toOpaque())
        IOHIDManagerRegisterDeviceRemovalCallback(m,{context,_,_,device in
            guard let context=context else{return};let owner=Unmanaged<MAKRMedia>.fromOpaque(context).takeUnretainedValue();var id:UInt64=0
            if IORegistryEntryGetRegistryEntryID(IOHIDDeviceGetService(device),&id)==KERN_SUCCESS,let old=owner.channels.removeValue(forKey:id){
                IOHIDDeviceUnscheduleFromRunLoop(device,CFRunLoopGetMain(),CFRunLoopMode.defaultMode.rawValue);IOHIDDeviceRegisterInputReportCallback(device,old.buffer,512,nil,nil);IOHIDDeviceClose(device,IOOptionBits(kIOHIDOptionsTypeNone));owner.retired.append(old)
            }
        },Unmanaged.passUnretained(self).toOpaque())
        IOHIDManagerScheduleWithRunLoop(m,CFRunLoopGetMain(),CFRunLoopMode.defaultMode.rawValue)
        for device in (IOHIDManagerCopyDevices(m) as? Set<IOHIDDevice>) ?? [] { attach(device) }
    }
    private func attach(_ device:IOHIDDevice){
        guard channels.count<8,retired.count<128,let page=IOHIDDeviceGetProperty(device,kIOHIDPrimaryUsagePageKey as CFString) as? NSNumber,page.intValue>=0xff00 else{return}
        var entry=IOHIDDeviceGetService(device);IOObjectRetain(entry);defer{IOObjectRelease(entry)}
        var interface = -1
        for _ in 0..<16 {
            if let n=IORegistryEntryCreateCFProperty(entry,"bInterfaceNumber" as CFString,kCFAllocatorDefault,0)?.takeRetainedValue() as? NSNumber {interface=n.intValue;break}
            var parent:io_registry_entry_t=0;guard IORegistryEntryGetParentEntry(entry,kIOServicePlane,&parent)==KERN_SUCCESS else{break};IOObjectRelease(entry);entry=parent
        }
        guard interface==2 else{return}
        var id:UInt64=0;guard IORegistryEntryGetRegistryEntryID(IOHIDDeviceGetService(device),&id)==KERN_SUCCESS,channels[id]==nil else{return}
        guard IOHIDDeviceOpen(device,IOOptionBits(kIOHIDOptionsTypeNone))==kIOReturnSuccess else{return}
        let channel=Channel(device);channels[id]=channel
        IOHIDDeviceRegisterInputReportCallback(device,channel.buffer,512,{_,result,_,kind,_,bytes,count in
            guard result==kIOReturnSuccess,kind==kIOHIDReportTypeInput,MAKRMedia.shared.enabled,count>=5,count<=512 else{return}
            let direction=MAKRKnob.direction(Array(UnsafeBufferPointer(start:bytes,count:count)))
            if direction != 0 { MAKRMedia.shared.adjustVolume(direction) }
        },nil)
        IOHIDDeviceScheduleWithRunLoop(device,CFRunLoopGetMain(),CFRunLoopMode.defaultMode.rawValue)
    }
    private func adjustVolume(_ direction:Int){
        var device=AudioDeviceID(0);var size=UInt32(MemoryLayout<AudioDeviceID>.size)
        var address=AudioObjectPropertyAddress(mSelector:kAudioHardwarePropertyDefaultOutputDevice,mScope:kAudioObjectPropertyScopeGlobal,mElement:0)
        guard AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject),&address,0,nil,&size,&device)==noErr,device != 0 else{return}
        for element:UInt32 in [0,1,2] {
            var volume=AudioObjectPropertyAddress(mSelector:kAudioDevicePropertyVolumeScalar,mScope:kAudioDevicePropertyScopeOutput,mElement:element);var settable=DarwinBoolean(false)
            guard AudioObjectHasProperty(device,&volume),AudioObjectIsPropertySettable(device,&volume,&settable)==noErr,settable.boolValue else{continue}
            var value:Float32=0;var count=UInt32(MemoryLayout<Float32>.size)
            guard AudioObjectGetPropertyData(device,&volume,0,nil,&count,&value)==noErr,value.isFinite else{continue}
            value=min(1,max(0,value+Float32(direction)/32));_ = AudioObjectSetPropertyData(device,&volume,0,nil,count,&value)
            if element==0{return}
        }
    }
}
