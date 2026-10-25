// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation

enum ReleaseVersion {
    static func components(_ value:String)->[Int]? {
        let text=value.hasPrefix("v") ? String(value.dropFirst()):value
        let parts=text.split(separator:".",omittingEmptySubsequences:false)
        guard (2...3).contains(parts.count) else { return nil }
        var result=[Int]()
        for part in parts { guard !part.isEmpty,part.allSatisfy({$0.isASCII && $0.isNumber}),let number=Int(part),number>=0 else { return nil };result.append(number) }
        while result.count<3 { result.append(0) };return result
    }
    static func isNewer(_ candidate:String,than installed:String)->Bool {
        guard let a=components(candidate),let b=components(installed) else { return false }
        return b.lexicographicallyPrecedes(a)
    }
}
