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
    var body: some View {
        VStack(alignment:.leading,spacing:12) {
            HStack { Image(systemName:"slider.horizontal.3").foregroundStyle(lime);Text("HackinFX").font(.system(size:13,weight:.semibold));Spacer();Circle().fill(entry.snapshot.profileReady ? lime : .gray).frame(width:5,height:5) }
            Text(entry.snapshot.gpuName).font(.system(size:family == .systemSmall ? 13 : 16,weight:.medium)).lineLimit(2)
            Spacer(minLength:0)
            if family == .systemMedium {
                HStack { Text(entry.snapshot.boardVendor).font(.caption).foregroundStyle(.secondary);Spacer();Link(destination:URL(string:"hackinfx://hardware")!) { Label("Hardware",systemImage:"cpu").font(.caption) } }
            }
            HStack { Text("LAST SENT").font(.system(size:8,weight:.semibold,design:.monospaced)).foregroundStyle(.secondary);Spacer();Text(entry.snapshot.lastCommand).font(.system(size:10,weight:.medium)).lineLimit(1) }
            if entry.snapshot.updatedAt != .distantPast { HStack { Text("Updated");Text(entry.snapshot.updatedAt,style:.relative);Spacer() }.font(.system(size:8)).foregroundStyle(.secondary) }
        }.foregroundStyle(Color(red:0.90,green:0.93,blue:0.91)).containerBackground(for:.widget) { Color(red:0.043,green:0.055,blue:0.063) }.widgetURL(URL(string:"hackinfx://studio"))
    }
}
struct HackinFXWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind:"HackinFXStatus",provider:Provider()) { WidgetView(entry:$0) }
            .configurationDisplayName("HackinFX").description("Your GPU profile and last lighting command. Open HackinFX to change lighting; this is not a live LED readback.").supportedFamilies([.systemSmall,.systemMedium])
    }
}
@main struct HackinFXWidgets: WidgetBundle { var body: some Widget { HackinFXWidget() } }
