// SPDX-License-Identifier: GPL-2.0-or-later
// HackinFX — by aleopho. See LICENSE.md and COPYING.
import AppKit
import SwiftUI
import UniformTypeIdentifiers

private let ink = Color(red: 0.075, green: 0.08, blue: 0.075)
private let panel = Color(red: 0.105, green: 0.115, blue: 0.105)
private let accent = Color(red: 0.73, green: 0.84, blue: 0.48)
private let muted = Color(red: 0.57, green: 0.60, blue: 0.53)

enum Lighting: String, CaseIterable, Identifiable {
    case solid = "Static", gradient = "Gradient", cycle = "Spectrum", breath = "Breathing", wave = "Wave"
    var id: String { rawValue }
    var backend: String { switch self { case .solid: return "static"; case .gradient: return "gradient"; case .cycle: return "cycle"; case .breath: return "breath"; case .wave: return "wave" } }
    var symbol: String { switch self { case .solid: return "circle.fill"; case .gradient: return "slider.horizontal.3"; case .cycle: return "circle.lefthalf.filled"; case .breath: return "waveform.path"; case .wave: return "water.waves" } }
    var detail: String { switch self {
    case .solid: return "One color across the card. Verified on the tested PNY profile."
    case .gradient: return "A color blend across three controller zones. Appearance depends on the card."
    case .cycle: return "The onboard controller cycles through the color spectrum."
    case .breath: return "The onboard controller pulses the selected color."
    case .wave: return "The onboard controller generates a moving color effect."
    } }
}

