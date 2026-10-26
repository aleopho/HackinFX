// SPDX-License-Identifier: GPL-2.0-or-later
import AppKit
import SwiftUI
import WidgetKit
import ServiceManagement

enum JSONScalar:Codable {
    case string(String),number(Double),bool(Bool)
    init(from decoder:Decoder)throws { let c=try decoder.singleValueContainer();if let b=try? c.decode(Bool.self) { self = .bool(b) } else if let n=try? c.decode(Double.self) { self = .number(n) } else { self = .string(try c.decode(String.self)) } }
    func encode(to encoder:Encoder)throws { var c=encoder.singleValueContainer();switch self { case .string(let v):try c.encode(v);case .number(let v):try c.encode(v);case .bool(let v):try c.encode(v) } }
}
struct CenterLEDPosition:Codable { let x:Double;let y:Double }
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
    var startup_excluded:Bool? = nil
    var hardware_state:[String:JSONScalar]? = nil
    var led_positions:[CenterLEDPosition]? = nil
    var color_scope:String? = nil
    var physical_led_count:Int? = nil
    var layout:String? = nil
    var topology_source:String? = nil
    var onboard_modes:[String]? = nil
    var static_modes:[String]? = nil
    var usb_id:String? = nil
    var driver:String? = nil
    var catalog_matches:[String]? = nil
    var zones:[CenterZone]? = nil
    var modes:[CenterMode]? = nil
    var symbol: String {
        switch category {
        case "gpu":return "cpu"
        case "dram":return "memorychip"
        case "keyboard","keypad":return "keyboard"
        case "mouse":return "computermouse"
        case "cooler","controller":return "fanblades"
        case "strip","light":return "light.strip.2"
        case "mainboard":return "cpu"
        default:return "cable.connector"
        }
    }
    var lightCountLabel:String {
        if color_scope == "whole-device" { return "1 color zone · LED count unknown" }
        if driver == "asus-keyboard",color_scope == "per-led" { return "\(led_count) mapped LEDs" }
        if backend == "native" || driver == "asus-spatha" { return "\(led_count) color zones" }
        return "\(led_count) LEDs"
    }
    var categoryLabel: String { ["dram":"Memory","gpu":"GPU","cooler":"Cooling","strip":"Lighting","keyboard":"Keyboard","mouse":"Mouse","usb":"USB","mainboard":"Mainboard","controller":"Controller" ][category] ?? category.capitalized }
}
struct CenterScene: Codable,Equatable {
    var synchronized = true
    var mapping = "mirror"
    var scale = 1.0
    var density = 55.0
    var reverse = false
    var mode = "twinkle"
    var palette = ["a7f3d0"]
    var brightness = 100.0
    var speed = 65.0
    var axis = "x"
    var fps = 30.0
    var sync_policy = "adaptive"
}
private struct PublicRelease:Decodable { let tag_name:String;let html_url:String;let draft:Bool;let prerelease:Bool }
private struct StringError:LocalizedError { let message:String;init(_ message:String) { self.message=message };var errorDescription:String? { message } }
struct SavedCenterScene: Codable, Identifiable { var id:String { name }; let name: String; let config:CenterScene }
struct CenterPosition: Codable { var x:Double;var y:Double;var width:Double }
struct CoreOutput:Codable { let frames:Int;let fps:Double;let command_ms:Double;let age_ms:Double;let missed:Int;var interval_ms:Double?=nil;var jitter_ms:Double?=nil;var max_interval_ms:Double?=nil }
struct CoreSync:Codable { let clock:String;let dropped:Int;let frames:Int;var outputs:[String:CoreOutput]? = nil }
struct NanoleafCandidate:Codable,Identifiable { let id:String;let address:String;let name:String;let model:String }
struct CenterState: Codable {
    var nanoleaf_candidates:[NanoleafCandidate]? = nil
    var sync:CoreSync? = nil
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
    @Published var nanoleafAddress=""
    @Published var state = CenterState.empty
    @Published var selected = Set<String>() { didSet { if selected != oldValue { scheduleLive() } } }
    @Published var scene = CenterScene() { didSet { scheduleLive() } }
    @Published var filter = "lighting"
    @Published var busy = false
    @Published var online = false
    @Published var error = ""
    @Published var sceneName = "My scene"
    @Published var activeDevice: CenterDevice?
    @Published var loginEnabled = UserDefaults.standard.object(forKey:"LaunchAtLogin") as? Bool ?? true
    @Published var loginMessage = "Launch automatically after macOS sign-in."
    func configureLoginAtLaunch() { setLaunchAtLogin(loginEnabled) }
    func setLaunchAtLogin(_ enabled:Bool) {
        loginEnabled=enabled;UserDefaults.standard.set(enabled,forKey:"LaunchAtLogin")
        guard Bundle.main.bundleURL.path.hasPrefix("/Applications/") else { loginMessage="Install HackinFX in Applications to enable login launch.";return }
        do {
            if enabled && SMAppService.mainApp.status != .enabled { try SMAppService.mainApp.register() }
            if !enabled && SMAppService.mainApp.status != .notRegistered { try SMAppService.mainApp.unregister() }
            switch SMAppService.mainApp.status {
            case .enabled:loginMessage="Enabled · starts after macOS sign-in and starts mint Twinkle on ready lighting devices. RAM is excluded."
            case .requiresApproval:loginMessage="Allow HackinFX in System Settings → General → Login Items."
            default:loginMessage=enabled ? "Login launch is unavailable. Check Login Items in System Settings.":"Launch at login is off."
            }
        } catch { loginMessage="Login launch: \(error.localizedDescription)" }
    }
    @Published var liveStatus = "Connecting to your devices…"
    @Published var automaticUpdates = UserDefaults.standard.object(forKey:"AutomaticUpdateChecks") as? Bool ?? true { didSet { UserDefaults.standard.set(automaticUpdates,forKey:"AutomaticUpdateChecks") } }
    @Published var checkingUpdates = false
    @Published var updateMessage = "Check GitHub for the latest public release."
    @Published var updateURL:URL?
    private var liveWork:DispatchWorkItem?
    private var livePending=false
    private var suppressLive=false
    private var liveRequest=false
    private var process:Process?
    private var discovery:CoreDiscovery?
    private var timer:Timer?
    private var polling = false
    private var shuttingDown = false
    private var logHandle:FileHandle?
    private var sessionFile:URL?
    private let session=URLSession(configuration:.ephemeral)
    private var mutationQueue:[()->Void]=[]
    private var mutating=false
    private func nextMutation() {
        guard !mutating && !mutationQueue.isEmpty && !shuttingDown else { return }
        mutating=true;mutationQueue.removeFirst()()
    }
    var controllable:[CenterDevice] { state.devices.filter { $0.controllable } }
    var visible:[CenterDevice] { state.devices.filter { device in filter == "all" || (filter == "lighting" && (device.controllable || device.driver != nil || !(device.catalog_matches ?? []).isEmpty)) || (filter == "attention" && !device.controllable && (device.driver != nil || !(device.catalog_matches ?? []).isEmpty)) || device.category == filter } }
    var chosen:[CenterDevice] { state.devices.filter { selected.contains($0.id) } }
    var canAnimate:Bool { !chosen.isEmpty && chosen.allSatisfy { $0.direct } }
    var sceneCompatible:Bool { !chosen.isEmpty && chosen.allSatisfy { $0.controllable && (!scene.synchronized || ["static","gradient"].contains(scene.mode) || $0.direct) && ($0.direct || ($0.static_modes ?? ["static"]).contains(scene.mode)) } }
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
            busy=true
            request("/v1/initialize") { result in
                self.suppressLive=true;self.accept(result)
                if case .success(let state)=result { self.scene=state.scene;self.selected=Set(state.devices.filter { $0.controllable && $0.category != "dram" && $0.startup_excluded != true }.map { $0.id });self.liveStatus="Mint Twinkle · 65% speed · RAM excluded" }
                self.suppressLive=false;self.busy=false;self.livePending=false;self.publishWidget()
            };return
        }
        guard attempt<60,process?.isRunning == true else { busy=false;error="Core did not become available. Check its local log or close another HackinFX instance.";return }
        DispatchQueue.main.asyncAfter(deadline:.now()+0.1) { self.awaitDiscovery(url,attempt:attempt+1) }
    }
    private func request(_ path:String,method:String="POST",body:[String:Any]=[:],completion:@escaping(Result<CenterState,Error>)->Void) {
        guard let info=discovery else { return }
        var request=URLRequest(url:URL(string:"http://127.0.0.1:\(info.port)\(path)")!);request.httpMethod=method;request.timeoutInterval=180
        request.setValue("Bearer "+info.credential,forHTTPHeaderField:"Authorization")
        if method == "POST" { request.setValue("application/json",forHTTPHeaderField:"Content-Type");request.httpBody=try? JSONSerialization.data(withJSONObject:body) }
        let launch = {
        self.session.dataTask(with:request) { data,response,error in
            let result:Result<CenterState,Error>
            if let error=error { result = .failure(error) }
            else if let data=data,(response as? HTTPURLResponse)?.statusCode == 200,let state=try? JSONDecoder().decode(CenterState.self,from:data),state.schema == 1 { result = .success(state) }
            else {
                let object=data.flatMap { try? JSONSerialization.jsonObject(with:$0) as? [String:Any] }
                result = .failure(NSError(domain:"HackinFXCore",code:1,userInfo:[NSLocalizedDescriptionKey:object?["error"] as? String ?? "Core returned an unreadable response"]))
            }
            DispatchQueue.main.async {
                completion(result)
                if method == "POST" { self.mutating=false;self.nextMutation() }
            }
        }.resume()
        }
        if method == "POST" { mutationQueue.append(launch);nextMutation() } else { launch() }
    }
    private func accept(_ result:Result<CenterState,Error>,clearError:Bool=true) {
        switch result {
        case .success(let state):self.state=state;self.publishWidget();let known=Set(state.devices.filter { $0.controllable }.map { $0.id });selected.formIntersection(known);if clearError { error="" }
        case .failure(let error):self.error=error.localizedDescription
        }
    }
    func poll() {
        guard online && !busy && !liveRequest && !mutating && !polling else { return };polling=true
        request("/v1/status",method:"GET") { result in self.polling=false;if !self.mutating && !self.liveRequest { self.accept(result,clearError:false) };self.flushLive() }
    }
    func discover() {
        guard online && !busy else { return };busy=true
        request("/v1/discover") { result in self.suppressLive=true;self.accept(result);self.selected=Set(self.controllable.filter { $0.category != "dram" && $0.startup_excluded != true }.map { $0.id });self.suppressLive=false;self.busy=false;self.scheduleLive() }
    }
    func toggle(_ device:CenterDevice) { guard device.controllable else { activeDevice=device;return };if selected.contains(device.id) { selected.remove(device.id) } else { selected.insert(device.id) } }
    func scheduleLive() {
        guard !suppressLive && !shuttingDown && discovery != nil else { return }
        liveWork?.cancel();livePending=true
        liveStatus=selected.isEmpty ? "Select devices to control" : "Updating lighting…"
        let work=DispatchWorkItem { [weak self] in self?.flushLive() }
        liveWork=work;DispatchQueue.main.asyncAfter(deadline:.now()+0.14,execute:work)
    }
    private func flushLive() {
        guard livePending && online && !busy && !liveRequest && !shuttingDown else { return }
        let targets=chosen.filter { $0.controllable && (!scene.synchronized || ["static","gradient"].contains(scene.mode) || $0.direct) && ($0.direct || ($0.static_modes ?? ["static"]).contains(scene.mode)) }
        guard !targets.isEmpty else { liveStatus=selected.isEmpty ? "Select devices to control":"No selected device supports this effect";livePending=false;return }
        let skipped=selected.count-targets.count
        livePending=false;liveRequest=true;liveStatus="Updating lighting…"
        let encoded=(try? JSONSerialization.jsonObject(with:JSONEncoder().encode(scene))) as? [String:Any] ?? [:]
        request("/v1/scene/start",body:["config":encoded,"devices":targets.map { $0.id }.sorted()]) { result in
            self.liveRequest=false;self.accept(result)
            switch result { case .success:self.liveStatus=skipped>0 ? "Live · \(targets.count) devices · \(skipped) skipped":"Live · changes sent";case .failure(let failure):self.liveStatus="Lighting unavailable · \(failure.localizedDescription)" }
            if self.livePending { self.scheduleLive() }
        }
    }
    func apply() { scheduleLive() } // Used by menu actions; the editor has no Apply step.
    func suspendForGPULab(_ completion:@escaping(Bool)->Void) {
        guard online else { completion(true);return };guard !busy else { completion(false);return }
        liveWork?.cancel();livePending=false;busy=true
        request("/v1/scene/stop") { result in self.busy=false;self.accept(result);if case .success=result { completion(true) } else { completion(false) } }
    }
    func stop() {
        guard online && !busy else { return };liveWork?.cancel();livePending=false;busy=true
        request("/v1/scene/stop") { result in self.busy=false;self.accept(result);self.liveStatus="Animation paused · last colors kept" }
    }
    func blackout() { scene.mode="static";scene.brightness=0 }
    func checkForUpdates() {
        guard !checkingUpdates else { return };checkingUpdates=true;updateURL=nil;updateMessage="Checking GitHub…"
        var request=URLRequest(url:URL(string:"https://api.github.com/repos/aleopho/HackinFX/releases/latest")!)
        request.timeoutInterval=20;request.setValue("application/vnd.github+json",forHTTPHeaderField:"Accept");request.setValue("HackinFX",forHTTPHeaderField:"User-Agent")
        session.dataTask(with:request) { data,response,error in
            let result:Result<PublicRelease,StringError>
            do {
                if let error=error { throw error }
                guard (response as? HTTPURLResponse)?.statusCode == 200,let data=data else { throw StringError("GitHub is unavailable or its request limit was reached. Try again later.") }
                let release=try JSONDecoder().decode(PublicRelease.self,from:data)
                guard !release.draft && !release.prerelease,let url=URL(string:release.html_url),url.scheme=="https",url.host=="github.com",url.path.hasPrefix("/aleopho/HackinFX/releases/tag/") else { throw StringError("GitHub returned an invalid release.") }
                result = .success(release)
            } catch { result = .failure(StringError(error.localizedDescription)) }
            DispatchQueue.main.async {
                self.checkingUpdates=false
                switch result {
                case .success(let release):
                    let current=Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "2.4.0"
                    let newer=ReleaseVersion.isNewer(release.tag_name,than:current)
                    self.updateMessage=newer ? "HackinFX \(release.tag_name) is available." : "You're up to date. Installed: \(current) · public release: \(release.tag_name)."
                    if newer { self.updateURL=URL(string:release.html_url) }
                case .failure(let error):self.updateMessage=error.localizedDescription
                }
            }
        }.resume()
    }
    func findNanoleaf() {
        guard online && !busy else { return };busy=true;error=""
        request("/v1/nanoleaf/scan") { result in
            self.busy=false;self.accept(result)
            if case .success(let state)=result { self.nanoleafAddress=state.nanoleaf_candidates?.first?.address ?? "";if self.nanoleafAddress.isEmpty { self.error="No Shapes found. Check that the controller and Mac are on the same network and Bonjour is allowed." } }
        }
    }
    func pairNanoleaf() {
        guard online && !busy else { return };busy=true;error=""
        request("/v1/nanoleaf/pair",body:["address":nanoleafAddress.trimmingCharacters(in:.whitespacesAndNewlines)]) { result in
            self.busy=false;self.accept(result);if case .success=result { self.livePending=true };self.flushLive()
        }
    }
    func probeRAM() {
        guard online && !busy else { return };busy=true;error=""
        request("/v1/ram/probe") { result in self.busy=false;self.accept(result);if case .success=result { self.livePending=true };self.flushLive() }
    }
    func saveScene() {
        guard online && !busy else { return };busy=true
        let encoded=(try? JSONSerialization.jsonObject(with:JSONEncoder().encode(scene))) as? [String:Any] ?? [:]
        request("/v1/scenes/save",body:["name":sceneName,"config":encoded]) { result in self.busy=false;self.accept(result);self.flushLive() }
    }
    func move(_ id:String,x:Double,y:Double,width:Double?=nil) {
        guard online && !busy else { return };busy=true
        let w=width ?? state.layout[id]?.width ?? 0.22
        request("/v1/layout",body:[id:["x":min(1,max(0,x)),"y":min(1,max(0,y)),"width":w]]) { result in self.busy=false;self.accept(result);self.scheduleLive() }
    }
    private var widgetKey=""
    private var lastWidgetReload=Date.distantPast
    private var widgetReload:DispatchWorkItem?
    func publishWidget() {
        guard online && !state.devices.isEmpty else { return }
        let gpu=state.devices.first { $0.category=="gpu" && $0.controllable } ?? state.devices.first { $0.category=="gpu" }
        let title=gpu?.name ?? "Lighting workspace"
        let status=state.errors.isEmpty ? "Lighting commands":"Needs attention"
        let key="\(state.scene.mode)|\(state.scene.palette)|\(state.scene.brightness)|\(controllable.count)|\(title)|\(status)"
        guard key != widgetKey else { return }
        let value=WidgetStatusSnapshot(readyDevices:controllable.count,statusText:status,gpuName:title,boardVendor:gpu?.vendor ?? "",profileReady:!controllable.isEmpty,lastCommand:state.scene.mode,updatedAt:Date(),colors:state.scene.palette,brightness:state.scene.brightness)
        let folder=FileManager.default.urls(for:.applicationSupportDirectory,in:.userDomainMask)[0].appendingPathComponent("HackinFX/Widget",isDirectory:true)
        do {
            try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
            let encoder=JSONEncoder();encoder.dateEncodingStrategy = .iso8601
            try encoder.encode(value).write(to:folder.appendingPathComponent("snapshot.json"),options:.atomic)
            widgetKey=key;widgetReload?.cancel()
            let work=DispatchWorkItem { self.lastWidgetReload=Date();WidgetCenter.shared.reloadTimelines(ofKind:"HackinFXStatus") }
            widgetReload=work;DispatchQueue.main.asyncAfter(deadline:.now()+max(0,5-Date().timeIntervalSince(lastWidgetReload)),execute:work)
        } catch { /* Widget failure must not block hardware control. */ }
    }
    func shutdown() {
        shuttingDown=true;liveWork?.cancel();livePending=false;timer?.invalidate();timer=nil
        if process?.isRunning == true { process?.terminate() }
        process=nil;discovery=nil;try? logHandle?.close();logHandle=nil
    }
}

