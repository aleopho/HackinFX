// SPDX-License-Identifier: GPL-2.0-or-later
import AppKit
import SwiftUI

struct CenterZone: Codable { let name:String;let led_count:Int }
struct CenterMode: Codable { let name:String;let flags:Int }
struct CenterDevice: Codable, Identifiable {
    let id: String
    let fingerprint: String
    let name: String
    let vendor: String
    let category: String
    let backend: String
    let led_count: Int
    let direct: Bool
    let controllable: Bool
    let status: String
    let detail: String
    var zones:[CenterZone]? = nil
    var modes:[CenterMode]? = nil
    var symbol: String {
        switch category {
        case "gpu":return "pciecard"
        case "dram":return "memorychip"
        case "keyboard","keypad":return "keyboard"
        case "mouse":return "computermouse"
        case "cooler":return "fanblades"
        case "strip","light":return "light.strip.2"
        case "mainboard":return "cpu"
        default:return "cable.connector"
        }
    }
    var categoryLabel: String { ["dram":"Memory","gpu":"GPU","cooler":"Cooling","strip":"Lighting","keyboard":"Keyboard","mouse":"Mouse","usb":"USB" ][category] ?? category.capitalized }
}
struct CenterScene: Codable {
    var mode = "static"
    var palette = ["c6ed91","42d6ce","9f8bff"]
    var brightness = 70.0
    var speed = 35.0
    var axis = "x"
}
struct SavedCenterScene: Codable, Identifiable { var id:String { name }; let name: String; let config:CenterScene }
struct CenterPosition: Codable { var x:Double;var y:Double;var width:Double }
struct CenterState: Codable {
    let schema:Int
    let devices:[CenterDevice]
    let layout:[String:CenterPosition]
    let scene:CenterScene
    let running:Bool
    let frames:Int
    let errors:[String]
    let bridge:String
    let scenes:[SavedCenterScene]
    let message:String
    static let empty = CenterState(schema:1,devices:[],layout:[:],scene:CenterScene(),running:false,frames:0,errors:[],bridge:"disconnected",scenes:[],message:"Start Core to discover your setup")
}
private struct CoreDiscovery: Codable { let schema:Int;let port:Int;let credential:String;let pid:Int }

