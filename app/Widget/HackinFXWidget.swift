// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
import SwiftUI
import WidgetKit
import Darwin

struct WidgetSnapshot: Codable {
    let schema: Int
    let gpuName: String
    let boardVendor: String
    let profileReady: Bool
    let lastCommand: String
    let updatedAt: Date
    var colors: [String]? = nil
    var brightness: Double? = nil
    static let empty = WidgetSnapshot(schema:1,gpuName:"Open HackinFX",boardVendor:"Lighting controls",profileReady:false,lastCommand:"No command recorded",updatedAt:.distantPast)
    static func read() -> WidgetSnapshot {
        guard let entry = getpwuid(getuid()), let home = entry.pointee.pw_dir else { return .empty }
        let file=URL(fileURLWithPath:String(cString:home)).appendingPathComponent("Library/Application Support/HackinFX/Widget/snapshot.json")
        guard let size = try? file.resourceValues(forKeys:[.fileSizeKey]).fileSize,size <= 16384,let data=try? Data(contentsOf:file) else { return .empty }
        let decoder=JSONDecoder();decoder.dateDecodingStrategy = .iso8601
        guard let snapshot=try? decoder.decode(Self.self,from:data),snapshot.schema == 1 else { return .empty }
        return snapshot
    }
}
struct Entry: TimelineEntry { let date: Date; let snapshot: WidgetSnapshot }
struct Provider: TimelineProvider {
    func placeholder(in context:Context) -> Entry { Entry(date:Date(),snapshot:.empty) }
    func getSnapshot(in context:Context,completion:@escaping(Entry)->Void) { completion(Entry(date:Date(),snapshot:context.isPreview ? .empty : .read())) }
    func getTimeline(in context:Context,completion:@escaping(Timeline<Entry>)->Void) { completion(Timeline(entries:[Entry(date:Date(),snapshot:.read())],policy:.after(Date().addingTimeInterval(900)))) }
}
struct WidgetView: View {
    @Environment(\.widgetFamily) var family
    let entry: Entry
    private let lime=Color(red:0.77,green:0.94,blue:0.49)
    private var mode: String { entry.snapshot.lastCommand.capitalized }
    private var palette: [Color] {
        if ["Spectrum","Wave"].contains(mode) { return [.cyan,.blue,.purple,.pink,.orange,.yellow,.green] }
        let hexes = mode == "Gradient" ? (entry.snapshot.colors ?? []) : Array((entry.snapshot.colors ?? []).prefix(1))
        let values = hexes.compactMap { hex -> Color? in
            guard hex.count == 6, let rgb=UInt32(hex,radix:16) else { return nil }
            return Color(red:Double((rgb >> 16) & 255)/255,green:Double((rgb >> 8) & 255)/255,blue:Double(rgb & 255)/255)
        }
        return mode == "Off" ? [.gray.opacity(0.25),.gray.opacity(0.15)] : (values.isEmpty ? [lime,lime.opacity(0.5)] : values)
    }
    var body: some View {
        VStack(alignment:.leading,spacing:8) {
            HStack {
                Image(systemName:"pciecard").foregroundStyle(lime)
                Text("HackinFX").font(.system(size:12,weight:.semibold))
                Spacer()
                if family == .systemMedium { Text(entry.snapshot.boardVendor).font(.system(size:10,design:.monospaced)).foregroundStyle(.secondary) }
            }
            Text(mode == "Not Applied" || mode == "No Command Recorded" ? "Ready to light up" : mode)
                .font(.system(size:family == .systemSmall ? 25 : 30,weight:.semibold,design:.rounded)).lineLimit(1).minimumScaleFactor(0.6)
            RoundedRectangle(cornerRadius:6)
                .fill(LinearGradient(colors:palette,startPoint:.leading,endPoint:.trailing))
                .frame(height:family == .systemSmall ? 12 : 18)
                .shadow(color:palette.first!.opacity(mode == "Off" ? 0 : 0.4),radius:8)
            Spacer(minLength:0)
            Text(entry.snapshot.gpuName).font(.system(size:12,weight:.medium)).lineLimit(2)
            HStack {
                Text("LAST APPLIED").font(.system(size:8,weight:.semibold,design:.monospaced))
                Spacer()
                if let brightness=entry.snapshot.brightness { Text("\(Int(brightness))%").font(.system(size:10,design:.monospaced)) }
            }.foregroundStyle(.secondary)
        }.foregroundStyle(Color(red:0.90,green:0.93,blue:0.91))
            .containerBackground(for:.widget) { Color(red:0.043,green:0.055,blue:0.063) }
            .widgetURL(URL(string:"hackinfx://studio"))
    }
}
struct HackinFXWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind:"HackinFXStatus",provider:Provider()) { WidgetView(entry:$0) }
            .configurationDisplayName("HackinFX").description("Your GPU, last applied lighting mode, colors and brightness. Open HackinFX to change lighting; this is not a live LED readback.").supportedFamilies([.systemSmall,.systemMedium])
    }
}
@main struct HackinFXWidgets: WidgetBundle { var body: some Widget { HackinFXWidget() } }
