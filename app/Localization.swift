// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
import SwiftUI

struct AppLanguage:Identifiable { let id:String;let name:String }
final class LocalizationCatalog {
    let english:[String:String]
    let translated:[String:String]
    private var folded=[String:String]()
    private var templates=[(String,String,NSRegularExpression)]()
    private var cache=[String:String]()
    private let lock=NSLock()
    init(directory:URL,language:String) {
        func load(_ code:String)->[String:String] { guard let data=try? Data(contentsOf:directory.appendingPathComponent(code+".json")),let values=try? JSONDecoder().decode([String:String].self,from:data) else { return [:] };return values }
        english=load("en");translated=load(language)
        let slot=try! NSRegularExpression(pattern:"\\{[0-9]+\\}")
        for key in english.keys.sorted() {
            let value=translated[key] ?? key
            if folded[key.lowercased()]==nil { folded[key.lowercased()]=value }
            let ns=key as NSString;let matches=slot.matches(in:key,range:NSRange(location:0,length:ns.length))
            guard !matches.isEmpty else { continue }
            var pattern="^",position=0;var literals=0;var prefix=""
            for (i,m) in matches.enumerated() {
                let part=ns.substring(with:NSRange(location:position,length:m.range.location-position));if i==0 { prefix=part };literals+=part.count;pattern+=NSRegularExpression.escapedPattern(for:part)+"(.*?)";position=m.range.location+m.range.length
            }
            let tail=ns.substring(from:position);literals+=tail.count;pattern+=NSRegularExpression.escapedPattern(for:tail)+"$"
            if literals>=4,let regex=try? NSRegularExpression(pattern:pattern,options:[.dotMatchesLineSeparators]) { templates.append((prefix,key,regex)) }
        }
        templates.sort { $0.1.count>$1.1.count }
    }
    func text(_ source:String)->String {
        lock.lock();defer { lock.unlock() }
        if let result=cache[source] { return result }
        var result=translated[source] ?? folded[source.lowercased()] ?? source
        if result==source && translated[source]==nil {
            let ns=source as NSString
            for (prefix,key,regex) in templates where source.hasPrefix(prefix) {
                guard let match=regex.firstMatch(in:source,range:NSRange(location:0,length:ns.length)) else { continue }
                var template=translated[key] ?? key
                let token=try! NSRegularExpression(pattern:"\\{([0-9]+)\\}")
                let raw=template as NSString
                for m in token.matches(in:template,range:NSRange(location:0,length:raw.length)).reversed() {
                    let index=Int(raw.substring(with:m.range(at:1))) ?? -1
                    if index>=0 && index+1<match.numberOfRanges,let range=Range(m.range,in:template) { template.replaceSubrange(range,with:ns.substring(with:match.range(at:index+1))) }
                }
                result=template;break
            }
        }
        if source==source.uppercased() && source != source.lowercased() { result=result.uppercased() }
        let leading=String(source.prefix {$0.isWhitespace}),trailing=String(source.reversed().prefix {$0.isWhitespace}.reversed())
        if !leading.isEmpty && !result.hasPrefix(leading) { result=leading+result }
        if !trailing.isEmpty && !result.hasSuffix(trailing) { result+=trailing }
        if cache.count>4096 { cache.removeAll(keepingCapacity:true) };cache[source]=result;return result
    }
}
final class AppLocalization:ObservableObject {
    static let languages:[AppLanguage] = [
        .init(id:"en",name:"English"),.init(id:"de",name:"Deutsch"),.init(id:"fr",name:"Français"),.init(id:"es",name:"Español"),.init(id:"it",name:"Italiano"),.init(id:"pt-BR",name:"Português (Brasil)"),.init(id:"pt-PT",name:"Português (Portugal)"),.init(id:"nl",name:"Nederlands"),.init(id:"pl",name:"Polski"),.init(id:"cs",name:"Čeština"),.init(id:"sv",name:"Svenska"),.init(id:"tr",name:"Türkçe"),.init(id:"uk",name:"Українська"),.init(id:"ru",name:"Русский"),.init(id:"ar",name:"العربية"),.init(id:"hi",name:"हिन्दी"),.init(id:"id",name:"Bahasa Indonesia"),.init(id:"vi",name:"Tiếng Việt"),.init(id:"ja",name:"日本語"),.init(id:"ko",name:"한국어"),.init(id:"zh-Hans",name:"简体中文"),.init(id:"zh-Hant",name:"繁體中文")]
    static let shared=AppLocalization()
    @Published var selection:String { didSet { UserDefaults.standard.set(selection,forKey:"HackinFXLanguage");reload() } }
    private(set) var catalog:LocalizationCatalog
    var identifier:String {
        if selection != "system",Self.languages.contains(where:{$0.id==selection}) { return selection }
        let available=Self.languages.map {$0.id}
        return Bundle.preferredLocalizations(from:available,forPreferences:Locale.preferredLanguages).first ?? "en"
    }
    var rtl:Bool { identifier=="ar" }
    private static var directory:URL { Bundle.main.resourceURL!.appendingPathComponent("Localization",isDirectory:true) }
    init() {
        selection=ProcessInfo.processInfo.environment["HACKINFX_RENDER_LANGUAGE"] ?? UserDefaults.standard.string(forKey:"HackinFXLanguage") ?? "system"
        catalog=LocalizationCatalog(directory:Self.directory,language:"en");reload()
    }
    private func reload() { catalog=LocalizationCatalog(directory:Self.directory,language:identifier) }
}
enum L10n { static func text(_ value:String)->String { AppLocalization.shared.catalog.text(value) } }