final class CenterModel: ObservableObject {
    @Published var state = CenterState.empty
    @Published var selected = Set<String>()
    @Published var scene = CenterScene()
    @Published var filter = "all"
    @Published var busy = false
    @Published var online = false
    @Published var error = ""
    @Published var sceneName = "My scene"
    @Published var activeDevice: CenterDevice?
    private var process:Process?
    private var discovery:CoreDiscovery?
    private var timer:Timer?
    private var polling = false
    private var shuttingDown = false
    private var logHandle:FileHandle?
    private var sessionFile:URL?
    private let session=URLSession(configuration:.ephemeral)
    var controllable:[CenterDevice] { state.devices.filter { $0.controllable } }
    var visible:[CenterDevice] { state.devices.filter { filter == "all" || $0.category == filter } }
    var chosen:[CenterDevice] { state.devices.filter { selected.contains($0.id) } }
    var canAnimate:Bool { !chosen.isEmpty && chosen.allSatisfy { $0.direct } }
    var sceneCompatible:Bool { !chosen.isEmpty && chosen.allSatisfy { $0.controllable } && (canAnimate || scene.mode == "static" || (scene.mode == "gradient" && chosen.allSatisfy { $0.direct || ($0.backend == "native" && $0.led_count == 3) })) }
    func start() {
        guard process == nil && !shuttingDown else { return }
        busy=true;error=""
        let folder=FileManager.default.urls(for:.applicationSupportDirectory,in:.userDomainMask)[0].appendingPathComponent("HackinFX/Core",isDirectory:true)
        let documents=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("HackinFX",isDirectory:true)
        let discoveryURL=folder.appendingPathComponent("session-\(UUID().uuidString).json")
        do {
            try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true,attributes:[.posixPermissions:0o700])
            try? logHandle?.close()
            let log=folder.appendingPathComponent("core-\(UUID().uuidString).log")
            FileManager.default.createFile(atPath:log.path,contents:Data(),attributes:[.posixPermissions:0o600])
            let handle=try FileHandle(forWritingTo:log);logHandle=handle
            let task=Process();task.executableURL=URL(fileURLWithPath:"/usr/bin/python3")
            task.arguments=["-B",Bundle.main.resourceURL!.appendingPathComponent("center_service.py").path,"--directory",folder.path,"--discovery",discoveryURL.path,"--profiles",documents.path,"--scenes",documents.appendingPathComponent("scenes.json").path,"--owner-pid",String(ProcessInfo.processInfo.processIdentifier)]
            task.standardOutput=handle;task.standardError=handle
            task.terminationHandler={ [weak self] _ in DispatchQueue.main.async { guard let self=self,!self.shuttingDown else { return };self.online=false;self.busy=false;self.state = .empty;self.selected=[];self.timer?.invalidate();self.error="Core stopped. Quit other HackinFX copies, then restart Core.";self.process=nil } }
            try task.run();process=task;sessionFile=discoveryURL
            awaitDiscovery(discoveryURL,attempt:0)
        } catch { process=nil;busy=false;self.error="Could not start Core: \(error.localizedDescription)" }
    }
    private func awaitDiscovery(_ url:URL,attempt:Int) {
        guard !shuttingDown else { return }
        if let data=try? Data(contentsOf:url),let info=try? JSONDecoder().decode(CoreDiscovery.self,from:data),info.schema == 1,(1...65535).contains(info.port),info.credential.count >= 32,info.pid == Int(process?.processIdentifier ?? -1) {
            discovery=info;online=true;busy=false
            timer=Timer.scheduledTimer(withTimeInterval:2,repeats:true) { [weak self] _ in self?.poll() }
            discover();return
        }
        guard attempt<60,process?.isRunning == true else { busy=false;error="Core did not become available. Check its local log or close another HackinFX instance.";return }
        DispatchQueue.main.asyncAfter(deadline:.now()+0.1) { self.awaitDiscovery(url,attempt:attempt+1) }
    }
    private func request(_ path:String,method:String="POST",body:[String:Any]=[:],completion:@escaping(Result<CenterState,Error>)->Void) {
        guard let info=discovery else { return }
        var request=URLRequest(url:URL(string:"http://127.0.0.1:\(info.port)\(path)")!);request.httpMethod=method;request.timeoutInterval=90
        request.setValue("Bearer "+info.credential,forHTTPHeaderField:"Authorization")
        if method == "POST" { request.setValue("application/json",forHTTPHeaderField:"Content-Type");request.httpBody=try? JSONSerialization.data(withJSONObject:body) }
        session.dataTask(with:request) { data,response,error in
            let result:Result<CenterState,Error>
            if let error=error { result = .failure(error) }
            else if let data=data,(response as? HTTPURLResponse)?.statusCode == 200,let state=try? JSONDecoder().decode(CenterState.self,from:data),state.schema == 1 { result = .success(state) }
            else {
                let object=data.flatMap { try? JSONSerialization.jsonObject(with:$0) as? [String:Any] }
                result = .failure(NSError(domain:"HackinFXCore",code:1,userInfo:[NSLocalizedDescriptionKey:object?["error"] as? String ?? "Core returned an unreadable response"]))
            }
            DispatchQueue.main.async { completion(result) }
        }.resume()
    }
    private func accept(_ result:Result<CenterState,Error>) {
        switch result {
        case .success(let state):self.state=state;let known=Set(state.devices.filter { $0.controllable }.map { $0.id });selected.formIntersection(known);error=""
        case .failure(let error):self.error=error.localizedDescription
        }
    }
    func poll() {
        guard online && !busy && !polling else { return };polling=true
        request("/v1/status",method:"GET") { result in self.polling=false;self.accept(result) }
    }
    func discover() {
        guard online && !busy else { return };busy=true
        request("/v1/discover") { result in self.busy=false;self.accept(result) }
    }
    func toggle(_ device:CenterDevice) { guard device.controllable else { activeDevice=device;return };if selected.contains(device.id) { selected.remove(device.id) } else { selected.insert(device.id) } }
    func apply() {
        guard online && !busy && sceneCompatible else { return };busy=true
        let encoded=(try? JSONSerialization.jsonObject(with:JSONEncoder().encode(scene))) as? [String:Any] ?? [:]
        request("/v1/scene/start",body:["config":encoded,"devices":Array(selected).sorted()]) { result in self.busy=false;self.accept(result) }
    }
    func stop() { guard online && !busy else { return };busy=true;request("/v1/scene/stop") { result in self.busy=false;self.accept(result) } }
    func blackout() { scene.mode="static";scene.brightness=0;apply() }
    func saveScene() {
        guard online && !busy else { return };busy=true
        let encoded=(try? JSONSerialization.jsonObject(with:JSONEncoder().encode(scene))) as? [String:Any] ?? [:]
        request("/v1/scenes/save",body:["name":sceneName,"config":encoded]) { result in self.busy=false;self.accept(result) }
    }
    func move(_ id:String,x:Double,y:Double,width:Double?=nil) {
        guard online && !busy else { return };busy=true
        let w=width ?? state.layout[id]?.width ?? 0.22
        request("/v1/layout",body:[id:["x":min(1,max(0,x)),"y":min(1,max(0,y)),"width":w]]) { result in self.busy=false;self.accept(result) }
    }
    func shutdown() {
        shuttingDown=true;timer?.invalidate();timer=nil
        if process?.isRunning == true { process?.terminate() }
        process=nil;discovery=nil;try? logHandle?.close();logHandle=nil
    }
}