final class Model: ObservableObject {
    @Published var effect = Lighting.solid
    @Published var colorA = Color(red: 0.73, green: 0.84, blue: 0.48)
    @Published var colorB = Color(red: 0.20, green: 0.45, blue: 1)
    @Published var colorC = Color(red: 0.75, green: 0.22, blue: 0.95)
    @Published var brightness = 50.0
    @Published var speed = 50.0
    @Published var busy = false
    @Published var message = "Ready. Changes are sent only when you click Apply."
    @Published var lastSuccess: Bool? = nil
    @Published var lastReport: URL?
    @Published var page = "Hardware"
    private var initialHardwareCheck = true
    @Published var scanning = false
    @Published var scanSummary = "No scan yet. Read-only inventory; no lighting commands."
    @Published var adapters: [GPUInfo] = []
    @Published var scanJSON = ""
    @Published var scanReport: URL?
    @Published var sessionEvents: [[String: String]] = []
    @Published var configurationStatus = "checking"
    @Published var configurationReason = "Checking hardware configuration…"
    @Published var boardLabel = ""
    @Published var observedBehavior = ""
    @Published var setupState = "required"
    @Published var setupTesting = false
    @Published var testTransportOK = false
    @Published var setupMessage = "Confirm lighting before saving a local profile."
    @Published var showReportPreview = false
    @Published var showSetupWizard = false
    @Published var manualVendor = ""
    @Published var manualModel = ""
    var detectedGPUName = ""
    var identitySource = "detected"
    var needsIdentity: Bool { ["display adapter","display","unknown","graphics device","nvidia graphics device","no display adapter detected"].contains(currentGPUName.lowercased()) || currentGPUName.isEmpty || currentGPUVendor.isEmpty || currentGPUVendor == "Unknown vendor" || currentBoardVendor.isEmpty || currentBoardVendor.hasPrefix("PCI ") || currentBoardVendor == "Unknown" || currentBoardVendor == "Unknown board vendor" }
    func saveIdentity() -> Bool {
        let vendor = manualVendor.trimmingCharacters(in:.whitespacesAndNewlines)
        let name = manualModel.trimmingCharacters(in:.whitespacesAndNewlines)
        guard !vendor.isEmpty && !name.isEmpty && vendor.utf16.count <= 120 && name.utf16.count <= 120 && vendor.rangeOfCharacter(from:.controlCharacters) == nil && name.rangeOfCharacter(from:.controlCharacters) == nil else { setupMessage = "Enter the board manufacturer and exact card model before confirming."; return false }
        if vendor != currentBoardVendor || name != currentGPUName {
            currentBoardVendor = vendor; currentGPUName = name; identitySource = "user-supplied"
            if let h = verifiedHardware { verifiedHardware = VerifiedHardware(vendor_id:h.vendor_id,device_id:h.device_id,subsystem_vendor_id:h.subsystem_vendor_id,subsystem_id:h.subsystem_id,gpu_name:name,gpu_vendor:h.gpu_vendor,board_vendor:vendor,profile:h.profile) }
        }
        return true
    }
    @Published var submissionMessage = ""
    @Published var submitting = false
    @Published var launching = true
    @Published var currentGPUName = "Detecting GPU…"
    @Published var currentGPUVendor = ""
    @Published var currentBoardVendor = ""
    @Published var compatibilityRows: [CompatibilityRow] = []
    @Published var contributeConfirmation = (UserDefaults.standard.object(forKey: "ContributeHardwareConfirmations") as? Bool ?? true) { didSet { UserDefaults.standard.set(contributeConfirmation, forKey: "ContributeHardwareConfirmations") } }
    @Published var communityStatus = ""
    @Published var uploadingCommunity = false
    var verifiedHardware: VerifiedHardware?
    let verificationStore = VerificationStore(directory: FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("HackinFX", isDirectory: true))
    let testPlan: [(String, String, String?, Double)] = [
        ("RED", "static", "ff0000", 2), ("GREEN", "static", "00ff00", 2), ("BLUE", "static", "0000ff", 2),
        ("GRADIENT", "gradient", nil, 4), ("SPECTRUM", "cycle", nil, 5), ("BREATHING", "breath", nil, 5), ("WAVE", "wave", nil, 5)
    ]
    init() { reloadCompatibility(); let count = verificationStore.pending().count; if count > 0 { communityStatus = "\(count) community confirmation(s) queued locally." } }
    var fingerprint = ""
    var confirmationSource = "none"
    var submissionID = UUID().uuidString
    var draftURL: URL?
    var feedbackSave: DispatchWorkItem?
    var testStep = 0
    var lightingEvidence: [[String: Any]] = []
    var reportPreview: String { String(data: (try? JSONSerialization.data(withJSONObject: diagnosticPayload(), options: [.prettyPrinted, .sortedKeys])) ?? Data(), encoding: .utf8) ?? "" }
    var canControlLighting: Bool { configurationStatus == "supported" && setupState == "confirmed" }
    var reportEndpoint: URL? {
        guard let file = Bundle.main.url(forResource: "report-endpoint", withExtension: "json"), let bytes = try? Data(contentsOf: file), let json = (try? JSONSerialization.jsonObject(with: bytes)) as? [String: String], let text = json["url"], let url = URL(string: text), url.scheme == "https", url.host != nil else { return nil }
        return url
    }
    var working: Bool { busy || scanning || setupTesting || submitting || launching }
    func record(_ action: String, _ outcome: String) {
        sessionEvents.append(["time": ISO8601DateFormatter().string(from: Date()), "action": action, "outcome": outcome])
        if sessionEvents.count > 100 { sessionEvents.removeFirst() }
    }
    func hex(_ color: Color) -> String {
        let c = NSColor(color).usingColorSpace(.sRGB) ?? .white
        return [c.redComponent, c.greenComponent, c.blueComponent].map { String(format: "%02x", Int(($0 * 255).rounded())) }.joined()
    }
    func apply(off: Bool = false, testHex: String? = nil, testEffect: String? = nil) {
        guard !busy && !scanning && !submitting && (!setupTesting || testEffect != nil) else { return }
        guard canControlLighting || (testEffect != nil && configurationStatus == "supported") else { page = "Hardware"; message = configurationReason; return }
        busy = true; lastSuccess = nil
        let selected = testEffect ?? (off ? "off" : effect.backend)
        message = "Applying \(off ? "Off" : effect.rawValue) …"
        let resource = Bundle.main.resourceURL!
        let reports = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("HackinFX/Reports", isDirectory: true)
        do { try FileManager.default.createDirectory(at: reports, withIntermediateDirectories: true) }
        catch { finish(false, "Report directory: \(error.localizedDescription)"); return }
        let output = reports.appendingPathComponent("rgb-\(UUID().uuidString).json")
        lastReport = output
        let args = ["-B", resource.appendingPathComponent("rgb.py").path, "--apply", "--port", "1", "--led", "all", "--effect", selected, "--color", testEffect != nil ? (testHex ?? "ff0000") : hex(colorA), "--colors", testEffect != nil ? "ff0000,00ff00,0000ff" : [hex(colorA),hex(colorB),hex(colorC)].joined(separator: ","), "--brightness", testEffect != nil ? "128" : String(Int((brightness * 255 / 100).rounded())), "--speed", testEffect != nil ? "50" : String(Int(speed)), "--output", output.path]
        DispatchQueue.global(qos: .userInitiated).async {
            let task = Process(); let pipe = Pipe()
            task.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
            task.arguments = args; task.standardOutput = pipe; task.standardError = pipe
            do {
                try task.run()
                let watchdog = DispatchWorkItem { if task.isRunning { task.terminate() } }
                DispatchQueue.global().asyncAfter(deadline:.now()+30,execute:watchdog)
                defer { watchdog.cancel() }
                let text = pipe.fileHandleForReading.readDataToEndOfFile()
                task.waitUntilExit()
                let success = task.terminationStatus == 0
                var result = success ? "Applied. Check the lighting on your GPU." : "Request failed. See the report for details."
                if !success {
                    if let data = try? Data(contentsOf: output), let json = try? JSONSerialization.jsonObject(with: data) as? [String:Any], let error = json["error"] as? String { result = error }
                    else if let detail = String(data: text, encoding: .utf8) { result = String(detail.prefix(400)) }
                }
                let finalMessage = result
                DispatchQueue.main.async { self.finish(success, finalMessage) }
            } catch { DispatchQueue.main.async { self.finish(false, error.localizedDescription) } }
        }
    }
    func finish(_ success: Bool, _ text: String) {
        busy = false; lastSuccess = success; message = text
        record("lighting", success ? "accepted" : "failed")
        if let url = lastReport, let bytes = try? Data(contentsOf: url), let report = (try? JSONSerialization.jsonObject(with: bytes)) as? [String: Any] {
            lightingEvidence.append(report)
            if lightingEvidence.count > 12 { lightingEvidence.removeFirst() }
        }
        if setupTesting {
            if !success { setupTesting = false; setupState = "failed"; UserDefaults.standard.set(fingerprint, forKey: "FailedLightingSetupFingerprint"); setupMessage = "The lighting command failed. Describe what happened below."; saveTroubleshooting(); return }
            testStep += 1
            if testStep == testPlan.count {
                setupMessage = "Observe Wave for a few seconds…"
                DispatchQueue.main.asyncAfter(deadline: .now() + testPlan[testStep - 1].3) {
                    guard self.setupTesting else { return }
                    self.setupTesting = false; self.testTransportOK = true; self.setupState = "awaiting-confirmation"
                    self.setupMessage = "Did RGB, Gradient, Spectrum, Breathing and Wave all work? Wave keeps running until you apply another mode."
                    self.saveTroubleshooting()
                }
            }
            else { DispatchQueue.main.asyncAfter(deadline: .now() + testPlan[testStep - 1].3) { self.runTestStep() } }
        }
    }
    func startSetupTest() {
        guard !working && configurationStatus == "supported" else { return }
        showSetupWizard = true; page = "Hardware"; setupTesting = true; testTransportOK = false; testStep = 0; setupState = "testing"
        lightingEvidence = []; draftURL = nil; confirmationSource = "current-test"; record("setup-test", "started"); runTestStep()
    }
    func runTestStep() {
        guard setupTesting else { return }
        let stage = testPlan[testStep]
        setupMessage = "Test \(testStep + 1)/\(testPlan.count): \(stage.0). Watch the card."
        apply(testHex: stage.2, testEffect: stage.1)
    }
    func confirmSetup(_ outcome: String) {
        guard !working else { return }
        if outcome == "confirmed" {
            guard testTransportOK && configurationStatus == "supported" && saveIdentity() else { return }
            guard !fingerprint.isEmpty else { setupMessage = "Visual test passed, but inventory is incomplete. Rescan before saving a reusable profile."; return }
            let profile = VerifiedSetup(fingerprint: fingerprint, confirmedAt: Date(), successfulSteps: 3, userConfirmed: true, verifiedEffects: ["static", "gradient", "cycle", "breath", "wave"])
            guard let data = try? JSONEncoder().encode(profile) else { return }
            UserDefaults.standard.set(data, forKey: "VerifiedLightingSetup")
            UserDefaults.standard.removeObject(forKey: "FailedLightingSetupFingerprint")
            showSetupWizard = false; setupState = "confirmed"; setupMessage = "Lighting confirmed. Local profile saved."; record("setup-confirmation", "confirmed"); saveTroubleshooting(); registerConfirmation(); page = "Studio"
        } else {
            setupState = outcome; UserDefaults.standard.set(fingerprint, forKey: "FailedLightingSetupFingerprint"); setupMessage = "Describe what did not work, then review the troubleshooting report."; record("setup-confirmation", outcome); saveTroubleshooting()
        }
    }
    func restoreSetup(_ report: [String: Any]) {
        fingerprint = report["configuration_fingerprint"] as? String ?? ""
        confirmationSource = "none"; testStep = 0
        testTransportOK = false
        if configurationStatus == "supported", let bytes = UserDefaults.standard.data(forKey: "VerifiedLightingSetup"), let saved = try? JSONDecoder().decode(VerifiedSetup.self, from: bytes), saved.matches(fingerprint), UserDefaults.standard.string(forKey: "FailedLightingSetupFingerprint") != fingerprint {
            setupState = "confirmed"; confirmationSource = "saved-profile"; testStep = saved.successfulSteps; setupMessage = "Saved lighting profile matches this configuration."; record("profile", "restored")
        } else { setupState = "required"; setupMessage = configurationStatus == "supported" ? "Known lighting controller. Run the short visual test to confirm your card." : "LED availability is unknown for this configuration. Submit an inventory for investigation." }
    }
    func reloadCompatibility() {
        var rows: [CompatibilityRow] = []
        if let url = Bundle.main.url(forResource: "compatibility", withExtension: "json"), let data = try? Data(contentsOf: url), let file = try? JSONDecoder().decode(CompatibilityFile.self, from: data) { rows = file.entries }
        var additions = verificationStore.load()
        if let data = UserDefaults.standard.data(forKey: "CommunityCatalog"), let catalog = try? JSONDecoder().decode(CompatibilityFile.self, from: data) { additions += catalog.entries }
        for row in additions {
            if let index = rows.firstIndex(where: { $0.hardware_key == row.hardware_key }) {
                if row.source == "Local user confirmation" { rows[index] = row }
                rows[index].confirmed_effects = Array(Set(rows[index].confirmed_effects + row.confirmed_effects)).sorted()
                rows[index].reports = max(rows[index].reports, row.reports)
                if (row.last_confirmed ?? "") > (rows[index].last_confirmed ?? "") { rows[index].last_confirmed = row.last_confirmed; rows[index].source = row.source }
            } else { rows.append(row) }
        }
        compatibilityRows = rows
    }
    func fetchCommunityCatalog() {
        guard let endpoint = reportEndpoint else { return }
        let url = endpoint.deletingLastPathComponent().appendingPathComponent("compatibility")
        URLSession.shared.dataTask(with: url) { data, response, _ in
            guard (response as? HTTPURLResponse)?.statusCode == 200, let bytes = data, bytes.count <= 524288, let catalog = try? JSONDecoder().decode(CompatibilityFile.self, from: bytes), catalog.schema_version == 1, catalog.entries.count <= 1000 else { return }
            DispatchQueue.main.async { UserDefaults.standard.set(bytes, forKey: "CommunityCatalog"); self.reloadCompatibility() }
        }.resume()
    }
    func effectIsConfirmed(_ effect: Lighting) -> Bool {
        guard let hardware = verifiedHardware else { return false }
        return compatibilityRows.contains { $0.hardware_key == hardware.key && $0.profile == hardware.profile && $0.confirmed_effects.contains(effect.backend) }
    }
    func identifyHardware(_ report: [String: Any]) {
        verifiedHardware = nil
        guard let all = report["adapters"] as? [[String: Any]], let gpu = all.first(where: { $0["nvrm_bound"] as? Bool == true }) ?? all.first else {
            currentGPUName = "No display adapter detected"; currentGPUVendor = ""; currentBoardVendor = ""; return
        }
        currentGPUName = gpu["profile_name"] as? String ?? gpu["gpu_name"] as? String ?? gpu["model"] as? String ?? "Display adapter"
        detectedGPUName = currentGPUName; identitySource = "detected"
        currentGPUVendor = gpu["vendor_name"] as? String ?? "Unknown vendor"
        currentBoardVendor = gpu["board_vendor"] as? String ?? "Unknown board vendor"
        manualVendor = currentBoardVendor.hasPrefix("PCI ") || currentBoardVendor == "Unknown board vendor" ? "" : currentBoardVendor
        manualModel = currentGPUName == "Display adapter" ? "" : currentGPUName
        if let saved = UserDefaults.standard.dictionary(forKey: "HardwareIdentity"), saved["fingerprint"] as? String == report["configuration_fingerprint"] as? String, let name = saved["name"] as? String, let vendor = saved["vendor"] as? String { currentGPUName = name; currentBoardVendor = vendor; identitySource = saved["source"] as? String ?? "user-supplied"; manualVendor = vendor; manualModel = name }
        if let ids = gpu["pci_hex"] as? [String: String], let profile = gpu["verified_profile"] as? String,
           let vendor = ids["vendor-id"], let device = ids["device-id"], let subvendor = ids["subsystem-vendor-id"], let subdevice = ids["subsystem-id"] {
            verifiedHardware = VerifiedHardware(vendor_id: vendor, device_id: device, subsystem_vendor_id: subvendor, subsystem_id: subdevice, gpu_name: currentGPUName, gpu_vendor: currentGPUVendor, board_vendor: currentBoardVendor, profile: profile)
        }
    }
    func registerConfirmation() {
        guard let hardware = verifiedHardware else { return }
        UserDefaults.standard.set(["fingerprint":fingerprint,"name":currentGPUName,"vendor":currentBoardVendor,"source":identitySource],forKey:"HardwareIdentity")
        var installationID = UserDefaults.standard.string(forKey: "CommunityInstallationID")
        if installationID == nil { installationID = UUID().uuidString; UserDefaults.standard.set(installationID!, forKey: "CommunityInstallationID") }
        let scan = diagnosticPayload()
        let runtime = scan["runtime"] as? [String: String] ?? [:]
        let drivers = scan["driver_bundles"] as? [[String: String]] ?? []
        let verification = HardwareVerification(verification_id: UUID().uuidString, installation_id: installationID!, hardware: hardware, macos: runtime["macos"] ?? "unknown", arch: runtime["arch"] ?? "unknown", driver_version: drivers.first(where: { $0["identifier"] == "com.nullmoth.NVRM" })?["version"] ?? "unknown", confirmed_effects: ["static","gradient","cycle","breath","wave"], identity_source: identitySource, detected_gpu_name: detectedGPUName, tested_steps: testPlan.count, confirmed_at: ISO8601DateFormatter().string(from: Date()))
        do {
            try verificationStore.remember(verification)
            reloadCompatibility()
            if contributeConfirmation {
                try verificationStore.enqueue(verification)
                communityStatus = reportEndpoint == nil ? "Confirmed locally. Community contribution queued until the inbox is connected." : "Community contribution queued."
                flushVerifications()
            } else { communityStatus = "Confirmed in the local compatibility database." }
        } catch { communityStatus = "Could not save the compatibility entry: \(error.localizedDescription)" }
    }
    func flushVerifications() {
        guard contributeConfirmation, !uploadingCommunity, let endpoint = reportEndpoint else { return }
        let pending = Array(verificationStore.pending().prefix(3))
        guard !pending.isEmpty else { return }
        uploadingCommunity = true
        let url = endpoint.deletingLastPathComponent().appendingPathComponent("verifications")
        func send(_ index: Int) {
            guard index < pending.count else { uploadingCommunity = false; communityStatus = "Community confirmation received."; fetchCommunityCatalog(); DispatchQueue.main.asyncAfter(deadline:.now()+65) { self.flushVerifications() }; return }
            let (file, verification) = pending[index]
            var request = URLRequest(url: url); request.httpMethod = "POST"; request.timeoutInterval = 25
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try? JSONEncoder().encode(verification)
            URLSession.shared.dataTask(with: request) { data, response, error in
                let receipt = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
                let accepted = error == nil && (response as? HTTPURLResponse)?.statusCode == 201 && receipt?["verification_id"] as? String == verification.verification_id
                DispatchQueue.main.async {
                    if accepted { try? FileManager.default.removeItem(at: file); send(index + 1) }
                    else { self.uploadingCommunity = false; self.communityStatus = "Not received yet. Saved locally; retrying automatically."; DispatchQueue.main.asyncAfter(deadline:.now()+65) { self.flushVerifications() } }
                }
            }.resume()
        }
        send(0)
    }
    func diagnosticPayload() -> [String: Any] {
        var report = (scanJSON.data(using: .utf8).flatMap { try? JSONSerialization.jsonObject(with: $0) }) as? [String: Any] ?? [:]
        report["submission_id"] = submissionID
        report["app_session_events"] = sessionEvents
        report["community_notes"] = ["exact_card_model": boardLabel, "observed_behavior": observedBehavior, "reported_board_vendor": manualVendor, "reported_exact_model": manualModel, "identity_source": identitySource]
        report["setup"] = ["outcome": setupState, "successful_test_steps": testStep, "transport_test_completed": testTransportOK, "visual_confirmation": setupState == "confirmed", "confirmation_source": confirmationSource] as [String: Any]
        report["lighting_evidence"] = lightingEvidence
        if setupState == "confirmed" { report["led_availability"] = "User-confirmed basic RGB (\(confirmationSource))" }
        return report
    }
    func saveTroubleshooting() {
        guard !scanJSON.isEmpty else { return }
        let folder = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("HackinFX/Troubleshooting", isDirectory: true)
        do {
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            let data = try JSONSerialization.data(withJSONObject: diagnosticPayload(), options: [.prettyPrinted, .sortedKeys])
            if draftURL == nil { draftURL = folder.appendingPathComponent("troubleshooting-\(UUID().uuidString).json") }
            try data.write(to: draftURL!, options: .atomic)
        } catch { submissionMessage = "Local report could not be saved: \(error.localizedDescription)" }
    }
    func reviewReport() { submissionMessage = ""; saveTroubleshooting(); showReportPreview = true }
    func feedbackChanged() {
        if observedBehavior.count > 4000 { observedBehavior = String(observedBehavior.prefix(4000)) }
        if boardLabel.count > 120 { boardLabel = String(boardLabel.prefix(120)) }
        submissionID = UUID().uuidString
        feedbackSave?.cancel()
        let work = DispatchWorkItem { self.saveTroubleshooting() }
        feedbackSave = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.7, execute: work)
    }
    func submitReport() {
        guard !working, let endpoint = reportEndpoint else { return }
        guard observedBehavior.count <= 8000 && boardLabel.count <= 8000 else { submissionMessage = "Keep each notes field below 8,000 characters, or use local export."; return }
        guard let data = try? JSONSerialization.data(withJSONObject: diagnosticPayload(), options: [.sortedKeys]), data.count <= 131072 else { submissionMessage = "Report exceeds the upload limit. Use local export."; return }
        submitting = true; submissionMessage = "Sending…"
        var request = URLRequest(url: endpoint); request.httpMethod = "POST"; request.timeoutInterval = 30
        request.setValue("application/json", forHTTPHeaderField: "Content-Type"); request.httpBody = data
        URLSession.shared.dataTask(with: request) { data, response, error in
            let http = response as? HTTPURLResponse
            let receipt = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
            let reportID = receipt?["report_id"] as? String
            DispatchQueue.main.async {
                self.submitting = false
                if error == nil, http?.statusCode == 201, let id = reportID {
                    self.submissionMessage = "Received. Report ID: \(id)"; self.record("submission", "received")
                } else { self.submissionMessage = "Report was not confirmed as received. Local export remains available."; self.record("submission", "failed") }
            }
        }.resume()
    }
    func scanHardware() {
        guard !working else { return }
        saveTroubleshooting()
        draftURL = nil; lightingEvidence = []; submissionID = UUID().uuidString
        scanning = true
        configurationStatus = "checking"
        configurationReason = "Checking hardware configuration…"
        scanJSON = ""; scanReport = nil; adapters = []
        scanSummary = "Scanning display adapters and graphics driver versions…"
        record("scan", "started")
        let resources = Bundle.main.resourceURL!
        let folder = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("HackinFX/Scans", isDirectory: true)
        do { try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true) }
        catch { scanning = false; configurationStatus = "unknown"; configurationReason = "Could not create scan directory"; page = "Hardware"; scanSummary = "Could not create scan directory."; record("scan", "directory-error"); return }
        let output = folder.appendingPathComponent("scan-\(UUID().uuidString).json")
        DispatchQueue.global(qos: .userInitiated).async {
            let process = Process(); let pipe = Pipe()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
            process.arguments = ["-B", resources.appendingPathComponent("scanner.py").path, "--output", output.path]
            process.standardOutput = pipe; process.standardError = pipe
            do {
                try process.run()
                let watchdog = DispatchWorkItem { if process.isRunning { process.terminate() } }
                DispatchQueue.global().asyncAfter(deadline:.now()+60,execute:watchdog)
                defer { watchdog.cancel() }
                _ = pipe.fileHandleForReading.readDataToEndOfFile()
                process.waitUntilExit()
                guard let data = try? Data(contentsOf: output), let report = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                    DispatchQueue.main.async { self.scanning = false; self.configurationStatus = "unknown"; self.configurationReason = "Scan produced no readable report."; self.page = "Hardware"; self.scanSummary = "Scan produced no readable report."; self.record("scan", "invalid-report") }; return
                }
                let rawAdapters = report["adapters"] as? [[String: Any]] ?? []
                let found = rawAdapters.enumerated().map { index, adapter -> GPUInfo in
                    let ids = adapter["pci_hex"] as? [String: Any] ?? [:]
                    return GPUInfo(id: index, name: adapter["profile_name"] as? String ?? adapter["gpu_name"] as? String ?? adapter["model"] as? String ?? "Display adapter", pci: "\(ids["vendor-id"] as? String ?? "????"):\(ids["device-id"] as? String ?? "????")", subsystem: "\(ids["subsystem-vendor-id"] as? String ?? "????"):\(ids["subsystem-id"] as? String ?? "????")", vendor: adapter["vendor_name"] as? String ?? "Unknown vendor", gpuType: adapter["gpu_type"] as? String ?? "Display controller", supported: adapter["rgb_support"] as? String == "verified-profile", nvrm: adapter["nvrm_bound"] as? Bool ?? false)
                }
                let compatibility = report["lighting_configuration"] as? [String: Any] ?? [:]
                let configStatus = compatibility["status"] as? String ?? "unknown"
                let configReason = compatibility["reason"] as? String ?? "Compatibility could not be determined"
                let errors = report["errors"] as? [[String: Any]] ?? []
                let raw = String(data: data, encoding: .utf8) ?? ""
                let summary = errors.isEmpty ? "Scan complete. \(found.count) display adapter(s) found." : "Scan finished with \(errors.count) query error(s). Export the report for analysis."
                DispatchQueue.main.asyncAfter(deadline:.now()+0.8) { self.configurationStatus = configStatus; self.configurationReason = configReason; self.scanJSON = raw; self.identifyHardware(report); self.restoreSetup(report); self.flushVerifications(); self.fetchCommunityCatalog(); if self.initialHardwareCheck || configStatus != "supported" { self.page = self.canControlLighting ? "Studio" : "Hardware" }; self.initialHardwareCheck = false; self.adapters = found; self.scanJSON = raw; self.scanReport = output; self.scanSummary = summary; self.scanning = false; self.record("scan", errors.isEmpty ? "completed" : "completed-with-errors"); if self.setupState == "required" && configStatus == "supported" { self.startSetupTest() } }
            } catch { DispatchQueue.main.async { self.scanning = false; self.configurationStatus = "unknown"; self.configurationReason = "Hardware check failed"; self.page = "Hardware"; self.scanSummary = "Could not start or read the scan. \(error.localizedDescription)"; self.record("scan", "failed") } }
        }
    }
    func exportDiagnostics() {
        guard !scanJSON.isEmpty else { return }
        let report = diagnosticPayload()
        let dialog = NSSavePanel()
        dialog.title = "Export hardware diagnostics"
        dialog.nameFieldStringValue = "HackinFX-hardware-\(Int(Date().timeIntervalSince1970)).json"
        dialog.allowedContentTypes = [.json]
        dialog.canCreateDirectories = true
        NSApp.activate(ignoringOtherApps: true)
        guard dialog.runModal() == .OK, let destination = dialog.url else { return }
        do {
            try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: destination, options: .atomic)
            record("export", "saved")
            scanSummary = "Diagnostics exported."
        } catch { scanSummary = "Export failed: \(error.localizedDescription)"; record("export", "failed") }
    }
    func revealReport() { if let url = lastReport { NSWorkspace.shared.activateFileViewerSelecting([url]) } }
}

