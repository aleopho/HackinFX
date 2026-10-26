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
// Intel HSTS bit 6 is a read-to-acquire semaphore, not HOST_BUSY.
// A status read returning bit 6 clear grants ownership. Release only that lease.
// https://edc.intel.com/content/www/us/en/design/publications/core-ultra-series-3-processors-i-o-registers/host-status-register-address-hsts-offset-0_1/
func withHostLease<T>(timeout:Double=0.05,read:()throws->UInt8,write:(UInt8)throws->Void,operation:(UInt8)throws->T)throws->T {
    let deadline=ProcessInfo.processInfo.systemUptime+timeout
    var initial=try read()
    while initial&0x40 != 0 {
        guard ProcessInfo.processInfo.systemUptime<deadline else { try reject("SMBus semaphore is owned by another client or a previous unclean session; no flags cleared. Restart after installing the corrected helper.") }
        usleep(1000);initial=try read()
    }
    // This read acquired the hardware semaphore. Never clear it on a failed acquisition.
    let value:T
    do { value=try operation(initial) }
    catch { try? write(0x40);throw error }
    try write(0x40);return value
}
func safeHostSnapshot(read:()throws->UInt8,write:(UInt8)throws->Void)throws->UInt8 {
    let status=try read()
    if status&0x40==0 { try write(0x40) } // A diagnostic read must not strand its own lease.
    return status
}
func allowedRAMAddress(_ address:UInt8)->Bool { (0x18...0x1f).contains(address) || (0x58...0x5f).contains(address) }
func allowedRAMWrite(_ register:UInt8,_ value:UInt8,_ identified:Bool,_ verified:Bool)->Bool {
    if identified && [UInt8(0x61),0x21].contains(register) && value==0 { return true }
    // Effect configuration writes disabled after the observed Titanium blackout.
    return false
}
// OpenRGB CorsairDRAMController::SetColorsPerLED word-write fallback.
// Fixed 12-LED packet only; no caller-supplied register or raw word access.
func titaniumDirectWords(_ colors:[UInt8])throws->[(UInt8,UInt16)] {
    guard colors.count==36 else { try reject("Exactly 12 RGB LEDs are required") }
    var packet:[UInt8]=[12]+colors;packet.append(crc8(packet))
    var words=[(UInt8,UInt16)]();var i=0
    while i<packet.count {
        var reg0:UInt8=i==0 ? 0x90:0xa0;var reg1:UInt8=0
        var word0=UInt16(packet[i]);i+=1
        if i<packet.count { word0 |= UInt16(packet[i])<<8;i+=1 }
        if i<packet.count { reg1=0xa0|((packet[i]&0xf0)>>4);reg0 |= packet[i]&0x0f;i+=1 }
        var word1:UInt16=0
        if i<packet.count { word1=UInt16(packet[i]);i+=1 }
        if i<packet.count { word1 |= UInt16(packet[i])<<8;i+=1 }
        words.append((reg0,word0));if reg1 != 0 { words.append((reg1,word1)) }
    }
    return words
}
// Standard SMBus Block Write, byte-by-byte handshaking (Intel i801).
// Reference: Linux i2c-i801.c i801_block_transaction_byte_by_byte (GPL-2.0-or-later).
// Caller owns HSTS semaphore. No AUXCTL / PCI configuration changes or KILL/reset.
func titaniumBlockWrite(_ address:UInt8,_ register:UInt8,_ data:[UInt8],read:(UInt16)throws->UInt8,write:(UInt16,UInt8)throws->Void)throws {
    guard allowedRAMAddress(address) else { try reject("Direct block target outside RGB-only address range") }
    guard (register==0x31 && data.count==32) || (register==0x32 && data.count==6) else { try reject("Only fixed Titanium direct LED blocks are allowed") }
    guard try read(0x0d)&3==0 else { try reject("SMBus auxiliary mode is not byte-handshake/no-PEC; left unchanged") }
    let initial=try read(0)
    guard initial&1==0 else { try reject("SMBus hardware busy before direct LED block; no reset") }
    let stale=initial&0x9e
    if stale != 0 { try write(0,stale);guard try read(0)&0x9e==0 else { try reject("SMBus block status did not clear") } }
    var completedBytes=0
    func waitFor(_ flag:UInt8)throws->UInt8 {
        let deadline=ProcessInfo.processInfo.systemUptime+0.1
        repeat {
            let status=try read(0)
            if status&0x1c != 0 {
                try write(0,status&0x9e)
                try reject(String(format:"Direct LED address 0x%02x block 0x%02x failed after %d bytes with host status 0x%02x; no retry/reset",address,register,completedBytes,status))
            }
            if status&flag != 0 { return status }
            usleep(100)
        } while ProcessInfo.processInfo.systemUptime<deadline
        try reject(String(format:"Direct LED address 0x%02x block 0x%02x timed out after %d bytes waiting for 0x%02x; no retry/reset",address,register,completedBytes,flag))
    }
    try write(4,address<<1);try write(3,register);try write(5,UInt8(data.count));try write(7,data[0])
    try write(2,0x54) // SMBus BLOCK_DATA (0x14) + START. No interrupts/PEC/KILL.
    for i in data.indices {
        _=try waitFor(0x80)
        if i+1<data.count { try write(7,data[i+1]) }
        completedBytes=i+1
        try write(0,0x80) // BYTE_DONE: release the next byte only after data is ready.
    }
    let final=try waitFor(0x02)
    guard final&1==0 else { try reject("Direct LED block signalled completion while hardware busy") }
    try write(0,0x02)
}
func titaniumDirectPacket(_ colors:[UInt8])throws->[UInt8] {
    guard colors.count==36 else { try reject("Exactly 12 RGB LEDs are required") }
    var packet:[UInt8]=[12]+colors;packet.append(crc8(packet));return packet
}
func titaniumFramePacket(_ colors:[[Int]])throws->[UInt8] {
    guard colors.count==12,colors.allSatisfy({$0.count==3 && $0.allSatisfy({(0...255).contains($0)})}) else { try reject("Exactly 12 bounded RGB colors are required") }
    return try titaniumDirectPacket(colors.reversed().flatMap {$0.map {UInt8($0)}})
}
final class CorsairBus {
    var connection:io_connect_t=0;var base:UInt16=0;var verified=Set<UInt8>();var identified=Set<UInt8>();var failed=false;var directVerified=Set<UInt8>();var lastFrame=[UInt8:Double]()
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
    func diagnostics()throws->[String:Any] {
        try open()
        return ["host":"8086:7f23","host_config":Int(try scalar(2,[0x40])),"pci_command":Int(try scalar(3,[4])),"bar_low":Int(try scalar(3,[0x20])),"status":Int(try safeHostSnapshot(read:{ try self.readPort(0) },write:{ try self.writePort(0,$0) })),"control":Int(try readPort(2)),"address_register":Int(try readPort(4)),"session_failed":failed,"aux_control":Int(try readPort(0x0d)),"helper_revision":"titanium-block-v3-paced","mode":"host-registers-with-semaphore-release"]
    }
    func readPort(_ offset:UInt16)throws->UInt8 { UInt8(try scalar(0,[UInt64(base+offset)])&255) }
    func writePort(_ offset:UInt16,_ value:UInt8)throws { _=try scalar(1,[UInt64(base+offset),UInt64(value)]) }
    func transaction(_ address:UInt8,_ register:UInt8,_ value:UInt8?=nil)throws->UInt8 {
        try transfer(address,register,value.map { UInt16($0) },word:false)
    }
    private func transfer(_ address:UInt8,_ register:UInt8,_ value:UInt16?,word:Bool)throws->UInt8 {
        guard !failed else { try reject("SMBus session stopped after a transaction failure; restart Core before retrying") }
        guard base>=0x100,allowedRAMAddress(address) else { try reject("Only documented Corsair RGB addresses are allowed; SPD addresses are excluded") }
        if word { guard directVerified.contains(address),value != nil,(0x90...0x9f).contains(register) || (0xa0...0xaf).contains(register) else { try reject("Direct LED word write outside verified protocol-4 controller") } }
        else if let v=value { guard v<=255,allowedRAMWrite(register,UInt8(v),identified.contains(address),verified.contains(address)) else { try reject("Register/value outside the identified RGB-only write allowlist") } }
        else { guard [UInt8(0x43),0x44,0x40,0x42,0x30].contains(register) else { try reject("Register outside RGB identity/status allowlist") } }
        var targetNACK=false
        do {
            return try withHostLease(read:{ try self.readPort(0) },write:{ try self.writePort(0,$0) }) { initial in
                guard initial&1==0 else { try reject("SMBus hardware is busy; no transaction started") }
                let stale=initial&0x9e
                if stale != 0 { try writePort(0,stale);guard try readPort(0)&0x9e==0 else { try reject("SMBus status did not clear; no transaction started") } }
                try writePort(4,(address<<1)|(value==nil ? 1:0));try writePort(3,register)
                if let v=value { try writePort(5,UInt8(v&255));if word { try writePort(6,UInt8(v>>8)) } }
                try writePort(2,word ? 0x4c:0x48)
                let deadline=ProcessInfo.processInfo.systemUptime+0.1
                while ProcessInfo.processInfo.systemUptime<deadline {
                    let status=try readPort(0)
                    if status&1==0 && status&0x1e != 0 {
                        try writePort(0,status&0x1e)
                        if status&0x1c != 0 {
                            targetNACK=status&0x1c==0x04
                            if !targetNACK { failed=true }
                            try reject(String(format:"SMBus RGB address 0x%02x register 0x%02x returned status 0x%02x (NACK/bus error); no reset",address,register,status))
                        }
                        return try readPort(5)
                    };usleep(1000)
                }
                failed=true;let status=try readPort(0);let control=try readPort(2)
                try reject(String(format:"SMBus timeout at RGB address 0x%02x register 0x%02x (status 0x%02x, control 0x%02x); no retry/reset",address,register,status,control))
            }
        } catch { if !targetNACK { failed=true };throw error }
    }
    func identify(_ address:UInt8)throws->[String:Any]? {
        guard [UInt8](0x18...0x1f).contains(address) || [UInt8](0x58...0x5f).contains(address) else { try reject("Address outside documented Corsair lighting ranges") }
        let a:UInt8;let b:UInt8
        do { a=try transaction(address,0x43);guard [0x1a,0x1b,0x1c].contains(a) else { return nil };b=try transaction(address,0x44) }
        catch { if failed { throw error };return nil }
        guard [1,3,4].contains(b) else { return nil }
        identified.insert(address)
        _=try transaction(address,0x61,0);_=try transaction(address,0x21,0)
        var bytes=[UInt8]();for _ in 0..<32 { bytes.append(try transaction(address,0x40)) }
        guard crc8(bytes)==(try transaction(address,0x42)) else { try reject("Corsair device-info CRC mismatch") }
        let vid=UInt16(bytes[0])|UInt16(bytes[1])<<8;let pid=UInt16(bytes[2])|UInt16(bytes[3])<<8
        guard vid==0x1b1c,[0x0800,0x0801,0x0810,0x0811].contains(pid),bytes[28]>0 else { return nil }
        verified.insert(address)
        if pid==0x0801 && bytes[28]==4 { directVerified.insert(address) }
        return ["address":Int(address),"name":"Corsair Dominator Titanium RGB DDR5","led_count":12,"protocol":Int(bytes[28]),"product_id":String(format:"%04x",pid)]
    }
    func probe()throws->[[String:Any]] {
        try open();verified=[];identified=[];directVerified=[];var rows=[[String:Any]]()
        for address in Array(UInt8(0x58)...UInt8(0x5f))+Array(UInt8(0x18)...UInt8(0x1f)) { if let row=try identify(address) { rows.append(row) };if failed { try reject("SMBus RGB identity probe stopped after a host/bus error; no lighting commands sent") } }
        return rows
    }
    func color(_ address:UInt8,_ rgb:[Int])throws {
        guard verified.contains(address),rgb.count==3,rgb.allSatisfy({(0...255).contains($0)}) else { try reject("RAM controller must pass exact identity and CRC checks first") }
        try frame(address,Array(repeating:rgb,count:12))
    }
    func frame(_ address:UInt8,_ colors:[[Int]])throws {
        guard !failed else { try reject("RAM session stopped after a bus error; no additional frames or retries") }
        guard directVerified.contains(address),colors.count==12,colors.allSatisfy({ $0.count==3 && $0.allSatisfy({ (0...255).contains($0) }) }) else { try reject("Frame requires verified Titanium 0801 / protocol 4 and exactly 12 RGB LEDs") }
        // OpenRGB marks Titanium's physical LED order as reversed.
        let packet=try titaniumFramePacket(colors)
        // Conservative diagnostic cap: at least 50ms since this DIMM's last complete frame.
        // No transaction retries; this is pacing before a fresh frame, not error recovery.
        if let last=lastFrame[address] {
            let remaining=0.05-(ProcessInfo.processInfo.systemUptime-last)
            if remaining>0 { usleep(useconds_t(remaining*1_000_000)) }
        }
        do {
            // OpenRGB's preferred direct transport: 32 bytes at 0x31 + 6 at 0x32.
            // Word fallback has not produced a correct visible color on this system.
            for (register,data) in [(UInt8(0x31),Array(packet.prefix(32))),(UInt8(0x32),Array(packet.suffix(6)))] {
                try withHostLease(read:{ try self.readPort(0) },write:{ try self.writePort(0,$0) }) { _ in
                    guard try scalar(2,[0x40])&4==0 else { try reject("Host is in I2C mode; configuration left unchanged") }
                    try titaniumBlockWrite(address,register,data,read:{ try self.readPort($0) },write:{ try self.writePort($0,$1) })
                }
                if register==0x31 { usleep(2000) } // Give RGB controller a short inter-block interval.
            }
            lastFrame[address]=ProcessInfo.processInfo.systemUptime
        } catch { failed=true;throw error }


    }
}
if CommandLine.arguments.contains("--self-test") {
    assert(crc8(Array("123456789".utf8))==0xf4)
    // Independently decode the nibble-packed words back to the full LED packet.
    let rgb=(0..<36).map { UInt8($0*7) }
    let words=try! titaniumDirectWords(rgb);var decoded=[UInt8]()
    for i in stride(from:0,to:words.count,by:2) {
        let (r0,w0)=words[i];let (r1,w1)=words[i+1]
        assert((i==0 ? r0&0xf0==0x90:r0&0xf0==0xa0) && r1&0xf0==0xa0)
        decoded += [UInt8(w0&255),UInt8(w0>>8),(r0&15)|((r1&15)<<4),UInt8(w1&255),UInt8(w1>>8)]
    }
    let expected:[UInt8]=[12]+rgb
    assert(Array(decoded.prefix(38))==expected+[crc8(expected)])
    assert(decoded.dropFirst(38).allSatisfy { $0==0 })
    var invalid=false;do { _=try titaniumDirectWords([0]) } catch { invalid=true };assert(invalid)

    // Exercise the complete port handshake with a deterministic fake host.
    for count in [32,6] {
        let payload=(0..<count).map { UInt8($0) };var transmitted=[UInt8]();var done=0;var started=false
        var controls=[UInt8]();var counts=[UInt8]()
        try! titaniumBlockWrite(0x18,count==32 ? 0x31:0x32,payload,read:{ offset in
            if offset==0x0d { return 0 }
            if offset==0 { return !started ? 0x40:(done<count ? 0xc1:0x42) }
            fatalError("Unexpected host read")
        },write:{ offset,value in
            assert([UInt16(0),2,3,4,5,7].contains(offset))
            if offset==7 { transmitted.append(value) }
            if offset==5 { counts.append(value) }
            if offset==2 { controls.append(value);started=true }
            if offset==0 && value==0x80 { assert(transmitted.count==min(done+2,count));done+=1 }
        })
        assert(transmitted==payload && done==count && controls==[0x54] && counts==[UInt8(count)])
    }
    var blockWrites=0;var blockBlocked=false
    do { try titaniumBlockWrite(0x18,0x31,[1],read:{_ in 0},write:{_,_ in blockWrites+=1}) } catch { blockBlocked=true }
    assert(blockBlocked && blockWrites==0)
    blockBlocked=false
    do { try titaniumBlockWrite(0x18,0x31,Array(repeating:0,count:32),read:{$0==0x0d ? 2:0},write:{_,_ in blockWrites+=1}) } catch { blockBlocked=true }
    assert(blockBlocked && blockWrites==0)
    for host in [UInt8(0x41)] {
        blockBlocked=false
        do { try titaniumBlockWrite(0x18,0x31,Array(repeating:0,count:32),read:{$0==0x0d ? 0:host},write:{_,_ in blockWrites+=1}) } catch { blockBlocked=true }
        assert(blockBlocked && blockWrites==0)
    }
    blockBlocked=false
    do { try titaniumBlockWrite(0x50,0x31,Array(repeating:0,count:32),read:{_ in fatalError("SPD test must not read host")},write:{_,_ in blockWrites+=1}) } catch { blockBlocked=true }
    assert(blockBlocked && blockWrites==0)
    var phase=0;var errorClears=[UInt8]();blockBlocked=false
    do { try titaniumBlockWrite(0x18,0x32,Array(repeating:0,count:6),read:{offset in offset==0x0d ? 0:(phase==0 ? 0x40:0x44)},write:{offset,value in
        if offset==2 { phase=1 };if offset==0 { errorClears.append(value) }
    }) } catch { blockBlocked=true }
    assert(blockBlocked && errorClears==[4])
    let mint=try! titaniumDirectPacket(Array(repeating:[UInt8(32),64,48],count:12).flatMap {$0})
    assert(mint.count==38 && mint.first==12 && mint.last==crc8(Array(mint.dropLast())))
    let distinct=(0..<12).map {[$0,$0+12,$0+24]}
    let distinctPacket=try! titaniumFramePacket(distinct)
    assert(Array(distinctPacket[1...3])==[11,23,35] && Array(distinctPacket[34...36])==[0,12,24])
    assert(distinctPacket[37]==crc8(Array(distinctPacket.prefix(37))))
    let unverified=CorsairBus();var blocked=false
    do { try unverified.color(0x18,[1,2,3]) } catch { blocked=true }
    assert(blocked && unverified.connection==0)
    blocked=false;do { try unverified.frame(0x18,Array(repeating:[1,2,3],count:12)) } catch { blocked=true };assert(blocked && unverified.connection==0)
    unverified.directVerified.insert(0x18)
    for invalid in [Array(repeating:[1,2,3],count:11),Array(repeating:[256,0,0],count:12),Array(repeating:[1,2],count:12)] {
        blocked=false;do { try unverified.frame(0x18,invalid) } catch { blocked=true };assert(blocked && unverified.connection==0)
    }
    unverified.failed=true;blocked=false
    do { try unverified.frame(0x18,Array(repeating:[1,2,3],count:12)) } catch { blocked=true }
    assert(blocked && unverified.connection==0)
    var writes=[UInt8]()
    let value=try! withHostLease(timeout:0,read:{0},write:{writes.append($0)},operation:{_ in 123})
    assert(value==123 && writes==[0x40]);writes=[]
    do { let _:Int=try withHostLease(timeout:0,read:{0x40},write:{writes.append($0)},operation:{_ in 1});assert(false) } catch { assert(writes.isEmpty) }
    do { let _:Int=try withHostLease(timeout:0,read:{0},write:{writes.append($0)},operation:{_ in throw RAMError(text:"fixture")});assert(false) } catch { assert(writes==[0x40]) };writes=[]
    assert((try! safeHostSnapshot(read:{0},write:{writes.append($0)}))==0 && writes==[0x40]);writes=[]
    assert((try! safeHostSnapshot(read:{0x40},write:{writes.append($0)}))==0x40 && writes.isEmpty)
    for a in UInt8(0x50)...UInt8(0x57) { assert(!allowedRAMAddress(a)) }
    assert(!allowedRAMWrite(0x23,0,true,true)) // No bootloader/firmware switch.
    assert(!allowedRAMWrite(0x20,255,false,false))
    assert(!allowedRAMWrite(0x20,255,true,true))
    assert(!allowedRAMWrite(0x82,1,true,true))
    print("Direct block byte-handshake/error bounds, 12-LED packet round-trip/CRC, semaphore ownership/release, SPD exclusion, disabled effect configuration and unverified-write gate passed; no driver or bus opened")
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
        else if command=="diagnostics" { result=try bus.diagnostics() }
        else {
            guard locked else { try reject("Another HackinFX RAM session owns the bus") }
            if command=="probe" { result=["devices":try bus.probe()] }
            else if command=="static",let address=request["address"] as? Int,(0...127).contains(address),let color=request["color"] as? [Int] { try bus.color(UInt8(address),color);result=["sent":true,"transport":"protocol-4-direct-block","led_count":12,"optically_confirmed":false] }
            else if command=="frame",let address=request["address"] as? Int,(0...127).contains(address),let colors=request["colors"] as? [[Int]] { try bus.frame(UInt8(address),colors);result=["sent":true,"transport":"protocol-4-direct-block","led_count":12,"optically_confirmed":false] }
            else { try reject("Only explicit RAM identity probe and bounded 12-LED lighting frames are implemented") }
        }
        print(String(decoding:try JSONSerialization.data(withJSONObject:result),as:UTF8.self))
    } catch { let message=(error as? RAMError)?.text ?? "RAM transport failed";print(String(decoding:try! JSONSerialization.data(withJSONObject:["error":message]),as:UTF8.self)) };fflush(stdout)
}
