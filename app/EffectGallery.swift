// SPDX-License-Identifier: GPL-2.0-or-later
import SwiftUI

struct EffectTexture:View {
    let scene:CenterScene
    let time:Double
    var columns=24
    var rows=6
    var body:some View {
        Canvas { context,size in
            let palette=EffectLibrary.palette(scene.palette),dx=size.width/Double(columns),dy=size.height/Double(rows)
            for row in 0..<rows { for column in 0..<columns {
                let u=Double(column)/Double(max(1,columns-1)),v=Double(row)/Double(max(1,rows-1)),index=row*columns+column
                let rgb=EffectMath.sample(mode:scene.mode,palette:palette,index:index,u:u,v:v,coord:scene.axis == "x" ? u:v,time:time,speed:scene.speed,scale:scene.scale,density:scene.density,reverse:scene.reverse)
                let level=scene.brightness/25500
                let color=Color(red:max(0,min(1,rgb[0]*level)),green:max(0,min(1,rgb[1]*level)),blue:max(0,min(1,rgb[2]*level)))
                let rect=CGRect(x:Double(column)*dx+1.5,y:Double(row)*dy+1.5,width:max(1,dx-3),height:max(1,dy-3))
                context.fill(Path(roundedRect:rect,cornerRadius:3),with:.color(color))
            } }
        }.background(Color.black.opacity(0.72)).clipShape(RoundedRectangle(cornerRadius:11)).accessibilityHidden(true)
    }
}
private struct GalleryEntry:Identifiable {
    let id:String
    let name:String
    let effect:LibraryEffect
    let scene:CenterScene
    let isLook:Bool
}
private struct GalleryCard:View {
    let entry:GalleryEntry
    let time:Double
    let selected:Bool
    let favorite:Bool
    let choose:()->Void
    let toggleFavorite:()->Void
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var hovered=false
    var body:some View {
        ZStack(alignment:.topTrailing) {
            Button(action:choose) {
                VStack(alignment:.leading,spacing:12) {
                    EffectTexture(scene:entry.scene,time:time).frame(height:96)
                    HStack(spacing:8) {
                        Image(systemName:entry.effect.symbol).foregroundStyle(CenterTheme.aqua)
                        Text(entry.name).font(.system(size:13,weight:.semibold)).lineLimit(1)
                        Spacer(minLength:0)
                        if selected { Image(systemName:"checkmark.circle.fill").foregroundStyle(CenterTheme.accent) }
                    }
                    Text(entry.isLook ? entry.effect.name+" · "+entry.effect.category:entry.effect.description).font(.system(size:10)).foregroundStyle(CenterTheme.muted).lineLimit(2).frame(height:28,alignment:.topLeading)
                }.padding(13).background(selected ? CenterTheme.accent.opacity(0.07):CenterTheme.surface).clipShape(RoundedRectangle(cornerRadius:17)).overlay(RoundedRectangle(cornerRadius:17).stroke(selected ? CenterTheme.accent.opacity(0.6):.white.opacity(hovered ? 0.18:0.065),lineWidth:1))
            }.buttonStyle(PressFeedbackStyle()).accessibilityLabel("Use "+entry.name).help("Send this look to selected compatible devices. Brightness stays unchanged.")
            Button(action:toggleFavorite) { Image(systemName:favorite ? "star.fill":"star").font(.system(size:12,weight:.medium)).foregroundStyle(favorite ? CenterTheme.accent:.white.opacity(0.8)).padding(9).background(.black.opacity(0.55)).clipShape(Circle()) }.buttonStyle(.plain).padding(19).accessibilityLabel((favorite ? "Remove ":"Favorite ")+entry.name)
        }.offset(y:hovered && !reduceMotion ? -2:0).shadow(color:CenterTheme.aqua.opacity(hovered ? 0.08:0),radius:14,y:5).onHover { hovered=$0 }.animation(reduceMotion ? nil:.easeOut(duration:0.18),value:hovered)
    }
}
struct EffectGallery:View {
    @ObservedObject var center:CenterModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @AppStorage("hackinfx-effect-favorites") private var favorites="[]"
    @State private var tab="Effects"
    @State private var category="All"
    @State private var search=""
    @State private var favoritesOnly=false
    private var favoriteIDs:Set<String> { EffectLibrary.favoriteIDs(favorites) }
    private func toggleFavorite(_ id:String) { var values=favoriteIDs;if values.contains(id) { values.remove(id) } else { values.insert(id) };favorites=EffectLibrary.encodedFavorites(values) }
    private func scene(_ effect:LibraryEffect,_ look:LibraryLook?=nil)->CenterScene {
        var value=CenterScene();value.mode=effect.id;value.palette=look?.palette ?? effect.palette;value.speed=look?.speed ?? effect.speed;value.scale=look?.scale ?? effect.scale;value.density=look?.density ?? effect.density;value.brightness=100;return value
    }
    private var entries:[GalleryEntry] {
        let library=EffectLibrary.catalog
        let all:[GalleryEntry]
        if tab=="Looks" { all=library.looks.compactMap { look in guard let effect=EffectLibrary.effect(look.effect) else { return nil };return GalleryEntry(id:"look:"+look.id,name:look.name,effect:effect,scene:scene(effect,look),isLook:true) } }
        else if tab=="Saved" { all=center.state.scenes.compactMap { saved in guard let effect=EffectLibrary.effect(saved.config.mode) else { return nil };return GalleryEntry(id:"saved:"+saved.name,name:saved.name,effect:effect,scene:saved.config,isLook:true) } }
        else { all=library.effects.map { GalleryEntry(id:"effect:"+$0.id,name:$0.name,effect:$0,scene:scene($0),isLook:false) } }
        return all.filter { entry in
            (category=="All" || entry.effect.category==category) && (!favoritesOnly || favoriteIDs.contains(entry.id)) && (search.isEmpty || (entry.name+" "+entry.effect.name+" "+entry.effect.description+" "+entry.effect.category).localizedCaseInsensitiveContains(search))
        }
    }
    private func choose(_ entry:GalleryEntry) {
        if entry.id.hasPrefix("saved:") { center.scene=entry.scene;return }
        var value=entry.scene;value.brightness=center.scene.brightness;value.mapping=center.scene.mapping;value.axis=center.scene.axis;value.fps=center.scene.fps;value.sync_policy=center.scene.sync_policy;value.synchronized=center.scene.synchronized;center.scene=value
    }
    private func selected(_ entry:GalleryEntry)->Bool { if entry.id.hasPrefix("saved:") { return center.scene==entry.scene };return center.scene.mode==entry.scene.mode && (!entry.isLook || (center.scene.palette==entry.scene.palette && center.scene.speed==entry.scene.speed && center.scene.scale==entry.scene.scale && center.scene.density==entry.scene.density && center.scene.reverse==entry.scene.reverse)) }
    private var filterBar:some View {
        VStack(alignment:.leading,spacing:14) {
            HStack(spacing:14) {
                Picker("Library",selection:$tab) { Text("Effects · \(EffectLibrary.catalog.effects.count)").tag("Effects");Text("Looks · \(EffectLibrary.catalog.looks.count)").tag("Looks");Text("Saved · \(center.state.scenes.count)").tag("Saved") }.pickerStyle(.segmented).frame(maxWidth:440)
                HStack { Image(systemName:"magnifyingglass").foregroundStyle(CenterTheme.muted);TextField("Search effects and looks",text:$search).textFieldStyle(.plain);if !search.isEmpty { Button { search="" } label: { Image(systemName:"xmark.circle.fill") }.buttonStyle(.plain) } }.font(.system(size:12)).padding(10).background(CenterTheme.elevated).clipShape(RoundedRectangle(cornerRadius:9))
                Button { favoritesOnly.toggle() } label: { Label("Favorites",systemImage:favoritesOnly ? "star.fill":"star").foregroundStyle(favoritesOnly ? CenterTheme.accent:CenterTheme.muted) }.buttonStyle(PressFeedbackStyle())
            }
            ScrollView(.horizontal,showsIndicators:false) { HStack(spacing:8) { ForEach(["All"]+EffectLibrary.catalog.categories,id:\.self) { name in Button { category=name } label: { Text(name).font(.system(size:11,weight:.medium)).padding(.horizontal,14).padding(.vertical,8).foregroundStyle(category==name ? CenterTheme.accent:CenterTheme.muted).background(category==name ? CenterTheme.accent.opacity(0.1):CenterTheme.surface).clipShape(Capsule()).overlay(Capsule().stroke(category==name ? CenterTheme.accent.opacity(0.3):.clear,lineWidth:1)) }.buttonStyle(PressFeedbackStyle()) } } }
        }
    }
    private func paletteColor(_ index:Int)->Binding<Color> { Binding(get:{ guard center.scene.palette.indices.contains(index) else { return Color.clear };let p=EffectLibrary.palette(center.scene.palette)[index];return Color(red:p[0]/255,green:p[1]/255,blue:p[2]/255) },set:{ color in guard center.scene.palette.indices.contains(index) else { return };let value=NSColor(color).usingColorSpace(.sRGB) ?? .white;center.scene.palette[index]=[value.redComponent,value.greenComponent,value.blueComponent].map { String(format:"%02x",Int(($0*255).rounded())) }.joined() }) }
    private var tuning:some View {
        CenterPanel {
            VStack(alignment:.leading,spacing:15) {
                HStack { Label(EffectLibrary.effect(center.scene.mode)?.name ?? center.scene.mode.capitalized,systemImage:EffectLibrary.effect(center.scene.mode)?.symbol ?? "sparkles").font(.system(size:17,weight:.semibold));Spacer();Text("CURRENT LOOK").font(.system(size:8,design:.monospaced)).tracking(1.5).foregroundStyle(CenterTheme.aqua) }
                HStack(spacing:22) {
                    VStack(alignment:.leading,spacing:10) {
                        HStack { Text("Speed").frame(width:62,alignment:.leading);Slider(value:$center.scene.speed,in:1...100).disabled(["static","gradient"].contains(center.scene.mode));Text("\(Int(center.scene.speed))%").monospacedDigit().frame(width:38) }
                        HStack { Text("Scale").frame(width:62,alignment:.leading);Slider(value:$center.scene.scale,in:0.25...4).disabled(["static","spectrum","breathing","color shift","pulse","heartbeat"].contains(center.scene.mode));Text(String(format:"%.1f×",center.scene.scale)).monospacedDigit().frame(width:38) }
                    }
                    VStack(alignment:.leading,spacing:10) {
                        HStack { Text("Brightness").frame(width:70,alignment:.leading);Slider(value:$center.scene.brightness,in:0...100);Text("\(Int(center.scene.brightness))%").monospacedDigit().frame(width:38) }
                        HStack { Text("Density").frame(width:70,alignment:.leading);Slider(value:$center.scene.density,in:0...100).disabled(!["twinkle","starfield","fireflies","rain","digital rain","confetti","snow","marquee","stripes"].contains(center.scene.mode));Toggle("Reverse",isOn:$center.scene.reverse).toggleStyle(.checkbox).disabled(["static","gradient"].contains(center.scene.mode)) }
                    }
                }.font(.system(size:11)).foregroundStyle(CenterTheme.muted)
                HStack(spacing:12) {
                    if EffectLibrary.effect(center.scene.mode)?.colors != false { ForEach(Array(center.scene.palette.indices),id:\.self) { i in ColorPicker("\(i+1)",selection:paletteColor(i),supportsOpacity:false).labelsHidden().help("Palette color \(i+1)") };Button { if center.scene.palette.count<8 { center.scene.palette.append("42d6ce") } } label: { Image(systemName:"plus") }.disabled(center.scene.palette.count>=8);Button { if center.scene.palette.count>1 { center.scene.palette.removeLast() } } label: { Image(systemName:"minus") }.disabled(center.scene.palette.count<=1) }
                    Spacer(minLength:8);TextField("Save this look as…",text:$center.sceneName).textFieldStyle(.roundedBorder).frame(maxWidth:220);Button("Save look",action:center.saveScene).disabled(center.busy || !center.online || center.sceneName.trimmingCharacters(in:.whitespaces).isEmpty)
                }
                if !center.sceneCompatible && !center.selected.isEmpty { Text("Some selected devices cannot stream this effect. They keep their last color.").font(.system(size:11)).foregroundStyle(.orange) }
            }
        }
    }
    var body:some View {
        VStack(alignment:.leading,spacing:24) {
            HStack(alignment:.top) {
                VStack(alignment:.leading,spacing:10) { Text("EXPLORE / CREATE").font(.system(size:9,weight:.semibold,design:.monospaced)).tracking(2).foregroundStyle(CenterTheme.accent);Text("Effect Gallery").font(.system(size:35,weight:.semibold,design:.rounded));Text("40 effects. 80 curated looks. Select a card to control your selected devices.").font(.system(size:12)).foregroundStyle(CenterTheme.muted) }
                Spacer();VStack(alignment:.trailing,spacing:6) { Text("120").font(.system(size:36,weight:.light,design:.rounded)).foregroundStyle(CenterTheme.accent);Text("BUILT-IN OPTIONS").font(.system(size:8,design:.monospaced)).tracking(1).foregroundStyle(CenterTheme.muted) }
            }
            tuning
            filterBar
            Text("\(entries.count) \(tab.lowercased())"+(favoritesOnly ? " · favorites":"")).font(.system(size:10,design:.monospaced)).foregroundStyle(CenterTheme.muted)
            TimelineView(.animation(minimumInterval:1.0/12,paused:reduceMotion)) { context in
                let time=reduceMotion ? 0:context.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy:3600)
                LazyVGrid(columns:[GridItem(.adaptive(minimum:225),spacing:16)],spacing:16) { ForEach(entries) { entry in GalleryCard(entry:entry,time:time,selected:selected(entry),favorite:favoriteIDs.contains(entry.id),choose:{choose(entry)},toggleFavorite:{toggleFavorite(entry.id)}) } }
            }
            if entries.isEmpty { VStack(spacing:12) { Image(systemName:tab=="Saved" ? "square.and.arrow.down":"magnifyingglass").font(.system(size:26,weight:.light));Text(tab=="Saved" && center.state.scenes.isEmpty ? "Save a look to keep it here.":"No matching looks. Try another search or category.").font(.system(size:13)) }.foregroundStyle(CenterTheme.muted).frame(maxWidth:.infinity).padding(40) }
            Text("Animated illustrations · not live LED feedback. Device transport limits still apply.").font(.system(size:10)).foregroundStyle(CenterTheme.muted)
        }
    }
}