struct Tag: View {
    var title: String
    var tint: Color = accent
    var body: some View { Text(title).font(.system(size: 10, weight: .semibold, design: .monospaced)).tracking(1).foregroundColor(tint).padding(.horizontal, 9).padding(.vertical, 5).background(tint.opacity(0.09)).clipShape(RoundedRectangle(cornerRadius: 2)) }
}
struct Card<Content: View>: View {
    let content: Content
    init(@ViewBuilder content: () -> Content) { self.content = content() }
    var body: some View { content.padding(22).frame(maxWidth: .infinity, alignment: .leading).background(panel).cornerRadius(6).overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.white.opacity(0.065), lineWidth: 1)) }
}
struct GPUPreview: View {
    @ObservedObject var model: Model
    var colors: [Color] { model.effect == .solid || model.effect == .breath ? [model.colorA, model.colorA, model.colorA] : [model.colorA, model.colorB, model.colorC] }
    var body: some View {
        ZStack {
            Canvas { context, size in
                var grid = Path()
                for x in stride(from: CGFloat(0), to: size.width, by: 24) { grid.move(to: CGPoint(x: x, y: 0)); grid.addLine(to: CGPoint(x: x, y: size.height)) }
                for y in stride(from: CGFloat(0), to: size.height, by: 24) { grid.move(to: CGPoint(x: 0, y: y)); grid.addLine(to: CGPoint(x: size.width, y: y)) }
                context.stroke(grid, with: .color(.white.opacity(0.025)), lineWidth: 1)
            }
            LinearGradient(colors: colors.map { $0.opacity(0.08) }, startPoint: .leading, endPoint: .trailing)
            VStack(spacing: 18) {
                HStack {
                    Text(model.currentBoardVendor.uppercased()).font(.system(size: 10, weight: .bold, design: .monospaced)).tracking(3).foregroundColor(muted)
                    Spacer(); Text(model.currentGPUName.uppercased()).font(.system(size: 10, weight: .bold, design: .monospaced)).foregroundColor(muted)
                }
                HStack(spacing: 30) {
                    ForEach(0..<3) { i in
                        ZStack {
                            Circle().stroke(colors[i].opacity(0.15), lineWidth: 12)
                            ForEach(0..<9) { blade in Capsule().fill(Color.white.opacity(0.06)).frame(width: 13, height: 42).offset(y: -23).rotationEffect(.degrees(Double(blade)*40)) }
                            Circle().fill(panel).frame(width: 27, height: 27).overlay(Circle().stroke(colors[i].opacity(0.5), lineWidth: 1))
                        }.frame(width: 94, height: 94)
                    }
                }
                RoundedRectangle(cornerRadius: 3).fill(LinearGradient(colors: colors, startPoint: .leading, endPoint: .trailing)).frame(height: 5).shadow(color: colors[0].opacity(0.45), radius: 6)
            }.padding(26).background(ink.opacity(0.8)).cornerRadius(6).padding(.horizontal, 42).padding(.vertical, 32)
        }.frame(height: 230).cornerRadius(6).overlay(RoundedRectangle(cornerRadius:6).stroke(Color.white.opacity(0.05)))
    }
}
struct Studio: View {
    @ObservedObject var model: Model
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("01 / LIGHTING STUDIO").font(.system(size: 10, weight: .medium, design: .monospaced)).tracking(3).foregroundColor(accent)
                    Text("Lighting").font(.system(size: 29, weight: .semibold))
                    Text(model.currentGPUName).font(.system(size:12)).foregroundColor(muted)
                }
                Spacer(); Tag(title: model.scanning ? "CHECKING" : model.canControlLighting ? "PROFILE READY" : "SCAN REQUIRED")
            }
            GPUPreview(model: model)
            HStack { Text("SCHEMATIC PREVIEW").font(.system(size: 9, design: .monospaced)).tracking(1.5); Spacer(); Text("No live GPU feedback") .font(.system(size: 10)) }.foregroundColor(muted)
            Card {
                VStack(alignment: .leading, spacing: 18) {
                    HStack { Text("Effect").font(.system(size: 15, weight: .semibold)); Spacer(); Tag(title: model.effectIsConfirmed(model.effect) ? "USER CONFIRMED" : "EXPERIMENTAL", tint: model.effectIsConfirmed(model.effect) ? accent : .orange) }
                    HStack(spacing: 8) {
                        ForEach(Lighting.allCases) { item in
                            Button { model.effect = item } label: {
                                VStack(spacing: 9) { Image(systemName: item.symbol).font(.system(size: 18)); Text(item.rawValue).font(.system(size: 10, weight: .medium)) }.frame(maxWidth: .infinity).padding(.vertical, 15).foregroundColor(model.effect == item ? accent : muted).background(model.effect == item ? accent.opacity(0.09) : ink).cornerRadius(4).overlay(RoundedRectangle(cornerRadius: 4).stroke(model.effect == item ? accent.opacity(0.5) : Color.clear))
                            }.buttonStyle(.plain)
                        }
                    }
                    Text(model.effect.detail).font(.system(size: 11)).foregroundColor(muted).frame(height: 28, alignment: .topLeading)
                    if model.effect == .solid || model.effect == .breath || model.effect == .gradient {
                        HStack(spacing: 18) {
                            ColorPicker(model.effect == .gradient ? "Zone 01" : "Color", selection: $model.colorA, supportsOpacity: false)
                            if model.effect == .gradient { ColorPicker("Zone 02", selection: $model.colorB, supportsOpacity: false); ColorPicker("Zone 03", selection: $model.colorC, supportsOpacity: false) }
                            Spacer()
                            Text("#" + model.hex(model.colorA).uppercased()).font(.system(size: 11, design: .monospaced)).foregroundColor(muted)
                        }.font(.system(size: 11))
                    }
                    HStack { Text("Brightness").frame(width: 80, alignment: .leading); Slider(value: $model.brightness, in: 0...100); Text("\(Int(model.brightness)) %").monospacedDigit().frame(width: 45) }.font(.system(size: 11)).foregroundColor(muted)
                    if model.effect != .solid && model.effect != .gradient {
                        HStack { Text("Speed").frame(width: 80, alignment: .leading); Slider(value: $model.speed, in: 0...100); Text("\(Int(model.speed)) %").monospacedDigit().frame(width: 45) }.font(.system(size: 11)).foregroundColor(muted)
                    }
                }
            }
            HStack(spacing: 12) {
                Button { model.apply(off: true) } label: { Label("Off", systemImage: "power").frame(width: 68).padding(.vertical, 11) }.buttonStyle(.plain).background(panel).cornerRadius(4)
                Spacer()
                Button { model.apply() } label: { HStack { if model.busy { ProgressView().controlSize(.small) }; Text(model.busy ? "Applying …" : "Apply"); Image(systemName: "arrow.up.right") }.font(.system(size: 12, weight: .semibold)).foregroundColor(ink).padding(.horizontal, 24).padding(.vertical, 13).background(accent).cornerRadius(4) }.buttonStyle(.plain)
            }.disabled(model.working || !model.canControlLighting)
            HStack(alignment: .top, spacing: 8) {
                Circle().fill(model.lastSuccess == false ? Color.orange : accent).frame(width: 5, height: 5).padding(.top, 5)
                Text(model.message).font(.system(size: 10)).foregroundColor(muted).textSelection(.enabled)
                Spacer()
                Button(action: model.revealReport) { Image(systemName: "doc.text.magnifyingglass") }.buttonStyle(.plain).disabled(model.lastReport == nil).help("Reveal latest lighting report in Finder")
            }.frame(minHeight: 30)
        }
    }
}