private enum CenterTheme {
    static let background=Color(red:0.035,green:0.047,blue:0.055)
    static let surface=Color(red:0.065,green:0.082,blue:0.09)
    static let elevated=Color(red:0.085,green:0.105,blue:0.11)
    static let accent=Color(red:0.77,green:0.94,blue:0.49)
    static let aqua=Color(red:0.31,green:0.82,blue:0.79)
    static let muted=Color(red:0.51,green:0.58,blue:0.59)
}
private struct CenterPanel<Content:View>:View {
    let content:Content
    init(@ViewBuilder content:()->Content) { self.content=content() }
    var body:some View { content.padding(22).frame(maxWidth:.infinity,alignment:.leading).background(CenterTheme.surface).clipShape(RoundedRectangle(cornerRadius:20)).overlay(RoundedRectangle(cornerRadius:20).stroke(.white.opacity(0.06),lineWidth:1)) }
}
private struct CenterBadge:View {
    let text:String
    var good=false
    var body:some View { HStack(spacing:5) { Circle().fill(good ? CenterTheme.accent : CenterTheme.muted).frame(width:4,height:4);Text(text.uppercased()).font(.system(size:8,weight:.semibold,design:.monospaced)).tracking(0.8) }.foregroundStyle(good ? CenterTheme.accent : CenterTheme.muted).padding(.horizontal,9).padding(.vertical,6).background((good ? CenterTheme.accent : .white).opacity(0.055)).clipShape(Capsule()) }
}
private struct CenterHeading:View {
    let eyebrow:String
    let title:String
    let subtitle:String
    var body:some View { VStack(alignment:.leading,spacing:9) { Text(eyebrow.uppercased()).font(.system(size:9,weight:.semibold,design:.monospaced)).tracking(2.6).foregroundStyle(CenterTheme.accent);Text(title).font(.system(size:32,weight:.semibold,design:.rounded));Text(subtitle).font(.system(size:12)).foregroundStyle(CenterTheme.muted).fixedSize(horizontal:false,vertical:true) } }
}
private struct CenterAction:View {
    let title:String
    let symbol:String
    let action:()->Void
    var body:some View { Button(action:action) { HStack { Text(title);Image(systemName:symbol) }.font(.system(size:12,weight:.semibold)).foregroundStyle(CenterTheme.background).padding(.horizontal,17).frame(height:38).background(CenterTheme.accent).clipShape(RoundedRectangle(cornerRadius:10)) }.buttonStyle(PressFeedbackStyle()) }
}

struct CenterNavigation:View {
    @ObservedObject var model:Model
    @ObservedObject var center:CenterModel
    @Environment(\.accessibilityReduceMotion) var reduceMotion
    @Namespace private var selection
    private let pages=[("Overview","square.grid.2x2"),("Devices","externaldrive.connected.to.line.below"),("Scenes","slider.horizontal.3"),("Layout","rectangle.3.group"),("Connections","point.3.connected.trianglepath.dotted"),("Studio","pciecard"),("Hardware","waveform.path.ecg"),("Credits","heart")]
    var body:some View {
        VStack(alignment:.leading,spacing:0) {
            HStack(spacing:11) { Image(nsImage:NSImage(contentsOf:Bundle.main.url(forResource:"hackinfx-logo",withExtension:"png")!) ?? NSImage()).resizable().scaledToFit().frame(width:36,height:36);VStack(alignment:.leading,spacing:3) { Text("HackinFX").font(.system(size:21,weight:.semibold,design:.rounded));Text("CONTROL CENTER").font(.system(size:7,weight:.semibold,design:.monospaced)).tracking(2).foregroundStyle(CenterTheme.muted) } }.padding(.bottom,35)
            Text("WORKSPACE").font(.system(size:8,weight:.medium,design:.monospaced)).tracking(2).foregroundStyle(CenterTheme.muted).padding(.horizontal,12).padding(.bottom,12)
            ForEach(pages,id:\.0) { page,symbol in
                Button { model.page=page } label: {
                    HStack(spacing:12) { Image(systemName:symbol).font(.system(size:14)).frame(width:18);Text(page == "Studio" ? "GPU Lab" : page == "Hardware" ? "Diagnostics" : page).font(.system(size:12,weight:.medium));Spacer();if page == "Devices" { Text("\(center.state.devices.count)").font(.system(size:10,design:.monospaced)) } }.foregroundStyle(model.page == page ? CenterTheme.accent : CenterTheme.muted).padding(.horizontal,13).frame(height:43).background { if model.page == page { RoundedRectangle(cornerRadius:10).fill(CenterTheme.accent.opacity(0.08)).matchedGeometryEffect(id:"center-nav",in:selection) } }
                }.buttonStyle(PressFeedbackStyle()).padding(.bottom,5)
            }
            Spacer(minLength:20)
            VStack(alignment:.leading,spacing:12) {
                HStack { Image(systemName:"circle.hexagongrid").foregroundStyle(CenterTheme.accent);Text("HACKINFX CORE").font(.system(size:8,weight:.semibold,design:.monospaced)).tracking(1) }
                Text(center.online ? "Local engine online" : "Core offline").font(.system(size:12,weight:.medium))
                HStack(spacing:6) { Circle().fill(center.online ? CenterTheme.accent : .orange).frame(width:5,height:5);Text("LOCAL ONLY · x86-64").font(.system(size:7,design:.monospaced)).foregroundStyle(CenterTheme.muted) }
            }.padding(15).frame(maxWidth:.infinity,alignment:.leading).background(CenterTheme.elevated.opacity(0.6)).clipShape(RoundedRectangle(cornerRadius:14))
            HStack { Text("2.0.0");Spacer();Text("BY ALEOPHO") }.font(.system(size:7,weight:.medium,design:.monospaced)).tracking(1).foregroundStyle(CenterTheme.muted).padding(.top,19)
        }.padding(22).frame(width:232).frame(maxHeight:.infinity).background(CenterTheme.background).animation(reduceMotion ? nil : .easeInOut(duration:0.22),value:model.page)
    }
}

