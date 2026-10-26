// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
import SwiftUI
import WidgetKit
import Darwin

struct WidgetSnapshot:Decodable {
    var language:String?=nil
    var readyLabel:String?=nil
    let schema:Int
    let gpuName:String
    let lastCommand:String
    let updatedAt:Date
    let colors:[String]?
    let brightness:Double?
    let readyDevices:Int?
    let statusText:String?
    static let empty=WidgetSnapshot(schema:1,gpuName:"Open HackinFX to connect your devices",lastCommand:"Ready",updatedAt:.distantPast,colors:["c6ed91","42d6ce"],brightness:nil,readyDevices:nil,statusText:"Waiting for app")
    static func read()->Self {
        guard let entry=getpwuid(getuid()),let home=entry.pointee.pw_dir else { return .empty }
        let url=URL(fileURLWithPath:String(cString:home)).appendingPathComponent("Library/Application Support/HackinFX/Widget/snapshot.json")
        guard let size=try? url.resourceValues(forKeys:[.fileSizeKey]).fileSize,size<=16384,let data=try? Data(contentsOf:url) else { return .empty }
        let decoder=JSONDecoder();decoder.dateDecodingStrategy = .iso8601
        guard let value=try? decoder.decode(Self.self,from:data),value.schema==1 else { return .empty }
        guard value.gpuName.count<=160,value.lastCommand.count<=80,(value.readyDevices ?? 0)>=0,(value.readyDevices ?? 0)<=192 else { return .empty }
        if let brightness=value.brightness,(!brightness.isFinite || !(0...100).contains(brightness)) { return .empty }
        return value
    }
}
struct Entry:TimelineEntry { let date:Date;let snapshot:WidgetSnapshot }
struct Provider:TimelineProvider {
    func placeholder(in context:Context)->Entry { Entry(date:Date(),snapshot:.empty) }
    func getSnapshot(in context:Context,completion:@escaping(Entry)->Void) { completion(Entry(date:Date(),snapshot:context.isPreview ? .empty:.read())) }
    func getTimeline(in context:Context,completion:@escaping(Timeline<Entry>)->Void) { completion(Timeline(entries:[Entry(date:Date(),snapshot:.read())],policy:.after(Date().addingTimeInterval(60)))) }
}
struct WidgetView:View {
    @Environment(\.widgetFamily) var family
    let entry:Entry
    private let accent=Color(red:0.77,green:0.94,blue:0.49)
    private var palette:[Color] {
        let values=(entry.snapshot.colors ?? []).prefix(8).compactMap { hex->Color? in
            guard hex.count==6,let rgb=UInt32(hex,radix:16) else { return nil }
            return Color(red:Double(rgb>>16&255)/255,green:Double(rgb>>8&255)/255,blue:Double(rgb&255)/255)
        }
        return values.isEmpty ? [accent]:values
    }
    var body:some View {
        VStack(alignment:.leading,spacing:10) {
            HStack { Image(systemName:"fanblades").foregroundStyle(accent);Text("HackinFX").font(.system(size:12,weight:.semibold));Spacer();if let count=entry.snapshot.readyDevices { Text(verbatim:"\(count) \(entry.snapshot.readyLabel ?? "READY")").font(.system(size:8,design:.monospaced)).foregroundStyle(accent) } }
            Text(entry.snapshot.lastCommand.capitalized).font(.system(size:family == .systemSmall ? 26:32,weight:.semibold,design:.rounded)).lineLimit(1).minimumScaleFactor(0.6)
            GeometryReader { geometry in
                ZStack(alignment:.leading) {
                    RoundedRectangle(cornerRadius:8).fill(.white.opacity(0.05))
                    RoundedRectangle(cornerRadius:8).fill(LinearGradient(colors:palette,startPoint:.leading,endPoint:.trailing)).frame(width:geometry.size.width*max(0,min(1,(entry.snapshot.brightness ?? 100)/100)))
                }
            }.frame(height:family == .systemSmall ? 14:22)
            Spacer(minLength:0)
            Text(entry.snapshot.gpuName).font(.system(size:11,weight:.medium)).lineLimit(2)
            HStack { Text(entry.snapshot.statusText ?? "Lighting commands").lineLimit(1);Spacer();if let value=entry.snapshot.brightness { Text("\(Int(value))%").monospacedDigit() } }.font(.system(size:9)).foregroundStyle(.secondary)
            if family == .systemMedium && entry.snapshot.updatedAt != .distantPast { Text(entry.snapshot.updatedAt,style:.relative).font(.system(size:8)).foregroundStyle(.secondary) }
        }.foregroundStyle(Color(red:0.91,green:0.94,blue:0.93)).padding(2)
        .containerBackground(for:.widget) { Color(red:0.035,green:0.047,blue:0.055) }
        .widgetURL(URL(string:"hackinfx://lighting"))
    }
}
@main struct HackinFXWidget:Widget {
    var body:some WidgetConfiguration {
        StaticConfiguration(kind:"HackinFXStatus",provider:Provider()) { WidgetView(entry:$0) }
        .configurationDisplayName("HackinFX").description("Lighting mode, colors, brightness, ready devices and GPU model. Command state, not live LED readback.").supportedFamilies([.systemSmall,.systemMedium]).contentMarginsDisabled()
    }
}
