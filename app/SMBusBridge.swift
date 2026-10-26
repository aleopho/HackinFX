// SPDX-License-Identifier: GPL-2.0-or-later
// Intel i801 byte-data / Corsair protocol references: OpenRGB (vendor/openrgb/ram).
// No arbitrary port API, SPD access, firmware or host-configuration writes.
import Foundation
import IOKit
import Darwin
struct RAMError:Error { let text:String }
func reject(_ text:String)throws->Never { throw RAMError(text:text) }
func driverService()->io_service_t { IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("macUSPCIO")) }
func controllers()->[[String:String]] {
    var iterator:io_iterator_t=0;var rows=[[String:String]]()
    guard IOServiceGetMatchingServices(kIOMainPortDefault,IOServiceMatching("IOPCIDevice"),&iterator)==KERN_SUCCESS else { return [] };defer { IOObjectRelease(iterator) }
    while true {
        let entry=IOIteratorNext(iterator);if entry==0 { break };defer { IOObjectRelease(entry) }
        func value(_ key:String)->UInt32? {
            guard let data=IORegistryEntryCreateCFProperty(entry,key as CFString,kCFAllocatorDefault,0)?.takeRetainedValue() as? Data,data.count>=4 else { return nil }
            return data.prefix(4).enumerated().reduce(UInt32(0)) { $0 | UInt32($1.element) << ($1.offset*8) }
        }
        if let code=value("class-code"),code>>8==0x0c05,let vid=value("vendor-id"),let pid=value("device-id") { rows.append(["vendor_id":String(format:"%04x",vid),"device_id":String(format:"%04x",pid)]) }
    };return rows
}
func crc8(_ bytes:[UInt8])->UInt8 { var crc:UInt8=0;for b in bytes { crc ^= b;for _ in 0..<8 { crc = crc&0x80 != 0 ? (crc &<< 1)^7 : crc &<< 1 } };return crc }
final class CorsairBus {
    var connection:io_connect_t=0;var base:UInt16=0;var verified=Set<UInt8>();var failed=false
    deinit { if connection != 0 { IOServiceClose(connection) } }
    func scalar(_ selector:UInt32,_ args:[UInt64])throws->UInt64 {
        var result:UInt64=0;var count:UInt32=1
        let status=IOConnectCallScalarMethod(connection,selector,args,UInt32(args.count),&result,&count)
        guard status==KERN_SUCCESS,count==1 else { try reject("macUSPCIO method failed (\(status)); no retry") };return result
    }
    func open()throws {
        if connection != 0 { guard base>=0x100 else { try reject("SMBus host validation failed; restart Core after correcting the driver") };return }
        guard controllers()==[["vendor_id":"8086","device_id":"7f23"]] else { try reject("Exactly one Intel 8086:7f23 SMBus controller is required") }
        let service=driverService();guard service != 0 else { try reject("macUSPCIO driver is not loaded. RAM RGB requires a separately reviewed OpenCore driver and reboot.") };defer { IOObjectRelease(service) }
        guard IOServiceOpen(service,mach_task_self_,0,&connection)==KERN_SUCCESS else { connection=0;try reject("macOS denied the SMBus user client") }
        guard try scalar(3,[0])==0x8086,try scalar(3,[2])==0x7f23 else { try reject("This transport is restricted to Intel Arrow Lake SMBus 8086:7f23") }
        let config=try scalar(2,[0x40]);guard config&1 != 0,config&2==0 else { try reject("SMBus host disabled or SMI-owned; host settings are left unchanged") }
        let bar=try scalar(3,[0x20]);guard bar&1==1,bar&0xfffe>=0x100,bar&0xfffe != 0xfffe else { try reject("Invalid SMBus I/O BAR") };base=UInt16(bar&0xfffe)
    }
    func readPort(_ offset:UInt16)throws->UInt8 { UInt8(try scalar(0,[UInt64(base+offset)])&255) }
    func writePort(_ offset:UInt16,_ value:UInt8)throws { _=try scalar(1,[UInt64(base+offset),UInt64(value)]) }
    func transaction(_ address:UInt8,_ register:UInt8,_ value:UInt8?=nil)throws->UInt8 {
        guard !failed else { try reject("SMBus session stopped after a transaction failure; restart Core before retrying") }
        guard base>=0x100 else { try reject("SMBus host is not validated") }
        let initial=try readPort(0);guard initial&0x41==0 else { failed=true;try reject("SMBus busy or in use; no transaction started") }
        try writePort(0,0x1e);try writePort(4,(address<<1)|(value==nil ? 1:0));try writePort(3,register)
        if let v=value { try writePort(5,v) }
        try writePort(2,0x48) // START | SMBus byte-data, without interrupts/PEC.
        let deadline=Date().addingTimeInterval(0.1)
        while Date()<deadline {
            let status=try readPort(0)
            if status&1==0 && status&0x1e != 0 {
                try writePort(0,status&0x1e)
                if status&0x1c != 0 { if status&0x18 != 0 { failed=true };try reject("SMBus target NACK / bus error") }
                return try readPort(5)
            };usleep(1000)
        }
        failed=true;try reject("SMBus transaction timed out; no automatic retry or host reset")
    }
    func identify(_ address:UInt8)throws->[String:Any]? {
        guard [UInt8](0x18...0x1f).contains(address) || [UInt8](0x58...0x5f).contains(address) else { try reject("Address outside documented Corsair lighting ranges") }
        guard let a=try? transaction(address,0x43),[0x1a,0x1b,0x1c].contains(a),let b=try? transaction(address,0x44),[1,3,4].contains(b) else { return nil }
        _=try transaction(address,0x61,0);_=try transaction(address,0x21,0)
        var bytes=[UInt8]();for _ in 0..<32 { bytes.append(try transaction(address,0x40)) }
        guard crc8(bytes)==(try transaction(address,0x42)) else { try reject("Corsair device-info CRC mismatch") }
        let vid=UInt16(bytes[0])|UInt16(bytes[1])<<8;let pid=UInt16(bytes[2])|UInt16(bytes[3])<<8
        guard vid==0x1b1c,[0x0800,0x0801,0x0810,0x0811].contains(pid),bytes[28]>0 else { return nil }
        verified.insert(address)
        return ["address":Int(address),"name":"Corsair Dominator Titanium RGB DDR5","led_count":12,"protocol":Int(bytes[28]),"product_id":String(format:"%04x",pid)]
    }
    func probe()throws->[[String:Any]] {
        try open();verified=[];var rows=[[String:Any]]()
        for address in Array(UInt8(0x18)...UInt8(0x1f))+Array(UInt8(0x58)...UInt8(0x5f)) { if let row=try identify(address) { rows.append(row) };if failed { try reject("SMBus probe stopped after timeout") } }
        return rows
    }
    func color(_ address:UInt8,_ rgb:[Int])throws {
        guard verified.contains(address),rgb.count==3,rgb.allSatisfy({(0...255).contains($0)}) else { try reject("RAM controller must pass exact identity and CRC checks first") }
        let data:[UInt8]=[0x10,1,1,0,UInt8(rgb[0]),UInt8(rgb[1]),UInt8(rgb[2]),255,UInt8(rgb[0]),UInt8(rgb[1]),UInt8(rgb[2]),255,0,0,0,0,0,0,0,0]
        do {
            _=try transaction(address,0x0b,0);_=try transaction(address,0x21,0)
            for v in data { _=try transaction(address,0x20,v) }
            guard crc8(data)==(try transaction(address,0x42)) else { try reject("Corsair color CRC mismatch; configuration was not applied") }
            _=try transaction(address,0x82,1) // Apply CRC-validated lighting effect configuration, not SPD/firmware.
            for _ in 0..<20 { if try transaction(address,0x30)&8==0 { return };usleep(10000) }
            try reject("Corsair lighting controller stayed busy")
        } catch { failed=true;throw error }
    }
}
if CommandLine.arguments.contains("--self-test") {
    assert(crc8(Array("123456789".utf8))==0xf4)
    let unverified=CorsairBus();var blocked=false
    do { try unverified.color(0x18,[1,2,3]) } catch { blocked=true }
    assert(blocked && unverified.connection==0)
    print("RAM CRC-8 vector and unverified-write gate passed; no driver or bus opened")
    exit(0)
}
let bus=CorsairBus()
// Serialize other HackinFX RAM helpers; no claim of exclusion against unrelated software.
let lockPath=FileManager.default.temporaryDirectory.appendingPathComponent("hackinfx-corsair-smbus-\(getuid()).lock").path
let fd=Darwin.open(lockPath,O_CREAT|O_RDWR|O_NOFOLLOW,S_IRUSR|S_IWUSR)
let locked=fd>=0 && flock(fd,LOCK_EX|LOCK_NB)==0
defer { if fd>=0 { Darwin.close(fd) } }
while let line=readLine() {
    do {
        guard line.utf8.count<=4096,let request=try JSONSerialization.jsonObject(with:Data(line.utf8)) as? [String:Any] else { try reject("Invalid RAM request") }
        let command=request["command"] as? String ?? "";var result:[String:Any]
        if command=="status" { let service=driverService();let loaded=service != 0;if loaded { IOObjectRelease(service) };result=["controllers":controllers(),"driver_loaded":loaded,"transport":"Intel i801 / macUSPCIO","mode":"preflight-only"] }
        else {
            guard locked else { try reject("Another HackinFX RAM session owns the bus") }
            if command=="probe" { result=["devices":try bus.probe()] }
            else if command=="static",let address=request["address"] as? Int,(0...127).contains(address),let color=request["color"] as? [Int] { try bus.color(UInt8(address),color);result=["sent":true] }
            else { try reject("Only explicit RAM identity probe and Static lighting are implemented") }
        }
        print(String(decoding:try JSONSerialization.data(withJSONObject:result),as:UTF8.self))
    } catch { let message=(error as? RAMError)?.text ?? "RAM transport failed";print(String(decoding:try! JSONSerialization.data(withJSONObject:["error":message]),as:UTF8.self)) };fflush(stdout)
}