private struct CenterDeviceCard:View {
    @ObservedObject var center:CenterModel
    let device:CenterDevice
    var body:some View {
        Button { center.toggle(device) } label: {
            VStack(alignment:.leading,spacing:17) {
                HStack { ZStack { RoundedRectangle(cornerRadius:13).fill(CenterTheme.aqua.opacity(0.07)).frame(width:46,height:46);Image(systemName:device.symbol).font(.system(size:23,weight:.light)).foregroundStyle(device.controllable ? CenterTheme.accent : CenterTheme.muted) };Spacer();Image(systemName:center.selected.contains(device.id) ? "checkmark.circle.fill" : "circle").foregroundStyle(center.selected.contains(device.id) ? CenterTheme.accent : CenterTheme.muted.opacity(0.4)) }
                VStack(alignment:.leading,spacing:5) { Text(device.name).font(.system(size:13,weight:.semibold)).lineLimit(2).frame(height:34,alignment:.topLeading);Text(device.vendor.isEmpty ? device.categoryLabel : device.vendor+" · "+device.categoryLabel).font(.system(size:10)).foregroundStyle(CenterTheme.muted).lineLimit(1) }
                HStack { CenterBadge(text:device.controllable ? "Ready" : device.status == "native-owned" ? "Native owned" : device.status == "hardware-modes-only" ? "Modes only" : device.backend == "inventory" ? "Detected only" : "Confirm first",good:device.controllable);Spacer();if device.led_count>0 { Text("\(device.led_count) \(device.backend == "native" ? "zones" : "LEDs")").font(.system(size:9,design:.monospaced)).foregroundStyle(CenterTheme.muted) } }
                Text(device.backend == "openrgb" ? "OpenRGB bridge" : device.backend == "native" ? "Native NVIDIA driver" : "No lighting driver attached").font(.system(size:9)).foregroundStyle(CenterTheme.muted)
            }.padding(19).frame(maxWidth:.infinity,alignment:.leading).background(center.selected.contains(device.id) ? CenterTheme.accent.opacity(0.045) : CenterTheme.surface).clipShape(RoundedRectangle(cornerRadius:17)).overlay(RoundedRectangle(cornerRadius:17).stroke(center.selected.contains(device.id) ? CenterTheme.accent.opacity(0.5) : .white.opacity(0.065),lineWidth:1))
        }.buttonStyle(PressFeedbackStyle()).help(device.detail).contextMenu { Button("Device details") { center.activeDevice=device } }
    }
}