enum CenterTheme {
    static let background=Color(red:0.035,green:0.047,blue:0.055)
    static let surface=Color(red:0.065,green:0.082,blue:0.09)
    static let elevated=Color(red:0.085,green:0.105,blue:0.11)
    static let accent=Color(red:0.77,green:0.94,blue:0.49)
    static let aqua=Color(red:0.31,green:0.82,blue:0.79)
    static let muted=Color(red:0.51,green:0.58,blue:0.59)
}
struct CenterPanel<Content:View>:View {
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
private struct CenterSecondaryStyle:ButtonStyle {
    @Environment(\.isEnabled) var enabled
    @Environment(\.accessibilityReduceMotion) var reduceMotion
    func makeBody(configuration:Configuration)->some View {
        configuration.label.font(.system(size:11,weight:.medium)).padding(.horizontal,12).padding(.vertical,8).foregroundStyle(.white.opacity(enabled ? 0.85:0.3)).background(.white.opacity(configuration.isPressed ? 0.10:0.04)).clipShape(RoundedRectangle(cornerRadius:8)).overlay(RoundedRectangle(cornerRadius:8).stroke(.white.opacity(0.07),lineWidth:1)).scaleEffect(configuration.isPressed && !reduceMotion ? 0.97:1).animation(reduceMotion ? nil:.easeOut(duration:0.15),value:configuration.isPressed)
    }
}
private struct CenterAction:View {
    let title:String
    let symbol:String
    let action:()->Void
    var body:some View { Button(action:action) { HStack { Text(title);Image(systemName:symbol) }.font(.system(size:12,weight:.semibold)).foregroundStyle(CenterTheme.background).padding(.horizontal,17).frame(height:38).background(CenterTheme.accent).clipShape(RoundedRectangle(cornerRadius:10)) }.buttonStyle(PressFeedbackStyle()) }
}

private struct CenterScenePreview:View {
    let scene:CenterScene
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    private func tint(_ index:Int,_ time:Double)->Color {
        let u=Double(index)/39
        let rgb=EffectMath.sample(mode:scene.mode,palette:EffectLibrary.palette(scene.palette),index:index,u:u,v:u,coord:u,time:time,speed:scene.speed,scale:scene.scale,density:scene.density,reverse:scene.reverse)
        let level=scene.brightness/25500
        return Color(red:max(0,min(1,rgb[0]*level)),green:max(0,min(1,rgb[1]*level)),blue:max(0,min(1,rgb[2]*level)))
    }
    var body:some View {
        TimelineView(.animation(minimumInterval:0.05,paused:reduceMotion || ["static","gradient"].contains(scene.mode))) { context in
            let time=reduceMotion ? 0:context.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy:3600)
            VStack(alignment:.leading,spacing:20) {
                HStack { Text(EffectLibrary.effect(scene.mode)?.name ?? scene.mode.capitalized).font(.system(size:20,weight:.semibold,design:.rounded));Spacer();Text("EFFECT VISUALIZATION").font(.system(size:7,design:.monospaced)).tracking(1.3).foregroundStyle(CenterTheme.muted) }
                HStack(spacing:4) { ForEach(0..<40) { i in Capsule().fill(tint(i,time)).frame(height:34).shadow(color:tint(i,time).opacity(0.45),radius:8) } }
            }.padding(20).background(LinearGradient(colors:[CenterTheme.background,CenterTheme.elevated.opacity(0.35)],startPoint:.topLeading,endPoint:.bottomTrailing)).clipShape(RoundedRectangle(cornerRadius:14))
        }.accessibilityLabel("Effect visualization. Not live LED feedback.")
    }
}

