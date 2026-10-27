// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
import SwiftUI
import WidgetKit
struct Entry:TimelineEntry { let date:Date;let snapshot:WidgetSnapshot }
struct Provider:TimelineProvider {
    func placeholder(in context:Context)->Entry { Entry(date:Date(),snapshot:WidgetSnapshot(schema:2,appName:"HackinFX",effect:"Twinkle",activeDevices:8,running:true,colors:["9bed4b"],brightness:75,updatedAt:Date())) }
    func getSnapshot(in context:Context,completion:@escaping(Entry)->Void) { if context.isPreview { completion(placeholder(in:context)) } else { WidgetSnapshot.fetch { completion(Entry(date:Date(),snapshot:$0)) } } }
    func getTimeline(in context:Context,completion:@escaping(Timeline<Entry>)->Void) { WidgetSnapshot.fetch { completion(Timeline(entries:[Entry(date:Date(),snapshot:$0)],policy:.after(Date().addingTimeInterval(60)))) } }
}
struct WidgetView:View {
    @Environment(\.widgetFamily) var family
    let entry:Entry
    private let accent=Color(red:0.61,green:0.93,blue:0.29)
    private var palette:[Color] { entry.snapshot.colors.compactMap { hex in guard let rgb=UInt32(hex,radix:16) else { return nil };return Color(red:Double(rgb>>16&255)/255,green:Double(rgb>>8&255)/255,blue:Double(rgb&255)/255) } }
    var body:some View {
        VStack(alignment:.leading,spacing:12) {
            HStack(spacing:7) { Image(systemName:"fanblades").foregroundStyle(accent);Text("HackinFX").font(.system(size:15,weight:.bold,design:.rounded));Spacer();Circle().fill(entry.snapshot.activeDevices>0 ? accent:.gray).frame(width:5,height:5) }
            Text(entry.snapshot.effect).font(.system(size:family == .systemSmall ? 25:31,weight:.semibold,design:.rounded)).lineLimit(1).minimumScaleFactor(0.6)
            HStack(spacing:4) { ForEach(0..<24,id:\.self) { i in RoundedRectangle(cornerRadius:3).fill((palette.isEmpty ? accent:palette[i%palette.count]).opacity(entry.snapshot.activeDevices>0 ? 0.85:0.12)).frame(height:8+CGFloat(i%4)*3) } }.frame(height:20)
            Spacer(minLength:0)
            HStack(alignment:.firstTextBaseline,spacing:7) { Text("\(entry.snapshot.activeDevices)").font(.system(size:25,weight:.semibold,design:.rounded)).monospacedDigit().foregroundStyle(accent);Text("active devices").font(.system(size:11,weight:.medium));Spacer();if family == .systemMedium { Text(entry.snapshot.updatedAt == .distantPast ? "Open HackinFX":entry.snapshot.running ? "LIVE CONTROL":"LAST APPLIED").font(.system(size:8,design:.monospaced)).foregroundStyle(.secondary) } }
        }.padding(16).foregroundStyle(Color(red:0.91,green:0.94,blue:0.93)).containerBackground(for:.widget) { Color(red:0.035,green:0.047,blue:0.055) }.widgetURL(URL(string:"hackinfx://lighting"))
    }
}
@main struct HackinFXWidget:Widget {
    var body:some WidgetConfiguration { StaticConfiguration(kind:"HackinFXStatus",provider:Provider()) { WidgetView(entry:$0) }.configurationDisplayName("HackinFX").description("Current effect and devices with successfully applied lighting. Updates are scheduled by macOS.").supportedFamilies([.systemSmall,.systemMedium]).contentMarginsDisabled() }
}