struct GPUInfo: Identifiable {
    let id: Int
    let name: String
    let pci: String
    let subsystem: String
    let vendor: String
    let gpuType: String
    let supported: Bool
    let nvrm: Bool
}

struct SetupCard: View {
    @ObservedObject var model: Model
    var body: some View {
        Card {
            VStack(alignment: .leading, spacing: 12) {
                HStack { Label("Lighting profile", systemImage: "checkmark.shield").font(.headline); Spacer(); Tag(title: model.setupState == "confirmed" ? "READY" : model.setupState.uppercased()) }
                Text(model.currentGPUName).font(.system(size: 16, weight: .semibold))
                Text("GPU: \(model.currentGPUVendor) · Board: \(model.currentBoardVendor)").foregroundColor(muted)
                HStack {
                    Text(model.setupMessage).font(.system(size:11)).foregroundColor(muted)
                    Spacer()
                    if model.configurationStatus == "supported" { Button(model.setupState == "confirmed" ? "Retest…" : "Continue setup…") { model.showSetupWizard = true }.disabled(model.working) }
                }
                if !model.communityStatus.isEmpty { Text(model.communityStatus).font(.caption).foregroundColor(accent) }
                DisclosureGroup("Sharing & privacy") {
                    VStack(alignment:.leading,spacing:8) {
                        Toggle("Share successful hardware confirmations", isOn:$model.contributeConfirmation)
                        Text("Shares card IDs, names, tested effects, software versions and a random installation ID. Troubleshooting notes are sent only after review.").font(.caption).foregroundColor(muted)
                    }.padding(.top,8)
                }.font(.system(size:11))
            }
        }
    }
}
struct SetupWizard: View {
    @ObservedObject var model: Model
    @State private var editIdentity = false
    var body: some View {
        VStack(alignment:.leading,spacing:18) {
            HStack { Text(model.setupTesting ? "Checking your lighting" : "Confirm your lighting").font(.title2.weight(.semibold)); Spacer(); Tag(title:"SETUP") }
            Text(model.currentGPUName).font(.headline)
            Text("GPU: \(model.currentGPUVendor) · Board: \(model.currentBoardVendor)").foregroundColor(muted)
            DisclosureGroup("Confirm or correct card identity",isExpanded:$editIdentity) {
                Text("Use the board manufacturer and exact model printed on the card or packaging. PCI IDs always remain those detected by the scanner.").font(.caption).foregroundColor(muted)
                TextField("Board manufacturer (e.g. PNY)",text:$model.manualVendor)
                TextField("Exact model / board revision",text:$model.manualModel)
            }
            Divider()
            if model.setupTesting {
                ProgressView(value:Double(model.testStep),total:Double(model.testPlan.count)).tint(accent)
                Text(model.setupMessage).font(.headline)
                Text("Watch the card: red, green, blue, Gradient, Spectrum, Breathing, then Wave. The test takes about 30 seconds.").foregroundColor(muted)
                Button("Stop test") { model.setupTesting = false; model.testTransportOK = false; model.setupState = "partial"; model.setupMessage = "Test stopped. No profile was confirmed."; model.record("setup-test","cancelled") }
            } else if model.testTransportOK && model.setupState == "awaiting-confirmation" {
                Text("Did every color and effect work on the physical card?").font(.headline)
                Text(model.setupMessage).font(.caption).foregroundColor(muted)
                Toggle("Share this confirmation with the community",isOn:$model.contributeConfirmation)
                Text("Your observation confirms compatibility. A successful command alone cannot verify visible lighting.").font(.caption).foregroundColor(muted)
                Button("Everything worked — save profile") { model.confirmSetup("confirmed") }.buttonStyle(.borderedProminent).disabled(model.working)
                HStack { Button("Partially working") { model.confirmSetup("partial") }; Button("No light") { model.confirmSetup("failed") } }
            } else if model.setupState == "failed" || model.setupState == "partial" {
                Text(model.setupMessage).foregroundColor(.orange)
                TextEditor(text:$model.observedBehavior).onChange(of:model.observedBehavior) { _ in model.feedbackChanged() }.frame(height:100)
                Text("Tell us which colors, zones or effects failed. Review the report before sending.").font(.caption).foregroundColor(muted)
                HStack { Button("Review report…") { model.showSetupWizard = false; DispatchQueue.main.asyncAfter(deadline:.now()+0.3) { model.reviewReport() } }; Spacer(); Button("Close") { model.showSetupWizard = false } }
            } else {
                Text("The guided test checks three primary colors and all four effects. Wave remains active afterwards.").foregroundColor(muted)
                HStack { Button("Run lighting test",action:model.startSetupTest).buttonStyle(.borderedProminent); Spacer(); Button("Close") { model.showSetupWizard = false } }
            }
        }.padding(28).frame(width:540).background(ink).foregroundColor(.white).preferredColorScheme(.dark).tint(accent).interactiveDismissDisabled(model.setupTesting).onAppear { editIdentity = model.needsIdentity }
    }
}
struct ReportPreview: View {
    @ObservedObject var model: Model
    var body: some View {
        VStack(alignment: .leading, spacing: 15) {
            Text("Troubleshooting report").font(.title2)
            Text("Review the exact payload. Upload happens only when you press Send.").font(.caption).foregroundColor(muted)
            ScrollView { Text(model.reportPreview).font(.system(size: 10, design: .monospaced)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading).padding() }.background(ink)
            if model.reportEndpoint == nil { Text("Report inbox is not configured yet. Save the report locally and share it with the maintainer.").font(.caption).foregroundColor(.orange) }
            if let destination = model.reportEndpoint?.host { Text("Destination: \(destination)").font(.caption).foregroundColor(muted) }
            Text(model.submissionMessage).font(.caption).textSelection(.enabled)
            HStack {
                Button("Close") { model.showReportPreview = false }.disabled(model.submitting)
                Button("Export…", action: model.exportDiagnostics)
                Spacer()
                Button("Send report", action: model.submitReport).disabled(model.reportEndpoint == nil || model.working)
            }
        }.padding(24).frame(width: 680, height: 570).background(panel).preferredColorScheme(.dark)
    }
}