struct CenterNavigation:View {
    @ObservedObject var model:Model
    @ObservedObject var center:CenterModel
    @Environment(\.accessibilityReduceMotion) var reduceMotion
    @State private var advanced=false
    @Namespace private var selection
    private let pages=[("Overview","sun.max"),("Devices","externaldrive.connected.to.line.below"),("Canvas","rectangle.3.group"),("Effects","sparkles"),("Feedback","bubble.left.and.text.bubble.right")]
    var body:some View {
        VStack(alignment:.leading,spacing:0) {
            HStack(spacing:11) { Image(nsImage:NSImage(contentsOf:Bundle.main.url(forResource:"hackinfx-logo",withExtension:"png")!) ?? NSImage()).resizable().scaledToFit().frame(width:36,height:36);VStack(alignment:.leading,spacing:3) { Text("HackinFX").font(.system(size:21,weight:.semibold,design:.rounded));Text("LIGHTING STUDIO").font(.system(size:7,weight:.semibold,design:.monospaced)).tracking(2).foregroundStyle(CenterTheme.muted) } }.padding(.bottom,35)
            Text("WORKSPACE").font(.system(size:8,weight:.medium,design:.monospaced)).tracking(2).foregroundStyle(CenterTheme.muted).padding(.horizontal,12).padding(.bottom,12)
            ForEach(pages,id:\.0) { page,symbol in
                Button { model.page=page } label: {
                    HStack(spacing:12) { Image(systemName:symbol).font(.system(size:14)).frame(width:18);Text(page == "Overview" ? "Lighting" : page).font(.system(size:12,weight:.medium));Spacer();if page == "Devices" { Text("\(center.state.devices.count)").font(.system(size:10,design:.monospaced)) } }.foregroundStyle(model.page == page ? CenterTheme.accent : CenterTheme.muted).padding(.horizontal,13).frame(height:43).background { if model.page == page { RoundedRectangle(cornerRadius:10).fill(CenterTheme.accent.opacity(0.08)).matchedGeometryEffect(id:"center-nav",in:selection) } }
                }.buttonStyle(PressFeedbackStyle()).padding(.bottom,5)
            }
            Spacer(minLength:20)
            DisclosureGroup("Advanced",isExpanded:$advanced) {
                VStack(alignment:.leading,spacing:8) {
                    ForEach([("Studio","GPU Lab","cpu"),("Hardware","Diagnostics","waveform.path.ecg"),("Credits","Credits","heart")],id:\.0) { key,title,symbol in
                        Button { model.page=key } label: { Label(title,systemImage:symbol).font(.system(size:11)).foregroundStyle(model.page == key ? CenterTheme.accent:CenterTheme.muted).frame(maxWidth:.infinity,alignment:.leading).padding(.vertical,6) }.buttonStyle(.plain)
                    }
                }.padding(.top,10)
            }.font(.system(size:11)).foregroundStyle(CenterTheme.muted).padding(.horizontal,12).padding(.bottom,18)
            Button { model.page="Settings" } label: { Label("Settings",systemImage:"gearshape").font(.system(size:12,weight:.medium)).foregroundStyle(model.page == "Settings" ? CenterTheme.accent:CenterTheme.muted).frame(maxWidth:.infinity,alignment:.leading).padding(12) }.buttonStyle(PressFeedbackStyle()).padding(.bottom,16)
            VStack(alignment:.leading,spacing:12) {
                HStack { Image(systemName:"circle.hexagongrid").foregroundStyle(CenterTheme.accent);Text("HACKINFX CORE").font(.system(size:8,weight:.semibold,design:.monospaced)).tracking(1) }
                Text(center.online ? "Local engine online" : "Core offline").font(.system(size:12,weight:.medium))
                HStack(spacing:6) { Circle().fill(center.online ? CenterTheme.accent : .orange).frame(width:5,height:5);Text("LOCAL ONLY · x86-64").font(.system(size:7,design:.monospaced)).foregroundStyle(CenterTheme.muted) }
            }.padding(15).frame(maxWidth:.infinity,alignment:.leading).background(CenterTheme.elevated.opacity(0.6)).clipShape(RoundedRectangle(cornerRadius:14))
            HStack { Text("2.4.0");Spacer();Text("LOCAL RGB") }.font(.system(size:7,weight:.medium,design:.monospaced)).tracking(1).foregroundStyle(CenterTheme.muted).padding(.top,19)
        }.onChange(of:model.page) { _,page in if ["Studio","Hardware","Credits"].contains(page) { advanced=true } }.padding(22).frame(width:216).frame(maxHeight:.infinity).background(CenterTheme.background).animation(reduceMotion ? nil : .easeInOut(duration:0.22),value:model.page)
    }
}