struct CenterWorkspace:View {
    @ObservedObject var center:CenterModel
    let page:String
    var body:some View {
        VStack(alignment:.leading,spacing:24) {
            if page == "Overview" { overview }
            else if page == "Devices" { devices }
            else if page == "Scenes" { sceneEditor }
            else if page == "Layout" { layout }
            else { connections }
            if !center.error.isEmpty { CenterPanel { Label(center.error,systemImage:"exclamationmark.triangle").font(.system(size:12)).foregroundStyle(.orange) } }
            if !center.state.errors.isEmpty { DisclosureGroup("Connection & device details") { ForEach(Array(center.state.errors.enumerated()),id:\.offset) { _,value in Text(value).font(.system(size:10,design:.monospaced)).foregroundStyle(CenterTheme.muted).textSelection(.enabled) } } }
        }.foregroundStyle(Color(red:0.91,green:0.94,blue:0.93)).sheet(item:$center.activeDevice) { device in CenterDeviceInspector(device:device) }
    }
    private var overview:some View {
        VStack(alignment:.leading,spacing:25) {
            CenterHeading(eyebrow:"Workspace / local",title:"Control Center",subtitle:"Manage your setup, compose scenes and control compatible devices together.")
            ZStack(alignment:.leading) {
                RoundedRectangle(cornerRadius:23).fill(LinearGradient(colors:[Color(red:0.10,green:0.16,blue:0.13),CenterTheme.surface],startPoint:.topLeading,endPoint:.bottomTrailing))
                HStack(alignment:.center,spacing:22) {
                    VStack(alignment:.leading,spacing:14) { CenterBadge(text:center.state.running ? "Scene active" : "Workspace ready",good:center.online);Text(center.state.running ? center.state.scene.mode.capitalized : "Your lighting workspace").font(.system(size:25,weight:.semibold,design:.rounded));Text("Native GPU control and OpenRGB devices.\nOne local engine, shared scenes.").font(.system(size:12)).foregroundStyle(CenterTheme.muted);HStack { CenterAction(title:center.busy ? "Discovering…" : "Discover devices",symbol:"arrow.clockwise",action:center.discover).disabled(!center.online || center.busy);if !center.online { Button("Start Core",action:center.start) } } }
                    Spacer(minLength:0)
                    ZStack { ForEach(0..<4) { i in RoundedRectangle(cornerRadius:CGFloat(22+i*6)).stroke(CenterTheme.accent.opacity(0.05+Double(i)*0.02),lineWidth:1).frame(width:CGFloat(82+i*30),height:CGFloat(82+i*30)).rotationEffect(.degrees(20)) };Image(systemName:"circle.hexagongrid").font(.system(size:54,weight:.ultraLight)).foregroundStyle(CenterTheme.accent.opacity(0.85)) }.frame(width:185,height:185)
                }.padding(27)
            }.frame(height:245)
            HStack(spacing:14) { metric("Controllable",value:"\(center.controllable.count)",symbol:"slider.horizontal.3");metric("Detected entries",value:"\(center.state.devices.count)",symbol:"externaldrive.connected.to.line.below");metric("Engine",value:center.state.running ? "Running" : "Idle",symbol:"waveform.path") }
            HStack { Text("Devices in your workspace").font(.system(size:17,weight:.semibold));Spacer();Text("\(center.selected.count) selected").font(.system(size:10,design:.monospaced)).foregroundStyle(CenterTheme.muted) }
            grid(Array(center.state.devices.prefix(4)))
            if center.state.devices.isEmpty { emptyState }
        }
    }
    private func metric(_ title:String,value:String,symbol:String)->some View { CenterPanel { HStack(alignment:.top) { VStack(alignment:.leading,spacing:10) { Text(title).font(.system(size:10)).foregroundStyle(CenterTheme.muted);Text(value).font(.system(size:25,weight:.medium,design:.rounded)) };Spacer();Image(systemName:symbol).foregroundStyle(CenterTheme.aqua) } } }
    private func grid(_ devices:[CenterDevice])->some View { LazyVGrid(columns:[GridItem(.adaptive(minimum:210),spacing:14)],spacing:14) { ForEach(devices) { device in CenterDeviceCard(center:center,device:device) } } }
    private var emptyState:some View { CenterPanel { VStack(alignment:.leading,spacing:12) { Image(systemName:"cable.connector").font(.system(size:25,weight:.light)).foregroundStyle(CenterTheme.aqua);Text("Connect your lighting hardware").font(.headline);Text("Discovery reads native GPU, USB and memory inventory, then connects to an OpenRGB SDK server on 127.0.0.1:6742. Inventory-only entries cannot receive lighting commands.").font(.system(size:12)).foregroundStyle(CenterTheme.muted) } } }
    private var devices:some View {
        VStack(alignment:.leading,spacing:22) {
            CenterHeading(eyebrow:"Device library",title:"Your devices",subtitle:"GPU, memory, USB peripherals and cooling — grouped by actual control capability.")
            HStack { ScrollView(.horizontal,showsIndicators:false) { HStack(spacing:7) { ForEach([("all","All"),("gpu","GPU"),("dram","Memory"),("keyboard","Keyboards"),("mouse","Mice"),("cooler","Cooling"),("usb","USB")],id:\.0) { key,label in Button { center.filter=key } label: { Text(label).font(.system(size:10,weight:.medium)).padding(.horizontal,12).padding(.vertical,8).background(center.filter == key ? CenterTheme.accent.opacity(0.12) : CenterTheme.surface).clipShape(Capsule()).foregroundStyle(center.filter == key ? CenterTheme.accent : CenterTheme.muted) }.buttonStyle(PressFeedbackStyle()) } } };Button("Refresh",action:center.discover).disabled(center.busy || !center.online) }
            grid(center.visible)
            if center.visible.isEmpty { emptyState }
            Text("Select controllable cards to include them in a scene. Detected-only devices are shown for inventory and driver development; recognition does not enable writes.").font(.system(size:11)).foregroundStyle(CenterTheme.muted)
        }
    }
    private func sceneColor(_ index:Int)->Binding<Color> { Binding(get:{ let hex=center.scene.palette[min(index,center.scene.palette.count-1)];let rgb=UInt32(hex,radix:16) ?? 0;return Color(red:Double((rgb>>16)&255)/255,green:Double((rgb>>8)&255)/255,blue:Double(rgb&255)/255) },set:{ value in while center.scene.palette.count<=index { center.scene.palette.append(center.scene.palette.last ?? "ffffff") };let c=NSColor(value).usingColorSpace(.sRGB) ?? .white;center.scene.palette[index]=[c.redComponent,c.greenComponent,c.blueComponent].map { String(format:"%02x",Int(($0*255).rounded())) }.joined() }) }
    private var sceneEditor:some View {
        VStack(alignment:.leading,spacing:22) {
            CenterHeading(eyebrow:"Shared lighting engine",title:"Scenes",subtitle:"A common clock and palette across selected devices. Changes apply only when you start the scene.")
            CenterPanel {
                VStack(alignment:.leading,spacing:20) {
                    HStack { ForEach([("static","Static","circle.fill"),("gradient","Gradient","slider.horizontal.3"),("spectrum","Spectrum","circle.lefthalf.filled"),("breathing","Breathing","waveform.path"),("wave","Wave","water.waves")],id:\.0) { key,label,symbol in Button { center.scene.mode=key } label: { VStack(spacing:11) { Image(systemName:symbol).font(.system(size:22,weight:.light));Text(label).font(.system(size:10,weight:.medium)) }.frame(maxWidth:.infinity).frame(height:83).foregroundStyle(center.scene.mode == key ? CenterTheme.accent : CenterTheme.muted).background(center.scene.mode == key ? CenterTheme.accent.opacity(0.09) : CenterTheme.background.opacity(0.5)).clipShape(RoundedRectangle(cornerRadius:12)).overlay(RoundedRectangle(cornerRadius:12).stroke(center.scene.mode == key ? CenterTheme.accent.opacity(0.4) : .clear,lineWidth:1)) }.buttonStyle(PressFeedbackStyle()) } }
                    if center.scene.mode != "spectrum" { HStack { ForEach(0..<( ["wave","gradient"].contains(center.scene.mode) ? 3 : 1),id:\.self) { i in ColorPicker("Color \(i+1)",selection:sceneColor(i),supportsOpacity:false) };Spacer() }.font(.system(size:10)) }
                    HStack { Text("Brightness").frame(width:75,alignment:.leading);Slider(value:$center.scene.brightness,in:0...100);Text("\(Int(center.scene.brightness))%").monospacedDigit().frame(width:40) }.font(.system(size:11)).foregroundStyle(CenterTheme.muted)
                    if !["static","gradient"].contains(center.scene.mode) { HStack { Text("Speed").frame(width:75,alignment:.leading);Slider(value:$center.scene.speed,in:1...100);Text("\(Int(center.scene.speed))%").monospacedDigit().frame(width:40) }.font(.system(size:11)).foregroundStyle(CenterTheme.muted) }
                    Picker("Spatial axis",selection:$center.scene.axis) { Text("Horizontal").tag("x");Text("Vertical").tag("y") }.pickerStyle(.segmented)
                    HStack { CenterAction(title:"Start scene",symbol:"play.fill",action:center.apply).disabled(!center.online || center.busy || !center.sceneCompatible);Button("Stop",action:center.stop).disabled(!center.state.running || center.busy);Button("Blackout",action:center.blackout).disabled(center.selected.isEmpty || center.busy);Spacer();Text("\(center.selected.count) TARGETS").font(.system(size:9,design:.monospaced)).foregroundStyle(CenterTheme.muted) }
                    if !center.sceneCompatible && !center.selected.isEmpty { Text("This scene needs Direct-mode devices. Native GPUs can join shared Static scenes and three-zone Gradient; use GPU Lab for their onboard animated effects.").font(.system(size:11)).foregroundStyle(.orange) }
                    Text(center.state.message).font(.system(size:10)).foregroundStyle(CenterTheme.muted)
                }
            }
            HStack { Text("Scene targets").font(.system(size:16,weight:.semibold));Spacer();Button("Select ready") { center.selected=Set(center.controllable.map { $0.id }) };Button("Clear") { center.selected=[] } }
            grid(center.state.devices.filter { $0.controllable })
            CenterPanel { VStack(alignment:.leading,spacing:15) { HStack { TextField("Scene name",text:$center.sceneName).textFieldStyle(.roundedBorder);Button("Save scene",action:center.saveScene).disabled(center.busy || !center.online) };Text("Saved scenes contain effect settings. Loading a scene never writes to hardware or guesses device bindings.").font(.system(size:10)).foregroundStyle(CenterTheme.muted);ForEach(center.state.scenes) { saved in Button { center.scene=saved.config } label: { HStack { Image(systemName:"square.stack");Text(saved.name);Spacer();Text(saved.config.mode.capitalized).foregroundStyle(CenterTheme.muted);Image(systemName:"arrow.up.right") } }.buttonStyle(.plain) } } }
        }
    }
    private var layout:some View {
        VStack(alignment:.leading,spacing:22) {
            CenterHeading(eyebrow:"Spatial lighting",title:"Setup layout",subtitle:"Drag a controllable device to position it in the shared effect space. Moving a device stops the active scene.")
            GeometryReader { geometry in
                ZStack {
                    RoundedRectangle(cornerRadius:20).fill(CenterTheme.surface)
                    Path { path in for x in stride(from:CGFloat(0),through:geometry.size.width,by:32) { path.move(to:CGPoint(x:x,y:0));path.addLine(to:CGPoint(x:x,y:geometry.size.height)) };for y in stride(from:CGFloat(0),through:geometry.size.height,by:32) { path.move(to:CGPoint(x:0,y:y));path.addLine(to:CGPoint(x:geometry.size.width,y:y)) } }.stroke(.white.opacity(0.025),lineWidth:1)
                    ForEach(center.controllable) { device in
                        let p=center.state.layout[device.id] ?? CenterPosition(x:0.5,y:0.5,width:0.22)
                        VStack(spacing:8) { Image(systemName:device.symbol).font(.system(size:25,weight:.light));Text(device.name).font(.system(size:9,weight:.medium)).lineLimit(2).multilineTextAlignment(.center) }.foregroundStyle(CenterTheme.accent).padding(12).frame(width:122,height:85).background(CenterTheme.background).clipShape(RoundedRectangle(cornerRadius:14)).overlay(RoundedRectangle(cornerRadius:14).stroke(CenterTheme.accent.opacity(0.25),lineWidth:1)).position(x:max(65,min(geometry.size.width-65,p.x*geometry.size.width)),y:max(50,min(geometry.size.height-50,p.y*geometry.size.height))).gesture(DragGesture(coordinateSpace:.named("lighting-canvas")).onEnded { value in center.move(device.id,x:Double(value.location.x/geometry.size.width),y:Double(value.location.y/geometry.size.height)) })
                    }
                    if center.controllable.isEmpty { Text("Discover and confirm a controllable device first").font(.system(size:12)).foregroundStyle(CenterTheme.muted) }
                }.coordinateSpace(name:"lighting-canvas").clipShape(RoundedRectangle(cornerRadius:20))
            }.frame(height:420)
            Text("Horizontal placement drives left-to-right waves and gradients. LED strip order is used within each device; keyboard matrix placement is not yet mapped. Unique device placement is saved locally. Identical devices need manual placement after rediscovery.").font(.system(size:11)).foregroundStyle(CenterTheme.muted)
        }
    }
    private var connections:some View {
        VStack(alignment:.leading,spacing:22) {
            CenterHeading(eyebrow:"Backend connections",title:"Connections",subtitle:"Hardware adapters stay separate from the shared engine. All Core API access remains on this Mac.")
            CenterPanel { VStack(alignment:.leading,spacing:16) { HStack { Label("OpenRGB bridge",systemImage:"point.3.connected.trianglepath.dotted").font(.headline);Spacer();CenterBadge(text:center.state.bridge,good:center.state.bridge == "connected") };Text("127.0.0.1 : 6742").font(.system(size:20,weight:.medium,design:.monospaced));Text("Enable the SDK server in OpenRGB, then discover devices. Keyboards, mice, DRAM, USB coolers and controllers can be controlled when that server provides a working Direct-mode device. The OpenRGB device catalog alone does not prove macOS compatibility.").font(.system(size:12)).foregroundStyle(CenterTheme.muted);CenterAction(title:"Connect & discover",symbol:"arrow.clockwise",action:center.discover).disabled(center.busy || !center.online) } }
            CenterPanel { VStack(alignment:.leading,spacing:14) { HStack { Label("Native NVIDIA",systemImage:"pciecard").font(.headline);Spacer();CenterBadge(text:"Native driver") };Text("The existing NullMoth/NVRM controller paths remain available in GPU Lab. A local visual confirmation is required before Core can include a GPU in a scene.").font(.system(size:12)).foregroundStyle(CenterTheme.muted);Text("DRAM / native USB: inventory is available; additional host transports and device-specific protocols remain development work.").font(.system(size:11)).foregroundStyle(CenterTheme.muted) } }
            CenterPanel { VStack(alignment:.leading,spacing:12) { Label("Private local Core",systemImage:"lock.shield").font(.headline);Text("The API uses a per-process credential and binds only to 127.0.0.1. No LAN listener, cloud account or Android access is enabled. Saved scenes stay in Documents/HackinFX. The engine stops when HackinFX quits.").font(.system(size:12)).foregroundStyle(CenterTheme.muted) } }
        }
    }
}

