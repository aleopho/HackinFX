import Foundation
@main struct WidgetStatusTests {
    static func main() {
        let payload="""
        {"schema":2,"appName":"HackinFX","effect":"Twinkle","activeDevices":10,"running":true,"colors":["9bed4b"],"brightness":65,"updatedAt":"2026-10-26T20:24:23Z"}
        """
        let valid=WidgetSnapshot.decode(Data(payload.utf8))!;precondition(valid.activeDevices==10);precondition(valid.effect=="Twinkle")
        for value in [payload.replacingOccurrences(of:"\"activeDevices\":10",with:"\"activeDevices\":999"),payload.replacingOccurrences(of:"9bed4b",with:"invalid"),payload.replacingOccurrences(of:"HackinFX",with:"OtherApp")] { precondition(WidgetSnapshot.decode(Data(value.utf8))==nil) }
        if CommandLine.arguments.contains("--fetch") {
            let done=DispatchSemaphore(value:0);WidgetSnapshot.fetch(port:CommandLine.arguments.last.flatMap(Int.init) ?? 49731) { value in precondition(value.appName=="HackinFX" && value.activeDevices==2 && value.updatedAt != .distantPast);print("Sandboxed widget received live effect and active-device count over loopback");done.signal() };precondition(done.wait(timeout:.now()+12) == .success)
        } else { print("Widget contract, counts, palette bounds and app identity verified") }
    }
}