private struct CenterDeviceCard:View {
    @ObservedObject var center:CenterModel
    let device:CenterDevice
    @State private var hovered=false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var body:some View {
        Button { center.toggle(device) } label: {
            VStack(alignment:.leading,spacing:17) {
                HStack { ZStack { RoundedRectangle(cornerRadius:13).fill(CenterTheme.aqua.opacity(0.07)).frame(width:46,height:46);Image(systemName:device.symbol).font(.system(size:23,weight:.light)).foregroundStyle(device.controllable ? CenterTheme.accent : CenterTheme.muted) };Spacer();Image(systemName:!device.controllable ? "info.circle" : center.selected.contains(device.id) ? "checkmark.circle.fill" : "circle").foregroundStyle(center.selected.contains(device.id) ? CenterTheme.accent : CenterTheme.muted.opacity(0.4)) }
                VStack(alignment:.leading,spacing:5) { Text(device.name).font(.system(size:13,weight:.semibold)).lineLimit(2).frame(height:34,alignment:.topLeading);Text(device.vendor.isEmpty ? device.categoryLabel : device.vendor+" · "+device.categoryLabel).font(.system(size:10)).foregroundStyle(CenterTheme.muted).lineLimit(1) }
                HStack { CenterBadge(text:device.controllable ? "Ready" : device.status.replacingOccurrences(of:"-",with:" "),good:device.controllable);Spacer();if device.led_count>0 { Text(device.lightCountLabel).font(.system(size:9,design:.monospaced)).foregroundStyle(CenterTheme.muted) } }
                if let output=center.state.sync?.outputs?[device.id],center.state.running,!(["static","gradient"].contains(center.state.scene.mode)) { HStack { Text(String(format:"%.1f FPS",output.fps)).foregroundStyle(CenterTheme.aqua);Spacer();Text(String(format:"%.1f ms jitter",output.jitter_ms ?? 0)).foregroundStyle(CenterTheme.muted) }.font(.system(size:9,design:.monospaced)) }
                Text(device.backend == "openrgb" ? "OpenRGB bridge" : device.backend == "native" ? "Native NVIDIA driver" : device.backend == "native-ram" ? "Native Corsair / SMBus" : device.backend == "native-usb" ? "Native USB / HID" : "No lighting driver attached").font(.system(size:9)).foregroundStyle(CenterTheme.muted)
            }.padding(19).frame(maxWidth:.infinity,alignment:.leading).background(center.selected.contains(device.id) ? CenterTheme.accent.opacity(0.045) : CenterTheme.surface).clipShape(RoundedRectangle(cornerRadius:17)).overlay(RoundedRectangle(cornerRadius:17).stroke(center.selected.contains(device.id) ? CenterTheme.accent.opacity(0.5) : .white.opacity(0.065),lineWidth:1))
        }.buttonStyle(PressFeedbackStyle()).offset(y:hovered && !reduceMotion ? -3:0).shadow(color:CenterTheme.accent.opacity(hovered ? 0.06:0),radius:16,y:6).onHover { hovered=$0 }.animation(reduceMotion ? nil:.spring(duration:0.25,bounce:0.15),value:hovered).animation(reduceMotion ? nil:.spring(duration:0.28,bounce:0.15),value:center.selected.contains(device.id)).help(device.detail).contextMenu { Button("Device details") { center.activeDevice=device } }
    }
}