private struct CenterDeviceInspector:View {
    let device:CenterDevice
    @Environment(\.dismiss) var dismiss
    var body:some View {
        VStack(alignment:.leading,spacing:19) {
            HStack { Image(systemName:device.symbol).font(.system(size:30,weight:.light)).foregroundStyle(CenterTheme.accent);Spacer();CenterBadge(text:device.backend,good:device.controllable) }
            Text(device.name).font(.system(size:23,weight:.semibold,design:.rounded))
            Text(device.vendor+" · "+device.categoryLabel).foregroundStyle(CenterTheme.muted)
            Divider()
            Text(device.detail).font(.system(size:12)).fixedSize(horizontal:false,vertical:true)
            Label(device.direct ? "Direct per-LED scene streaming" : device.controllable ? "Static scenes and supported native effects" : "Lighting control unavailable",systemImage:device.controllable ? "checkmark.circle" : "info.circle").font(.system(size:12)).foregroundStyle(device.controllable ? CenterTheme.accent : CenterTheme.muted)
            if let zones=device.zones,!zones.isEmpty { Text("ZONES").font(.system(size:8,design:.monospaced)).foregroundStyle(CenterTheme.muted);ForEach(Array(zones.prefix(8).enumerated()),id:\.offset) { _,zone in HStack { Text(zone.name);Spacer();Text("\(zone.led_count) LEDs").foregroundStyle(CenterTheme.muted) }.font(.system(size:11)) } }
            if let modes=device.modes,!modes.isEmpty { Text("Hardware modes: "+modes.prefix(12).map { $0.name }.joined(separator:", ")).font(.system(size:11)).foregroundStyle(CenterTheme.muted) }
            Text("Connection readiness is not a physical lighting confirmation.").font(.caption).foregroundStyle(CenterTheme.muted)
            HStack { Spacer();Button("Close") { dismiss() }.keyboardShortcut(.cancelAction) }
        }.padding(28).frame(width:510).background(CenterTheme.background).foregroundStyle(.white).preferredColorScheme(.dark)
    }
}

