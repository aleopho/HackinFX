// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation

struct VerifiedSetup: Codable {
    var schema = 1
    let fingerprint: String
    let confirmedAt: Date
    let successfulSteps: Int
    let userConfirmed: Bool
    var verifiedEffects: [String]? = nil
    var gpuName: String? = nil
    var boardVendor: String? = nil
    var gpuVendor: String? = nil
    var identitySource: String? = nil
    func matches(_ current: String, requiredEffects: [String] = ["static","gradient","cycle","breath","wave"]) -> Bool {
        schema == 1 && !current.isEmpty && fingerprint == current && successfulSteps == 3 && userConfirmed && Set(verifiedEffects ?? []).isSuperset(of:requiredEffects)
    }
}

// Confirmed profiles live in the current user's Documents/HackinFX directory.
final class SetupProfileStore {
    let directory: URL
    init(directory: URL) { self.directory = directory }
    func file(_ fingerprint: String) -> URL? {
        guard fingerprint.count == 64, fingerprint.allSatisfy({ $0.isHexDigit && $0.isASCII }) else { return nil }
        return directory.appendingPathComponent("profile-" + fingerprint.lowercased() + ".json")
    }
    func load(_ fingerprint: String) -> Data? {
        guard let url = file(fingerprint) else { return nil }
        return try? Data(contentsOf:url)
    }
    func save(_ data: Data, fingerprint: String) throws {
        guard let url = file(fingerprint) else { throw CocoaError(.fileWriteInvalidFileName) }
        try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
        try data.write(to:url,options:.atomic)
    }
}

struct CompatibilityRow: Codable, Identifiable {
    var id: String { hardware_key }
    let hardware_key: String
    let gpu_name: String
    let gpu_vendor: String
    let board_vendor: String
    let profile: String
    var confirmed_effects: [String]
    var reports: Int
    var source: String?
    var last_confirmed: String?
}
struct CompatibilityFile: Codable {
    var schema_version = 1
    var entries: [CompatibilityRow]
}

struct VerifiedHardware: Codable {
    let vendor_id: String
    let device_id: String
    let subsystem_vendor_id: String
    let subsystem_id: String
    let gpu_name: String
    let gpu_vendor: String
    let board_vendor: String
    let profile: String
    var key: String { [vendor_id, device_id, subsystem_vendor_id, subsystem_id].joined(separator: ":") }
}
struct HardwareVerification: Codable {
    var schema_version = 1
    var kind = "hardware-verification"
    let verification_id: String
    let installation_id: String
    let hardware: VerifiedHardware
    let macos: String
    let arch: String
    let driver_version: String
    let confirmed_effects: [String]
    var basic_rgb_confirmed = true
    var user_confirmed = true
    var transport_test_completed = true
    var identity_source: String? = nil
    var detected_gpu_name: String? = nil
    let tested_steps: Int
    var app_version = "2.7.0"
    let confirmed_at: String
}
final class VerificationStore {
    let directory: URL
    init(directory: URL) { self.directory = directory }
    var catalogURL: URL { directory.appendingPathComponent("compatibility.json") }
    var queueURL: URL { directory.appendingPathComponent("VerificationQueue", isDirectory: true) }
    func load() -> [CompatibilityRow] {
        guard let data = try? Data(contentsOf: catalogURL), let file = try? JSONDecoder().decode(CompatibilityFile.self, from: data) else { return [] }
        return file.entries
    }
    func remember(_ verification: HardwareVerification) throws {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        var rows = load()
        let row = CompatibilityRow(hardware_key: verification.hardware.key, gpu_name: verification.hardware.gpu_name, gpu_vendor: verification.hardware.gpu_vendor, board_vendor: verification.hardware.board_vendor, profile: verification.hardware.profile, confirmed_effects: verification.confirmed_effects, reports: 1, source: "Local user confirmation", last_confirmed: verification.confirmed_at)
        rows.removeAll { $0.hardware_key == row.hardware_key }
        rows.append(row)
        try JSONEncoder().encode(CompatibilityFile(entries: rows)).write(to: catalogURL, options: .atomic)
    }
    func enqueue(_ verification: HardwareVerification) throws {
        try FileManager.default.createDirectory(at: queueURL, withIntermediateDirectories: true)
        let destination = queueURL.appendingPathComponent(verification.verification_id + ".json")
        try JSONEncoder().encode(verification).write(to: destination, options: .atomic)
        for (url, old) in pending() where old.verification_id != verification.verification_id && old.hardware.key == verification.hardware.key && old.installation_id == verification.installation_id { try? FileManager.default.removeItem(at: url) }
    }
    func pending() -> [(URL, HardwareVerification)] {
        let files = (try? FileManager.default.contentsOfDirectory(at: queueURL, includingPropertiesForKeys: nil)) ?? []
        return files.filter { $0.pathExtension == "json" }.sorted { $0.lastPathComponent < $1.lastPathComponent }.compactMap { url in
            guard let data = try? Data(contentsOf: url), let item = try? JSONDecoder().decode(HardwareVerification.self, from: data) else { return nil }
            return (url, item)
        }
    }
}

// Read-only WidgetKit export: no PCI IDs, reports, notes, or credentials.
struct WidgetStatusSnapshot: Codable {
    var language:String?=nil
    var readyLabel:String?=nil
    var readyDevices:Int? = nil
    var statusText:String? = nil
    var schema = 1
    let gpuName: String
    let boardVendor: String
    let profileReady: Bool
    let lastCommand: String
    let updatedAt: Date
    var colors: [String]? = nil
    var brightness: Double? = nil
}