struct CenterWorkspace:View {
    @ObservedObject var center:CenterModel
    let page:String
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Namespace private var effectSelection
    @State private var galleryPresented=false
    @State private var dragLocations:[String:CGPoint] = [:]
    var body:some View {
        VStack(alignment:.leading,spacing:24) {
            if page == "Overview" { overview }
            else if page == "Devices" { devices }
            else if page == "Effects" || page == "Scenes" { EffectGallery(center:center) }
            else if page == "Canvas" || page == "Layout" { layout }
            else { connections }
            if !center.error.isEmpty { CenterPanel { HStack { Label(center.error,systemImage:"exclamationmark.triangle").font(.system(size:12)).foregroundStyle(.orange).textSelection(.enabled);Spacer();Button { center.error="" } label: { Image(systemName:"xmark") }.help("Dismiss error") } } }
            if !center.state.errors.isEmpty { DisclosureGroup("Connection & device details") { ForEach(Array(center.state.errors.enumerated()),id:\.offset) { _,value in Text(value).font(.system(size:10,design:.monospaced)).foregroundStyle(CenterTheme.muted).textSelection(.enabled) } } }
        }.animation(reduceMotion ? nil:.smooth(duration:0.24),value:center.filter).buttonStyle(CenterSecondaryStyle()).foregroundStyle(Color(red:0.91,green:0.94,blue:0.93)).sheet(item:$center.activeDevice) { device in CenterDeviceInspector(center:center,device:device) }
    }
    private var overview:some View {
        VStack(alignment:.leading,spacing:22) {
            HStack(alignment:.top) {
                CenterHeading(eyebrow:"Your workspace",title:"Lighting",subtitle:"One place for your setup. Every adjustment goes live.")
                Spacer();CenterBadge(text:center.online ? "Live control":"Connecting",good:center.online)
            }
            lightingControls
            HStack(spacing:14) { Label("Output",systemImage:"speedometer").foregroundStyle(CenterTheme.aqua);Picker("Target output rate",selection:$center.scene.fps) { Text("20 FPS").tag(20.0);Text("30 FPS").tag(30.0);Text("60 FPS").tag(60.0) }.labelsHidden().frame(width:100);Text(center.scene.sync_policy == "adaptive" ? "Adaptive pacing · each device reports its achieved rate" : "Lockstep · group follows the slowest device").foregroundStyle(CenterTheme.muted);Spacer() }.font(.system(size:10)).padding(14).background(CenterTheme.elevated.opacity(0.5)).clipShape(RoundedRectangle(cornerRadius:12))
            HStack {
                VStack(alignment:.leading,spacing:5) { Text("Connected lighting").font(.system(size:17,weight:.semibold));Text("\(center.controllable.count) ready · \(center.selected.count) selected").font(.system(size:11)).foregroundStyle(CenterTheme.muted) }
                Spacer();Button(center.busy ? "Discovering…":"Rediscover",action:center.discover).disabled(center.busy || !center.online)
                if !center.online { Button("Start Core",action:center.start) }
            }
            grid(center.visible.filter { $0.controllable }.sorted { $0.name.localizedStandardCompare($1.name) == .orderedAscending })
            if center.controllable.isEmpty { emptyState }
            if center.state.devices.contains(where:{ !$0.controllable && $0.driver != nil }) {
                Label("Some devices need setup. Open Devices → Needs attention for details.",systemImage:"info.circle").font(.system(size:11)).foregroundStyle(CenterTheme.muted)
            }
        }
    }
    private func metric(_ title:String,value:String,symbol:String)->some View { CenterPanel { HStack(alignment:.top) { VStack(alignment:.leading,spacing:10) { Text(title).font(.system(size:10)).foregroundStyle(CenterTheme.muted);Text(value).font(.system(size:25,weight:.medium,design:.rounded)) };Spacer();Image(systemName:symbol).foregroundStyle(CenterTheme.aqua) } } }
    private func grid(_ devices:[CenterDevice])->some View { LazyVGrid(columns:[GridItem(.adaptive(minimum:210),spacing:14)],spacing:14) { ForEach(devices) { device in CenterDeviceCard(center:center,device:device) } } }
    private var emptyState:some View { CenterPanel { VStack(alignment:.leading,spacing:12) { Image(systemName:"cable.connector").font(.system(size:25,weight:.light)).foregroundStyle(CenterTheme.aqua);Text("Connect your lighting hardware").font(.headline);Text("HackinFX starts its bundled OpenRGB engine and discovers native GPU, USB/HID and memory devices. Inventory-only entries remain visible for diagnostics.").font(.system(size:12)).foregroundStyle(CenterTheme.muted) } } }
    private var devices:some View {
        VStack(alignment:.leading,spacing:22) {
            CenterHeading(eyebrow:"Device library",title:"Your devices",subtitle:"GPU, memory, USB peripherals and cooling — grouped by actual control capability.")
            HStack(spacing:8) {
                ForEach([("lighting","Lighting"),("attention","Needs attention"),("all","All devices")],id:\.0) { key,label in
                    Button { center.filter=key } label: { Text(label).foregroundStyle(center.filter == key ? CenterTheme.accent:CenterTheme.muted) }
                }
                Spacer(minLength:8)
                Menu {
                    ForEach([("gpu","GPU"),("dram","Memory"),("keyboard","Keyboards"),("mouse","Mice"),("cooler","Cooling"),("mainboard","Mainboards"),("controller","Controllers"),("usb","Other USB")],id:\.0) { key,label in Button(label) { center.filter=key } }
                } label: { Label(["gpu":"GPU","dram":"Memory","keyboard":"Keyboards","mouse":"Mice","cooler":"Cooling","mainboard":"Mainboards","controller":"Controllers","usb":"Other USB"][center.filter] ?? "Category",systemImage:"line.3.horizontal.decrease") }.fixedSize()
                Button("Refresh",action:center.discover).disabled(center.busy || !center.online)
            }

            grid(center.visible)
            if center.visible.isEmpty { emptyState }
            Text("Select devices to control together. Click an unavailable device for setup details.").font(.system(size:11)).foregroundStyle(CenterTheme.muted)
        }
    }
    private func sceneColor(_ index:Int)->Binding<Color> { Binding(get:{ let hex=center.scene.palette[min(index,center.scene.palette.count-1)];let rgb=UInt32(hex,radix:16) ?? 0;return Color(red:Double((rgb>>16)&255)/255,green:Double((rgb>>8)&255)/255,blue:Double(rgb&255)/255) },set:{ value in while center.scene.palette.count<=index { center.scene.palette.append(center.scene.palette.last ?? "ffffff") };let c=NSColor(value).usingColorSpace(.sRGB) ?? .white;center.scene.palette[index]=[c.redComponent,c.greenComponent,c.blueComponent].map { String(format:"%02x",Int(($0*255).rounded())) }.joined() }) }
    private var lightingControls:some View {
        CenterPanel {
                VStack(alignment:.leading,spacing:20) {
                    CenterScenePreview(scene:center.scene)
                    HStack(spacing:12) {
                        Menu {
                            ForEach(EffectLibrary.catalog.categories,id:\.self) { category in
                                Menu(category) { ForEach(EffectLibrary.catalog.effects.filter {$0.category==category}) { effect in Button(effect.name) { center.scene.mode=effect.id } } }
                            }
                        } label: { Label(EffectLibrary.effect(center.scene.mode)?.name ?? center.scene.mode.capitalized,systemImage:EffectLibrary.effect(center.scene.mode)?.symbol ?? "sparkles") }
                        Spacer();Button { galleryPresented=true } label: { Label("Browse 40 effects",systemImage:"square.grid.2x2") }
                    }
                    if EffectLibrary.effect(center.scene.mode)?.colors != false { HStack { ForEach(0..<min(4,center.scene.palette.count),id:\.self) { i in ColorPicker("Color \(i+1)",selection:sceneColor(i),supportsOpacity:false) };Spacer() }.font(.system(size:10)) }
                    HStack { Text("Brightness").frame(width:75,alignment:.leading);Slider(value:$center.scene.brightness,in:0...100);Text("\(Int(center.scene.brightness))%").monospacedDigit().frame(width:40) }.font(.system(size:11)).foregroundStyle(CenterTheme.muted)
                    if !["static","gradient"].contains(center.scene.mode) { HStack { Text("Speed").frame(width:75,alignment:.leading);Slider(value:$center.scene.speed,in:1...100);Text("\(Int(center.scene.speed))%").monospacedDigit().frame(width:40) }.font(.system(size:11)).foregroundStyle(CenterTheme.muted) }
                    if !["static","spectrum","breathing","color shift","pulse","heartbeat"].contains(center.scene.mode) { Picker("Direction",selection:$center.scene.axis) { Text("Horizontal").tag("x");Text("Vertical").tag("y") }.pickerStyle(.segmented) }
                    HStack(spacing:10) {
                        Label(center.liveStatus,systemImage:"bolt.fill").font(.system(size:10)).foregroundStyle(center.error.isEmpty ? CenterTheme.aqua:.orange)
                        Spacer();Button("Pause animation",action:center.stop).disabled(!center.state.running || center.busy)
                        Button("Lights off",action:center.blackout).disabled(center.selected.isEmpty)
                    }
                    if !center.sceneCompatible && !center.selected.isEmpty { Text("Devices that cannot play this effect keep their last color. Choose Static to control all ready devices.").font(.system(size:11)).foregroundStyle(.orange) }
                    if center.chosen.contains(where:{($0.onboard_modes ?? []).contains(center.scene.mode)}) { Text("Onboard effects use their own clocks. Use Canvas with shared-clock streaming devices for synchronized effects.").font(.system(size:10)).foregroundStyle(CenterTheme.muted) }

                }
            }.animation(reduceMotion ? nil:.smooth(duration:0.25),value:center.scene.mode).sheet(isPresented:$galleryPresented) {
                VStack(spacing:0) { HStack { Text("HackinFX / Effects").font(.system(size:11,design:.monospaced)).foregroundStyle(CenterTheme.muted);Spacer();Button("Done") { galleryPresented=false } }.padding(20);Divider();ScrollView { EffectGallery(center:center).padding(28) } }.frame(minWidth:1000,idealWidth:1120,minHeight:760,idealHeight:860).background(CenterTheme.background).preferredColorScheme(.dark)
            }
    }
    private var layout:some View {
        VStack(alignment:.leading,spacing:22) {
            CenterHeading(eyebrow:"Spatial lighting",title:"Canvas",subtitle:"Arrange your setup in one shared effect space. Move devices without resetting the animation clock.")
            CenterPanel { VStack(alignment:.leading,spacing:12) {
                Toggle("Shared effect timeline",isOn:$center.scene.synchronized).toggleStyle(.switch)
                Picker("Output policy",selection:$center.scene.sync_policy) { Text("Adaptive · keep fast devices smooth").tag("adaptive");Text("Lockstep · wait for every device").tag("lockstep") }.pickerStyle(.segmented)
                HStack { Text("Target frame rate");Picker("Target frame rate",selection:$center.scene.fps) { Text("20 FPS").tag(20.0);Text("30 FPS").tag(30.0);Text("60 FPS").tag(60.0) }.labelsHidden();Spacer();Text("Actual rates depend on each transport").foregroundStyle(CenterTheme.muted) }.font(.system(size:11))
                Picker("Effect mapping",selection:$center.scene.mapping) { Text("Mirror on all devices").tag("mirror");Text("Across Canvas").tag("canvas") }.pickerStyle(.segmented)
                HStack { Button("Select streaming devices") { center.selected=Set(center.controllable.filter { $0.direct }.map { $0.id }) };Spacer();Text("Shared clock · measured device FPS").font(.system(size:10,design:.monospaced)).foregroundStyle(CenterTheme.aqua) }
                Text("Adaptive output keeps one bounded frame in flight per device and samples a shared timeline using measured command latency. Slow outputs do not stall fast ones. Lockstep waits for the whole group. Hardware buffering still affects visible timing.").font(.system(size:11)).foregroundStyle(CenterTheme.muted)
            } }
            GeometryReader { geometry in
                ZStack {
                    RoundedRectangle(cornerRadius:20).fill(CenterTheme.surface)
                    Path { path in for x in stride(from:CGFloat(0),through:geometry.size.width,by:32) { path.move(to:CGPoint(x:x,y:0));path.addLine(to:CGPoint(x:x,y:geometry.size.height)) };for y in stride(from:CGFloat(0),through:geometry.size.height,by:32) { path.move(to:CGPoint(x:0,y:y));path.addLine(to:CGPoint(x:geometry.size.width,y:y)) } }.stroke(.white.opacity(0.025),lineWidth:1)
                    ForEach(center.controllable.filter { !center.scene.synchronized || $0.direct }) { device in
                        let p=center.state.layout[device.id] ?? CenterPosition(x:0.5,y:0.5,width:0.22)
                        let location=dragLocations[device.id] ?? CGPoint(x:p.x*geometry.size.width,y:p.y*geometry.size.height)
                        VStack(spacing:8) { Image(systemName:device.symbol).font(.system(size:25,weight:.light));Text(device.name).font(.system(size:9,weight:.medium)).lineLimit(2).multilineTextAlignment(.center) }.foregroundStyle(CenterTheme.accent).padding(12).frame(width:122,height:85).background(CenterTheme.background).clipShape(RoundedRectangle(cornerRadius:14)).overlay(RoundedRectangle(cornerRadius:14).stroke(CenterTheme.accent.opacity(0.25),lineWidth:1)).position(x:max(65,min(geometry.size.width-65,location.x)),y:max(50,min(geometry.size.height-50,location.y))).gesture(DragGesture(coordinateSpace:.named("lighting-canvas")).onChanged { value in dragLocations[device.id]=value.location }.onEnded { value in dragLocations.removeValue(forKey:device.id);center.move(device.id,x:Double(value.location.x/geometry.size.width),y:Double(value.location.y/geometry.size.height)) })
                    }
                    if center.controllable.isEmpty { Text("Discover and confirm a controllable device first").font(.system(size:12)).foregroundStyle(CenterTheme.muted) }
                }.coordinateSpace(name:"lighting-canvas").clipShape(RoundedRectangle(cornerRadius:20))
            }.frame(height:560)
            Text("Horizontal placement drives left-to-right waves and gradients. LED strip order is used within each device; reported keyboard/panel coordinates are used when available. Unique device placement is saved locally. Identical devices need manual placement after rediscovery.").font(.system(size:11)).foregroundStyle(CenterTheme.muted)
        }
    }
    private var connections:some View {
        VStack(alignment:.leading,spacing:22) {
            CenterHeading(eyebrow:"Preferences",title:"Settings",subtitle:"Updates, startup behavior and device connections.")
            CenterPanel { VStack(alignment:.leading,spacing:14) {
                HStack { Label("Software Update",systemImage:"arrow.down.circle").font(.headline);Spacer();Text(Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "2.4.0").font(.system(size:12,design:.monospaced)).foregroundStyle(CenterTheme.muted) }
                Toggle("Check automatically at launch",isOn:$center.automaticUpdates).toggleStyle(.switch)
                Text(center.updateMessage).font(.system(size:12)).foregroundStyle(CenterTheme.muted).textSelection(.enabled)
                HStack { Button(center.checkingUpdates ? "Checking…":"Check for Updates",action:center.checkForUpdates).disabled(center.checkingUpdates);if let url=center.updateURL { Link("View release",destination:url) } }
            } }
            CenterPanel { VStack(alignment:.leading,spacing:12) {
                Toggle("Launch at login",isOn:Binding(get:{center.loginEnabled},set:{center.setLaunchAtLogin($0)})).toggleStyle(.switch)
                Text(center.loginMessage).font(.system(size:11)).foregroundStyle(CenterTheme.muted)
                Button("Open Login Items") { SMAppService.openSystemSettingsLoginItems() }
                Label("Startup & live control",systemImage:"sun.max").font(.headline);Text("On launch, ready devices receive mint Twinkle at 65% speed. RAM stays untouched until you explicitly probe and select its DIMMs. Rediscovery keeps the current colors. Color and effect changes are sent automatically to selected compatible devices.").font(.system(size:12)).foregroundStyle(CenterTheme.muted) } }
            CenterPanel { VStack(alignment:.leading,spacing:12) {
                Label("Nanoleaf Shapes",systemImage:"triangle").font(.headline)
                Text("Find Shapes Triangles on your local network, select your controller, then hold its power button for 5–7 seconds until flashing and click Pair Shapes within 30 seconds.").font(.system(size:12)).foregroundStyle(CenterTheme.muted)
                HStack { Button("Find Nanoleaf",action:center.findNanoleaf).disabled(center.busy || !center.online)
                    if let candidates=center.state.nanoleaf_candidates,!candidates.isEmpty {
                        Picker("Controller",selection:$center.nanoleafAddress) { ForEach(candidates) { candidate in Text(candidate.name).tag(candidate.address) } }.labelsHidden()
                        Button("Pair Shapes",action:center.pairNanoleaf).disabled(center.busy || center.nanoleafAddress.isEmpty)
                    }
                }
                Text("Pairing stores a private local token and reads the real panel layout. Select the panels in Lighting to start control. Streaming uses 10 Hz with panel interpolation; it does not change saved Nanoleaf scenes.").font(.system(size:11)).foregroundStyle(CenterTheme.muted)
            } }
            DisclosureGroup("Device connections & advanced details") {
            CenterPanel { VStack(alignment:.leading,spacing:16) { HStack { Label("Bundled OpenRGB 1.1",systemImage:"point.3.connected.trianglepath.dotted").font(.headline);Spacer();CenterBadge(text:center.state.bridge,good:center.state.bridge == "connected") };Text("LOCAL ENGINE").font(.system(size:20,weight:.medium,design:.monospaced));Text("OpenRGB starts and stops with HackinFX. Its macOS device drivers are included; no separate OpenRGB installation is required. Direct-mode devices join live scenes. Native adapters own their matching hardware to avoid duplicate writes.").font(.system(size:12)).foregroundStyle(CenterTheme.muted);CenterAction(title:"Rediscover devices",symbol:"arrow.clockwise",action:center.discover).disabled(center.busy || !center.online) } }
            CenterPanel { VStack(alignment:.leading,spacing:14) { HStack { Label("Native NVIDIA",systemImage:"cpu").font(.headline);Spacer();CenterBadge(text:"Native driver") };Text("The existing NullMoth/NVRM controller paths remain available in GPU Lab. A local visual confirmation is required before Core can include a GPU in a scene.").font(.system(size:12)).foregroundStyle(CenterTheme.muted);Text("Native HID LampArray covers compatible keyboards, mainboards and lighting controllers. ASUS Spatha X and NZXT Kraken X2/M2 have dedicated lighting paths. Other supported USB families use the bundled OpenRGB engine. DRAM access depends on the chipset, module and required macUSPCIO driver.").font(.system(size:11)).foregroundStyle(CenterTheme.muted) } }
            CenterPanel { VStack(alignment:.leading,spacing:12) { Label("Private local Core",systemImage:"lock.shield").font(.headline);Text("The API uses a per-process credential and binds only to 127.0.0.1. No LAN listener, cloud account or Android access is enabled. Saved scenes stay in Documents/HackinFX. The engine stops when HackinFX quits.").font(.system(size:12)).foregroundStyle(CenterTheme.muted) } }
            }
        }
    }
}