struct Community: View {
    @ObservedObject var model: Model
    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            SetupCard(model: model)
            HStack {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Hardware scanner").font(.system(size: 28, weight: .semibold))
                    Text("Read-only inventory for community compatibility reports.").font(.system(size: 12)).foregroundColor(muted)
                }
                Spacer()
            }
            Card {
                VStack(alignment: .leading, spacing: 15) {
                    HStack {
                        Tag(title: "NO HARDWARE WRITES")
                        Spacer()
                        if model.scanning { ProgressView().controlSize(.small) }
                    }
                    Text(model.configurationReason).font(.system(size: 12, weight: .medium)).foregroundColor(model.canControlLighting ? accent : .orange)
                    Text(model.scanSummary).font(.system(size: 12)).foregroundColor(muted)
                    HStack {
                        Button(model.scanning ? "Scanning…" : "Scan hardware", action: model.scanHardware).disabled(model.working)
                        Button("Export diagnostics…", action: model.exportDiagnostics).disabled(model.scanJSON.isEmpty || model.scanning)
                        Spacer()
                    }
                    Text("Exports PCI IDs, model labels, driver versions and query logs. No serial numbers, hostname, raw device tree or kernel addresses. No automatic uploads.").font(.system(size: 10)).foregroundColor(muted)
                }
            }
            ForEach(model.adapters) { gpu in
                Card {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack { Text(gpu.name).font(.headline); Spacer(); Tag(title: gpu.supported ? "VERIFIED PROFILE" : "UNSUPPORTED", tint: gpu.supported ? accent : .orange) }
                        Text("\(gpu.vendor) · \(gpu.gpuType)").font(.system(size: 11)).foregroundColor(muted)
                        Text("PCI \(gpu.pci) / \(gpu.subsystem)").font(.system(size: 12, design: .monospaced)).foregroundColor(accent)
                        Text(gpu.nvrm ? "NVRM binding found" : "No NVRM binding found").font(.system(size: 11)).foregroundColor(muted)
                    }
                }
            }
            if !model.sessionEvents.isEmpty {
                Card {
                    VStack(alignment: .leading, spacing: 8) {
                        DisclosureGroup("Session log") {
                        ForEach(Array(model.sessionEvents.suffix(6).enumerated()), id: \.offset) { _, event in
                            Text("\(event["time"] ?? "")  \(event["action"] ?? "") / \(event["outcome"] ?? "")").font(.system(size: 9, design: .monospaced)).foregroundColor(muted).textSelection(.enabled)
                        }
                        }
                    }
                }
            }
            Card {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Community report").font(.headline)
                    if model.needsIdentity {
                        TextField("Board manufacturer",text:$model.manualVendor).onChange(of:model.manualVendor) { _ in model.feedbackChanged() }
                        TextField("Exact card model / board revision",text:$model.manualModel).onChange(of:model.manualModel) { _ in model.feedbackChanged() }
                    } else { TextField("Board revision or additional model details (optional)", text: $model.boardLabel).onChange(of:model.boardLabel) { _ in model.feedbackChanged() } }
                    TextEditor(text: $model.observedBehavior).onChange(of: model.observedBehavior) { _ in model.feedbackChanged() }.frame(height: 90).overlay(RoundedRectangle(cornerRadius: 4).stroke(muted.opacity(0.3)))
                    Text("Describe missing colors, unlit zones, errors, or no response at all. Notes are exported as entered.").font(.system(size: 10)).foregroundColor(muted)
                    Button("Review / send report…", action: model.reviewReport).disabled(model.scanJSON.isEmpty || model.working)
                    Text("These reports help identify boards and compare drivers. They do not reveal the RGB protocol, controller address or physical LED mapping. Those still need source research and targeted hardware tests.").font(.system(size: 11)).foregroundColor(muted)
                }
            }
            Text("Compatibility database").font(.system(size: 16, weight: .semibold))
            ForEach(model.compatibilityRows) { row in
                Card {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack { Text("\(row.board_vendor) · \(row.gpu_vendor) \(row.gpu_name)").font(.headline); Spacer(); Tag(title: "USER CONFIRMED") }
                        Text(row.hardware_key.uppercased()).font(.system(size: 11, design: .monospaced)).foregroundColor(accent)
                        Text("Confirmed: " + row.confirmed_effects.map { mode in Lighting.allCases.first(where: { $0.backend == mode })?.rawValue ?? mode }.joined(separator: ", ")).font(.system(size: 11)).foregroundColor(muted)
                        Text("\(row.reports) confirmation(s) · \(row.source ?? "Community")").font(.system(size: 10)).foregroundColor(muted)
                    }
                }
            }
            Card {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Additional hardware").font(.headline)
                    Text("Other models are not enabled. Each profile needs PCI IDs, a documented lighting controller and a verified transport. Unknown cards are never written to.").font(.system(size: 12)).foregroundColor(muted).lineSpacing(5)
                }
            }
            Text("This is the verified profile, not a live connection indicator.").font(.system(size: 11)).foregroundColor(muted)
            Spacer()
        }
    }
}
struct Credits: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            Text("Credits").font(.system(size: 28, weight: .semibold))
            Text("HackinFX / by aleopho").font(.system(size: 14, design: .monospaced)).foregroundColor(accent)
            Card {
                VStack(alignment: .leading, spacing: 16) {
                    Text("NullMoth").font(.headline)
                    Text("The installed NVRM interface provides macOS access. The driver is installed separately and is not bundled. NVRM source v2.5.3 specifies PolyForm Noncommercial 1.0.0.").font(.system(size: 12)).foregroundColor(muted).lineSpacing(4)
                    Link("NullMoth / project and license", destination: URL(string:"https://github.com/nullmoth/nvidia-macos-driver")!)
                    Divider()
                    Text("OpenRGB").font(.headline)
                    Text("PNY Lovelace protocol and effect packets adapted from yufan and the OpenRGB contributors. The source is GPL-2.0-or-later. Thank you for the open implementation.").font(.system(size: 12)).foregroundColor(muted).lineSpacing(4)
                    Link("OpenRGB / PNY controller", destination: URL(string:"https://gitlab.com/CalcProgrammer1/OpenRGB/-/tree/master/Controllers/PNYLovelaceGPUController")!)
                    Divider()
                    Text("NVIDIA").font(.headline)
                    Text("Public RM ABI definitions from open-gpu-kernel-modules 610.57.04, MIT. License notices are included.").font(.system(size: 12)).foregroundColor(muted)
                    Link("NVIDIA / SDK sources", destination: URL(string:"https://github.com/NVIDIA/open-gpu-kernel-modules/tree/610.57.04")!)
                }
            }
            Text("Independent community project. Not affiliated with PNY, NVIDIA, Apple, NullMoth or OpenRGB. GPL-2.0-or-later · No warranty. License and source are included.").font(.system(size: 11)).foregroundColor(muted).lineSpacing(4)
            HStack {
                Button("License text") { if let file = Bundle.main.url(forResource: "COPYING", withExtension: nil) { NSWorkspace.shared.open(file) } }
                Button("Source code") { if let folder = Bundle.main.resourceURL?.appendingPathComponent("Source") { NSWorkspace.shared.activateFileViewerSelecting([folder]) } }
            }
            Spacer()
        }
    }
}
struct LaunchView: View {
    @Environment(\.accessibilityReduceMotion) var reduceMotion
    @State private var visible = false
    var body: some View {
        VStack(spacing: 20) {
            Image(nsImage: NSImage(contentsOf: Bundle.main.url(forResource: "hackinfx-logo", withExtension: "png")!) ?? NSImage()).resizable().scaledToFit().frame(width: 110, height: 110)
            Text("HackinFX").font(.system(size: 26, weight: .semibold, design: .monospaced))
            Text("by aleopho").font(.system(size: 11, design: .monospaced)).foregroundColor(muted)
        }.opacity(visible ? 1 : 0).scaleEffect(reduceMotion ? 1 : visible ? 1 : 0.97)
        .frame(maxWidth: .infinity, maxHeight: .infinity).background(ink)
        .onAppear { withAnimation(reduceMotion ? nil : .easeOut(duration: 0.4)) { visible = true } }
    }
}

