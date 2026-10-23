import Foundation
@main struct SetupSupportTests {
    static func main() throws {
        let saved = VerifiedSetup(fingerprint: "hardware-a", confirmedAt: Date(), successfulSteps: 3, userConfirmed: true, verifiedEffects:["static","gradient","cycle","breath","wave"])
        assert(saved.matches("hardware-a"))
        assert(!VerifiedSetup(fingerprint:"hardware-a",confirmedAt:Date(),successfulSteps:3,userConfirmed:true).matches("hardware-a"))
        assert(!saved.matches("hardware-b"))
        assert(!saved.matches(""))
        assert(!VerifiedSetup(fingerprint: "a", confirmedAt: Date(), successfulSteps: 2, userConfirmed: true).matches("a"))
        assert(!VerifiedSetup(fingerprint: "a", confirmedAt: Date(), successfulSteps: 3, userConfirmed: false).matches("a"))
        var future = saved; future.schema = 2
        assert(!future.matches("hardware-a"))
        let decoded = try JSONDecoder().decode(VerifiedSetup.self, from: JSONEncoder().encode(saved))
        assert(decoded.matches("hardware-a"))
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: folder) }
        let store = VerificationStore(directory: folder)
        let card = VerifiedHardware(vendor_id: "10de", device_id: "2704", subsystem_vendor_id: "196e", subsystem_id: "13bc", gpu_name: "GeForce RTX 4080", gpu_vendor: "NVIDIA", board_vendor: "PNY", profile: "pny-4080-196e-13bc")
        let item = HardwareVerification(verification_id: UUID().uuidString, installation_id: "installation", hardware: card, macos: "26.7.1", arch: "x86_64", driver_version: "2.5.2", confirmed_effects: ["static", "wave"], tested_steps: 7, confirmed_at: "2026-10-23")
        try store.remember(item)
        assert(store.load().count == 1)
        assert(store.load()[0].gpu_vendor == "NVIDIA" && store.load()[0].board_vendor == "PNY")
        try store.enqueue(item)
        assert(store.pending().count == 1)
        var newer = item
        newer = HardwareVerification(verification_id: UUID().uuidString, installation_id: item.installation_id, hardware: card, macos: "26.7.1", arch: "x86_64", driver_version: "2.5.2", confirmed_effects: ["static", "wave"], tested_steps: 7, confirmed_at: "2026-10-24")
        try store.enqueue(newer)
        assert(store.pending().count == 1)
        assert(store.pending()[0].1.verification_id == newer.verification_id)
        try store.remember(newer)
        assert(store.load().count == 1)
        assert(store.load()[0].last_confirmed == "2026-10-24")
        let oldBytes = try JSONEncoder().encode(item)
        let restored = try JSONDecoder().decode(HardwareVerification.self, from: oldBytes)
        assert(restored.hardware.key == item.hardware.key)
        assert(restored.identity_source == nil)
        var identified = item; identified.identity_source = "user-supplied"; identified.detected_gpu_name = "Generic adapter"
        let roundtrip = try JSONDecoder().decode(HardwareVerification.self,from:JSONEncoder().encode(identified))
        assert(roundtrip.identity_source == "user-supplied" && roundtrip.detected_gpu_name == "Generic adapter")
        let snapshot = WidgetStatusSnapshot(gpuName:"PNY RTX 4080",boardVendor:"PNY",profileReady:true,lastCommand:"Wave",updatedAt:Date(),colors:["ff0000","00ff00","0000ff"],brightness:50)
        let widgetBytes = try JSONEncoder().encode(snapshot)
        let decodedWidget = try JSONDecoder().decode(WidgetStatusSnapshot.self,from:widgetBytes)
        assert(decodedWidget.gpuName == "PNY RTX 4080")
        assert(decodedWidget.colors == ["ff0000","00ff00","0000ff"] && decodedWidget.brightness == 50)
        assert(!String(decoding:widgetBytes,as:UTF8.self).contains("installation_id"))
        print("21 local-profile and compatibility-store assertions passed")
    }
}
