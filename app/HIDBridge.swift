// SPDX-License-Identifier: GPL-2.0-or-later
// IOKit HID transport. Never opens or reads keyboard/mouse input collections.
import Foundation
import IOKit
import IOKit.hid

func property(_ device:IOHIDDevice,_ key:String)->Any? { IOHIDDeviceGetProperty(device,key as CFString) }
func integer(_ device:IOHIDDevice,_ key:String)->Int { (property(device,key) as? NSNumber)?.intValue ?? 0 }
func text(_ device:IOHIDDevice,_ key:String)->String { String(((property(device,key) as? String) ?? "").unicodeScalars.filter { !CharacterSet.controlCharacters.contains($0) }.map(String.init).joined().prefix(160)) }
func entryID(_ entry:io_registry_entry_t)->String { var id:UInt64=0;IORegistryEntryGetRegistryEntryID(entry,&id);return String(id) }
func parentUSB(_ device:IOHIDDevice)->String {
    var current=IOHIDDeviceGetService(device);IOObjectRetain(current);defer { IOObjectRelease(current) }
    for _ in 0..<16 {
        if IOObjectConformsTo(current,"IOUSBHostDevice") != 0 || IOObjectConformsTo(current,"IOUSBDevice") != 0 { return entryID(current) }
        var parent:io_registry_entry_t=0
        guard IORegistryEntryGetParentEntry(current,kIOServicePlane,&parent)==KERN_SUCCESS else { break }
        IOObjectRelease(current);current=parent
    }
    return entryID(IOHIDDeviceGetService(device))
}
func deviceList()->[IOHIDDevice] {
    let manager=IOHIDManagerCreate(kCFAllocatorDefault,IOOptionBits(kIOHIDOptionsTypeNone))
    IOHIDManagerSetDeviceMatching(manager,nil)
    return Array((IOHIDManagerCopyDevices(manager) as? Set<IOHIDDevice>) ?? []).sorted { entryID(IOHIDDeviceGetService($0)) < entryID(IOHIDDeviceGetService($1)) }
}
func interfaceNumber(_ device:IOHIDDevice)->Int {
    var current=IOHIDDeviceGetService(device);IOObjectRetain(current);defer { IOObjectRelease(current) }
    for _ in 0..<16 {
        if let value=IORegistryEntryCreateCFProperty(current,"bInterfaceNumber" as CFString,kCFAllocatorDefault,0)?.takeRetainedValue() as? NSNumber { return value.intValue }
        var parent:io_registry_entry_t=0;guard IORegistryEntryGetParentEntry(current,kIOServicePlane,&parent)==KERN_SUCCESS else { break };IOObjectRelease(current);current=parent
    };return -1
}
func inventory(_ devices:[IOHIDDevice])->[[String:Any]] {
    devices.prefix(256).map { device in
        var row:[String:Any]=["handle":entryID(IOHIDDeviceGetService(device)),"physical_id":parentUSB(device),"vendor_id":integer(device,"VendorID"),"product_id":integer(device,"ProductID"),"name":text(device,"Product"),"vendor":text(device,"Manufacturer"),"usage_page":integer(device,"PrimaryUsagePage"),"usage":integer(device,"PrimaryUsage"),"transport":text(device,"Transport"),"interface":interfaceNumber(device)]
        if integer(device,"PrimaryUsagePage")==0x59 || integer(device,"VendorID")==0x0b05,let descriptor=property(device,"ReportDescriptor") as? Data,descriptor.count<=16384 { row["descriptor"]=descriptor.base64EncodedString() }
        return row
    }
}
func usbInventory()->[[String:Any]] {
    var iterator:io_iterator_t=0
    guard IOServiceGetMatchingServices(kIOMainPortDefault,IOServiceMatching("IOUSBHostDevice"),&iterator)==KERN_SUCCESS else { return [] }
    defer { IOObjectRelease(iterator) };var rows=[[String:Any]]()
    while rows.count<256 {
        let entry=IOIteratorNext(iterator);if entry==0 { break };defer { IOObjectRelease(entry) }
        func p(_ key:String)->Any? { IORegistryEntryCreateCFProperty(entry,key as CFString,kCFAllocatorDefault,0)?.takeRetainedValue() }
        guard let vid=p("idVendor") as? NSNumber,let pid=p("idProduct") as? NSNumber else { continue }
        rows.append(["physical_id":entryID(entry),"vendor_id":vid.intValue,"product_id":pid.intValue,"name":String((p("USB Product Name") as? String ?? "USB device").prefix(160)),"vendor":String((p("USB Vendor Name") as? String ?? "").prefix(160)),"transport":"USB"])
    }
    return rows
}
final class LightingReply {
    let prefix:[UInt8];var bytes:[UInt8]?
    init(_ prefix:[UInt8]) { self.prefix=prefix }
}
func lightingExchange(_ device:IOHIDDevice,_ packet:[UInt8])throws->[UInt8] {
    let state=LightingReply(Array(packet.prefix(3)))
    let buffer=UnsafeMutablePointer<UInt8>.allocate(capacity:512);defer { buffer.deallocate() }
    let loop=CFRunLoopGetCurrent()!
    IOHIDDeviceRegisterInputReportCallback(device,buffer,512,{ context,result,_,_,_,report,length in
        guard result==kIOReturnSuccess,let context=context,length>0,length<=512 else { return }
        let state=Unmanaged<LightingReply>.fromOpaque(context).takeUnretainedValue()
        var bytes=Array(UnsafeBufferPointer(start:report,count:length))
        if state.prefix.first==0 { bytes.insert(0,at:0) }
        if bytes.count>=3 && Array(bytes.prefix(3))==state.prefix { state.bytes=bytes }
    },Unmanaged.passUnretained(state).toOpaque())
    IOHIDDeviceScheduleWithRunLoop(device,loop,CFRunLoopMode.defaultMode.rawValue)
    defer {
        IOHIDDeviceUnscheduleFromRunLoop(device,loop,CFRunLoopMode.defaultMode.rawValue)
        IOHIDDeviceRegisterInputReportCallback(device,buffer,512,nil,nil)
    }
    var bytes=packet;let id=bytes[0];if id==0 { bytes.removeFirst() }
    let result=IOHIDDeviceSetReport(device,kIOHIDReportTypeOutput,CFIndex(id),bytes,bytes.count)
    guard result==kIOReturnSuccess else { try fail("Lighting request failed (\(result))") }
    let deadline=Date().addingTimeInterval(2)
    while state.bytes==nil && Date()<deadline { CFRunLoopRunInMode(CFRunLoopMode.defaultMode,0.01,true) }
    guard let reply=state.bytes else { try fail("Lighting acknowledgement timed out; no automatic retry") }
    return reply
}
struct BridgeError:Error { let message:String }
func fail(_ message:String)throws->Never { throw BridgeError(message:message) }
func execute(_ request:[String:Any],devices:[IOHIDDevice])throws->[String:Any] {
    let command=request["command"] as? String ?? ""
    if command=="inventory" { return ["devices":inventory(devices),"usb":usbInventory()] }
    guard let handle=request["handle"] as? String,let device=devices.first(where:{entryID(IOHIDDeviceGetService($0))==handle}) else { try fail("Device disconnected; rediscover") }
    let page=integer(device,"PrimaryUsagePage"),vid=integer(device,"VendorID"),pid=integer(device,"ProductID")
    let lamp=page==0x59 && integer(device,"PrimaryUsage")==1
    let mouse=vid==0x0b05 && [0x1977,0x1979].contains(pid) && page==0xff01
    let kraken=vid==0x1e71 && [0x170e,0x1715].contains(pid) && page>=0xff00
    let radius=vid==0x36bc && pid==0x1003 && page==0xff00 && integer(device,"PrimaryUsage")==1 && interfaceNumber(device)==0
    let keyboard=vid==0x0b05 && ((pid==0x1ace && page>=0xff00) || (pid==0x1aae && page==0xff00))
    guard lamp || mouse || kraken || radius || keyboard else { try fail("No implemented lighting transport for this collection") }
    guard let id=request["report_id"] as? Int,(0...255).contains(id) else { try fail("Invalid report ID") }
    let opened=IOHIDDeviceOpen(device,IOOptionBits(kIOHIDOptionsTypeNone))
    guard opened==kIOReturnSuccess else { try fail("macOS denied HID lighting access (\(opened)). Close other lighting software and check device permissions.") }
    defer { IOHIDDeviceClose(device,IOOptionBits(kIOHIDOptionsTypeNone)) }
    if command=="access" { return ["available":true] }
    if command=="feature_get" && lamp {
        guard let size=request["size"] as? Int,(2...512).contains(size),id>0 else { try fail("Invalid feature size") }
        var buffer=[UInt8](repeating:0,count:size);buffer[0]=UInt8(id);var length=size
        let result=IOHIDDeviceGetReport(device,kIOHIDReportTypeFeature,CFIndex(id),&buffer,&length)
        guard result==kIOReturnSuccess,length>0,length<=size else { try fail("HID feature read failed (\(result))") }
        return ["data":Data(buffer.prefix(length)).base64EncodedString()]
    }
    guard let encoded=request["data"] as? String,let data=Data(base64Encoded:encoded),!data.isEmpty,data.count<=512 else { try fail("Invalid lighting packet") }
    var bytes=[UInt8](data)
    let feature=command=="feature_set"
    if command=="exchange" {
        let radiusQuery=radius && id==2 && bytes.count==64 && bytes.prefix(4)==[2,0xa4,8,1]
        let radiusLight=radius && id==2 && bytes.count==64 && bytes[1]==0xa4 && [0x0a,0x11,0x12].contains(bytes[2])
        let keyboardQuery=keyboard && ((pid==0x1ace && bytes.count==64 && ((id==2 && bytes.prefix(3)==[2,0x12,0x12]) || (id==1 && bytes.prefix(3)==[1,0xa0,0]))) || (pid==0x1aae && bytes.count==65 && id==0 && bytes.prefix(3)==[0,0x12,0x12]))
        guard radiusQuery || radiusLight || keyboardQuery else { try fail("Exchange outside lighting-only allowlist") }
        return ["data":Data(try lightingExchange(device,bytes)).base64EncodedString()]
    }
    guard (lamp && feature && id>0 && bytes.first==UInt8(id)) || (mouse && command=="output" && id==0 && bytes.count==65 && bytes.prefix(3)==[0,0x51,0x28]) || (kraken && command=="output" && id==2 && bytes.count==64 && bytes.prefix(2)==[2,0x4c]) || (keyboard && command=="output" && ((pid==0x1ace && id==2 && bytes.count==64) || (pid==0x1aae && id==0 && bytes.count==65)) && bytes[1]==0x51 && bytes[2]==0x2c && [0,1,2].contains(bytes[3])) else { try fail("Packet outside lighting-only protocol allowlist") }
    // Match hidapi's macOS framing: report zero is omitted, nonzero IDs stay in the buffer.
    if id==0 { bytes.removeFirst() }
    let result=IOHIDDeviceSetReport(device,feature ? kIOHIDReportTypeFeature : kIOHIDReportTypeOutput,CFIndex(id),bytes,bytes.count)
    guard result==kIOReturnSuccess else { try fail("HID lighting write failed (\(result))") }
    return ["sent":true]
}
if CommandLine.arguments.contains("--inventory") {
    let result:[String:Any]=["devices":inventory(deviceList()),"usb":usbInventory()]
    let data=try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]);print(String(decoding:data,as:UTF8.self))
} else {
    // Session-scoped handles remain bound to the retained IOKit objects, never reused by index.
    let devices=deviceList()
    while let line=readLine() {
        if line.utf8.count>65536 { print("{\"error\":\"Request too large\"}");fflush(stdout);continue }
        do {
            guard let data=line.data(using:.utf8),let request=try JSONSerialization.jsonObject(with:data) as? [String:Any] else { try fail("JSON object required") }
            let response=try execute(request,devices:devices)
            print(String(decoding:try JSONSerialization.data(withJSONObject:response,options:[.sortedKeys]),as:UTF8.self))
        } catch { let message=(error as? BridgeError)?.message ?? "Invalid HID request";print(String(decoding:try! JSONSerialization.data(withJSONObject:["error":message]),as:UTF8.self)) }
        fflush(stdout)
    }
}