struct Root: View {
    @ObservedObject var model: Model
    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 0) {
                HStack(spacing: 10) {
                    Image(nsImage: NSImage(contentsOf: Bundle.main.url(forResource: "hackinfx-logo", withExtension: "png")!) ?? NSImage()).resizable().scaledToFit().frame(width: 48, height: 48).background(Color.black).cornerRadius(4)
                    VStack(alignment: .leading, spacing: 3) { Text("HackinFX").font(.system(size: 15, weight: .bold, design: .monospaced)); Text("BY ALEOPHO").font(.system(size: 8, weight: .medium, design: .monospaced)).tracking(2).foregroundColor(muted) }
                }.padding(.bottom, 45)
                Text("WORKSPACE / LOCAL").font(.system(size: 8, design: .monospaced)).tracking(2).foregroundColor(muted).padding(.bottom, 15)
                ForEach([("Studio","slider.horizontal.3"),("Hardware","cpu"),("Credits","heart")], id: \.0) { title, icon in
                    Button { model.page = title == "Studio" && !model.canControlLighting ? "Hardware" : title } label: { HStack(spacing: 12) { Image(systemName: icon).frame(width: 18); Text(title); Spacer() }.font(.system(size: 12, weight: .medium)).padding(12).foregroundColor(model.page == title ? accent : muted).background(model.page == title ? accent.opacity(0.08) : Color.clear).cornerRadius(4) }.buttonStyle(.plain).padding(.bottom, 5)
                }
                Spacer()
                Rectangle().fill(Color.white.opacity(0.07)).frame(height: 1).padding(.bottom, 18)
                Text(model.canControlLighting ? "LIGHTING PROFILE" : "HARDWARE STATUS").font(.system(size: 8, design: .monospaced)).tracking(1.5).foregroundColor(muted)
                Text(model.currentGPUName).font(.system(size: 12, weight: .medium)).padding(.top, 8)
                Text("\(model.currentGPUVendor) / \(model.currentBoardVendor)").font(.system(size: 9)).foregroundColor(muted).padding(.top, 4)
                Tag(title: "1.0.0 / COMMUNITY").padding(.top, 18)
            }.padding(24).frame(width: 180).background(panel.opacity(0.6))
            ScrollView { Group { if model.page == "Studio" { Studio(model:model) } else if model.page == "Hardware" { Community(model:model) } else { Credits() } }.padding(30).frame(maxWidth: .infinity, alignment: .leading) }.frame(width: 690)
        }.frame(minHeight: 790).background(ink).foregroundColor(Color(red: 0.88, green: 0.87, blue: 0.81)).font(.system(size: 12, design: .monospaced)).preferredColorScheme(.dark).environment(\.locale, Locale(identifier: "en")).fontDesign(.monospaced).tint(accent).overlay { if model.launching { LaunchView().transition(.opacity) } }.animation(.easeOut(duration: 0.2), value: model.launching).overlay { if model.scanning { VStack(spacing:18) { ProgressView().controlSize(.large); Text("Detecting your hardware").font(.title2); Text("Reading PCI identity, driver and lighting profile…").foregroundColor(muted) }.frame(maxWidth:.infinity,maxHeight:.infinity).background(ink.opacity(0.97)) } }.sheet(isPresented:$model.showSetupWizard) { SetupWizard(model:model) }.sheet(isPresented: $model.showReportPreview) { ReportPreview(model: model) }
    }
}
final class Delegate: NSObject, NSApplicationDelegate, NSMenuDelegate, NSWindowDelegate {
    let model = Model()
    var window: NSWindow!
    var statusItem: NSStatusItem!
    var actionItems: [NSMenuItem] = []
    var exportItem: NSMenuItem!
    var scanItem: NSMenuItem!
    static func menuGPUImage() -> NSImage {
        let image = NSImage(size:NSSize(width:26,height:18),flipped:false) { _ in
            NSColor.black.setStroke()
            let body = NSBezierPath(roundedRect:NSRect(x:4,y:4,width:21,height:12),xRadius:1.8,yRadius:1.8); body.lineWidth = 0.9; body.stroke()
            for x in [10.0,19.0] { let fan = NSBezierPath(ovalIn:NSRect(x:x-3.3,y:6.7,width:6.6,height:6.6)); fan.lineWidth=0.8; fan.stroke(); let hub=NSBezierPath(ovalIn:NSRect(x:x-0.8,y:9.2,width:1.6,height:1.6));hub.lineWidth=0.7;hub.stroke() }
            let edge=NSBezierPath();edge.lineWidth=0.9;edge.move(to:NSPoint(x:2,y:3));edge.line(to:NSPoint(x:2,y:17));edge.move(to:NSPoint(x:6,y:2));edge.line(to:NSPoint(x:17,y:2));edge.stroke()
            return true
        }; image.isTemplate=true; image.accessibilityDescription="HackinFX GPU"; return image
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        window = NSWindow(contentRect: NSRect(x:0,y:0,width:918,height:790), styleMask:[.titled,.closable,.miniaturizable], backing:.buffered, defer:false)
        window.title = "HackinFX — by aleopho"
        window.appearance = NSAppearance(named: .darkAqua)
        window.isReleasedWhenClosed = false
        window.delegate = self
        window.contentView = NSHostingView(rootView: Root(model:model))
        window.center()
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.button?.image = Self.menuGPUImage()
        statusItem.button?.title = " FX"
        statusItem.button?.toolTip = "HackinFX — GPU lighting"
        let menu = NSMenu(); menu.delegate = self; menu.autoenablesItems = false
        let header = menu.addItem(withTitle:"HackinFX · by aleopho", action:nil, keyEquivalent:""); header.isEnabled = false
        add(menu,"Open Lighting",#selector(show),"o")
        menu.addItem(NSMenuItem.separator())
        actionItems.append(add(menu,"Apply current settings",#selector(applyCurrent)))
        actionItems.append(add(menu,"Turn lighting off",#selector(turnOff)))
        let effects = NSMenu()
        for (index,effect) in Lighting.allCases.enumerated() {
            let item = add(effects,effect.rawValue,#selector(selectEffect)); item.tag = index; actionItems.append(item)
        }
        let effectItem = menu.addItem(withTitle:"Effects", action:nil, keyEquivalent:""); effectItem.submenu = effects
        menu.addItem(NSMenuItem.separator())
        scanItem = add(menu,"Scan hardware…",#selector(scan))
        exportItem = add(menu,"Export diagnostics…",#selector(exportScan))
        add(menu,"Open reports folder",#selector(reports))
        add(menu,"Credits & licenses",#selector(credits))
        menu.addItem(NSMenuItem.separator())
        add(menu,"Quit HackinFX",#selector(quit),"q")
        statusItem.menu = menu
        let main = NSMenu()
        let appItem = NSMenuItem(); let appMenu = NSMenu()
        add(appMenu,"About HackinFX",#selector(credits))
        appMenu.addItem(NSMenuItem.separator())
        add(appMenu,"Quit HackinFX",#selector(quit),"q")
        appItem.submenu = appMenu; main.addItem(appItem)
        let editItem = NSMenuItem(); let edit = NSMenu(title:"Edit")
        edit.addItem(withTitle:"Copy", action:#selector(NSText.copy(_:)), keyEquivalent:"c")
        edit.addItem(withTitle:"Paste", action:#selector(NSText.paste(_:)), keyEquivalent:"v")
        edit.addItem(withTitle:"Select All", action:#selector(NSText.selectAll(_:)), keyEquivalent:"a")
        editItem.submenu = edit; main.addItem(editItem); NSApp.mainMenu = main
        show()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.85) { self.model.launching = false; self.model.scanHardware() }
    }
    @discardableResult func add(_ menu: NSMenu, _ title: String, _ selector: Selector, _ key: String = "") -> NSMenuItem {
        let item = menu.addItem(withTitle:title, action:selector, keyEquivalent:key); item.target = self; return item
    }
    func menuWillOpen(_ menu: NSMenu) {
        for item in actionItems { item.isEnabled = !model.working && model.canControlLighting }
        scanItem.isEnabled = !model.working
        exportItem.isEnabled = !model.scanJSON.isEmpty && !model.scanning
    }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { show(); return true }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func windowShouldClose(_ sender: NSWindow) -> Bool {
        sender.orderOut(nil)
        NSApp.setActivationPolicy(.accessory)
        return false
    }
    @objc func show() { NSApp.setActivationPolicy(.regular); NSApp.activate(ignoringOtherApps:true); window.makeKeyAndOrderFront(nil) }
    @objc func applyCurrent() { model.apply() }
    @objc func turnOff() { model.apply(off:true) }
    @objc func selectEffect(_ sender: NSMenuItem) { guard !model.working && model.canControlLighting else { return }; model.effect = Lighting.allCases[sender.tag]; model.apply() }
    @objc func scan() { model.page = "Hardware"; show(); model.scanHardware() }
    @objc func exportScan() { model.exportDiagnostics() }
    @objc func reports() {
        let folder = FileManager.default.urls(for:.applicationSupportDirectory,in:.userDomainMask)[0].appendingPathComponent("HackinFX",isDirectory:true)
        try? FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
        NSWorkspace.shared.open(folder)
    }
    @objc func credits() { model.page = "Credits"; show() }
    @objc func quit() { NSApp.terminate(nil) }
}
@main
struct HackinFXMain {
    static func main() throws {
UserDefaults.standard.set(["en"], forKey: "AppleLanguages")
let app = NSApplication.shared
if CommandLine.arguments.count == 3 && ["--render-preview","--render-setup-preview"].contains(CommandLine.arguments[1]) {
    app.setActivationPolicy(.prohibited)
    let preview = Model(); preview.launching = false; preview.page = "Studio"; preview.configurationStatus = "supported"; preview.setupState = "confirmed"; preview.currentGPUName = "PNY XLR8 RTX 4080 VERTO"; preview.currentGPUVendor = "NVIDIA"; preview.currentBoardVendor = "PNY"
    preview.manualVendor = "PNY"; preview.manualModel = preview.currentGPUName
    if CommandLine.arguments[1] == "--render-setup-preview" { preview.setupState = "awaiting-confirmation"; preview.testTransportOK = true; preview.setupMessage = "All seven transport steps completed. Confirm visible operation below." }
    let content = CommandLine.arguments[1] == "--render-setup-preview" ? AnyView(SetupWizard(model:preview)) : AnyView(Root(model:preview))
    let view = NSHostingView(rootView: content)
    view.frame = NSRect(x: 0, y: 0, width: 918, height: 790)
    view.layoutSubtreeIfNeeded()
    if let bitmap = view.bitmapImageRepForCachingDisplay(in: view.bounds) {
        view.cacheDisplay(in: view.bounds, to: bitmap)
        if let png = bitmap.representation(using: .png, properties: [:]) { try png.write(to: URL(fileURLWithPath: CommandLine.arguments[2])) }
    }
    exit(0)
}
let delegate = Delegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
withExtendedLifetime(delegate) { app.run() }

    }
}
