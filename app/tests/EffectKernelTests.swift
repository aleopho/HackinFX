// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
struct EffectCase:Decodable { let mode:String;let palette:[[Double]];let index:Int;let u:Double;let v:Double;let coord:Double;let time:Double;let speed:Double;let scale:Double;let density:Double;let reverse:Bool;let expected:[Double] }
@main struct EffectKernelTests {
    static func main()throws {
        let cases=try JSONDecoder().decode([EffectCase].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
        for c in cases {
            let actual=EffectMath.sample(mode:c.mode,palette:c.palette,index:c.index,u:c.u,v:c.v,coord:c.coord,time:c.time,speed:c.speed,scale:c.scale,density:c.density,reverse:c.reverse)
            guard zip(actual,c.expected).allSatisfy({ abs($0-$1)<0.1 && $0.isFinite }) else { fatalError("Preview diverged from hardware renderer: \(c.mode) at \(c.time)") }
        }
        print("\(cases.count) cross-language effect samples match the hardware renderer")
    }
}