// Used only by the explicit CLI design-check renderer, never by device discovery.
extension CenterModel {
    func loadDesignFixture() {
        let fixtures:[CenterDevice] = [
            CenterDevice(id:"sample:gpu",fingerprint:"sample-gpu",name:"GPU controller",vendor:"Sample device",category:"gpu",backend:"native",led_count:3,direct:false,controllable:true,status:"ready",detail:"Design fixture, not detected hardware"),
            CenterDevice(id:"sample:keyboard",fingerprint:"sample-keyboard",name:"Mechanical keyboard",vendor:"Sample device",category:"keyboard",backend:"openrgb",led_count:104,direct:true,controllable:true,status:"ready",detail:"Design fixture, not detected hardware"),
            CenterDevice(id:"sample:cooler",fingerprint:"sample-cooler",name:"USB cooling",vendor:"Sample device",category:"cooler",backend:"openrgb",led_count:24,direct:true,controllable:true,status:"ready",detail:"Design fixture, not detected hardware"),
            CenterDevice(id:"sample:dram",fingerprint:"sample-dram",name:"Memory kit",vendor:"Sample device",category:"dram",backend:"inventory",led_count:0,direct:false,controllable:false,status:"inventory-only",detail:"Design fixture, not detected hardware")
        ]
        state=CenterState(schema:1,devices:fixtures,layout:Dictionary(uniqueKeysWithValues:fixtures.enumerated().map { i,d in (d.id,CenterPosition(x:Double(i+1)/5,y:0.5,width:0.2)) }),scene:CenterScene(),running:false,frames:0,errors:[],bridge:"connected",scenes:[SavedCenterScene(name:"Evening",config:CenterScene())],message:"SAMPLE DATA — design validation only")
        selected=["sample:keyboard","sample:cooler"];online=true
    }
}