private struct CenterDeviceInspector:View {
    @ObservedObject var center:CenterModel
    let device:CenterDevice
    @Environment(\.dismiss) var dismiss
    var body:some View {
        ScrollView { VStack(alignment:.leading,spacing:19) {
            HStack { Image(systemName:device.symbol).font(.system(size:30,weight:.light)).foregroundStyle(CenterTheme.accent);Spacer();CenterBadge(text:device.backend,good:device.controllable) }
            Text(device.name).font(.system(size:23,weight:.semibold,design:.rounded))
            Text(device.vendor+" · "+device.categoryLabel).foregroundStyle(CenterTheme.muted)
            Divider()
            if let positions=device.led_positions,!positions.isEmpty { VStack(alignment:.leading,spacing:8) { Text("MAPPED LED POSITIONS · SCHEMATIC").font(.system(size:8,design:.monospaced)).foregroundStyle(CenterTheme.muted);GeometryReader { geometry in ZStack { ForEach(Array(positions.enumerated()),id:\.offset) { _,point in RoundedRectangle(cornerRadius:2).fill(CenterTheme.accent.opacity(0.75)).frame(width:10,height:10).position(x:10+point.x*(geometry.size.width-20),y:10+point.y*(geometry.size.height-20)) } } }.frame(height:120) }.padding(14).background(CenterTheme.background).clipShape(RoundedRectangle(cornerRadius:12)) }
            if let usb=device.usb_id { Text("USB ID · "+usb).font(.system(size:11,design:.monospaced)).foregroundStyle(CenterTheme.muted) }
            if let matches=device.catalog_matches,!matches.isEmpty { Text("OpenRGB identities: "+matches.joined(separator:", ")).font(.system(size:11)).foregroundStyle(CenterTheme.muted) }
            Text(device.lightCountLabel).font(.system(size:13,weight:.semibold)).foregroundStyle(CenterTheme.accent)
            if let source=device.topology_source { Text(source+(device.layout.map { " · "+$0 } ?? "")).font(.system(size:10)).foregroundStyle(CenterTheme.muted) }
            if let output=center.state.sync?.outputs?[device.id] { Text(String(format:"Output %.1f FPS · command %.2f ms · %d sent · %d busy ticks",output.fps,output.command_ms,output.frames,output.missed)).font(.system(size:10,design:.monospaced)).foregroundStyle(CenterTheme.aqua) }
            Text(device.detail).font(.system(size:12)).fixedSize(horizontal:false,vertical:true).textSelection(.enabled)
            if let modes=device.static_modes,!modes.isEmpty { Text("Supported scenes: "+(device.direct ? ["Static","Gradient","Spectrum","Breathing","Wave","Aurora","Comet","Twinkle","Color shift"] : modes.map { $0.capitalized }).joined(separator:", ")).font(.system(size:11)).foregroundStyle(CenterTheme.muted) }
            if device.driver == "corsair-ddr5-i801" {
                HStack { Button("Probe RAM RGB") { center.probeRAM();dismiss() }.disabled(center.busy || !center.online || device.status.hasPrefix("unsupported"));Button("RAM setup guide") { if let path=Bundle.main.resourceURL?.appendingPathComponent("Source/docs/RAM-SETUP.md") { NSWorkspace.shared.open(path) } } }
                Text("The initial RAM adapter requires a separately installed macUSPCIO driver and exact Corsair identity/CRC checks. The app never changes OpenCore or installs a kernel extension.").font(.system(size:10)).foregroundStyle(CenterTheme.muted)
            }
            Label(device.direct ? (device.color_scope == "whole-device" ? "Host-streamed whole-device color" : device.backend == "native" ? "Host-streamed GPU color zones" : "Direct per-LED scene streaming") : device.controllable ? "Static scenes and supported native effects" : "Lighting control unavailable",systemImage:device.controllable ? "checkmark.circle" : "info.circle").font(.system(size:12)).foregroundStyle(device.controllable ? CenterTheme.accent : CenterTheme.muted)
            if let zones=device.zones,!zones.isEmpty { Text("ZONES").font(.system(size:8,design:.monospaced)).foregroundStyle(CenterTheme.muted);ForEach(Array(zones.prefix(8).enumerated()),id:\.offset) { _,zone in HStack { Text(zone.name);Spacer();Text("\(zone.led_count) LEDs").foregroundStyle(CenterTheme.muted) }.font(.system(size:11)) } }
            if let modes=device.modes,!modes.isEmpty { Text("Hardware modes: "+modes.prefix(12).map { $0.name }.joined(separator:", ")).font(.system(size:11)).foregroundStyle(CenterTheme.muted) }
            Text("Connection readiness is not a physical lighting confirmation.").font(.caption).foregroundStyle(CenterTheme.muted)
            HStack { Spacer();Button("Close") { dismiss() }.keyboardShortcut(.cancelAction) }
        }.padding(28) }.frame(width:566,height:650).background(CenterTheme.background).foregroundStyle(.white).preferredColorScheme(.dark)
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

struct PeripheralDiagnostics:View {
    @ObservedObject var center:CenterModel
    var body:some View {
        VStack(alignment:.leading,spacing:14) {
            HStack { Text("USB & lighting controllers").font(.headline);Spacer();Button(center.busy ? "Scanning…" : "Refresh peripherals",action:center.discover).disabled(center.busy || !center.online) }
            Text("Native IOKit inventory and OpenRGB identities. Refresh stops the current scene. Detection and catalog matches are separate from verified lighting control.").font(.system(size:11)).foregroundStyle(CenterTheme.muted)
            ForEach(center.state.devices.filter { $0.backend != "native" }) { device in
                HStack(alignment:.top,spacing:11) {
                    Image(systemName:device.symbol).foregroundStyle(CenterTheme.aqua).frame(width:19)
                    VStack(alignment:.leading,spacing:4) {
                        Text(device.name).font(.system(size:12,weight:.medium))
                        Text([device.vendor,device.usb_id ?? "",device.driver ?? device.backend].filter { !$0.isEmpty }.joined(separator:" · ")).font(.system(size:10,design:.monospaced)).foregroundStyle(CenterTheme.muted)
                        if device.status == "access-required" { Text(device.detail).font(.system(size:10)).foregroundStyle(.orange).fixedSize(horizontal:false,vertical:true) }
                    }
                    Spacer();CenterBadge(text:device.status.replacingOccurrences(of:"-",with:" "),good:device.controllable)
                }.padding(.vertical,6)
            }
            if center.state.devices.isEmpty { Text("No Core inventory yet. Start Core and discover devices in Overview.").font(.system(size:11)).foregroundStyle(CenterTheme.muted) }
        }.padding(22).background(CenterTheme.surface).clipShape(RoundedRectangle(cornerRadius:16))
    }
}
