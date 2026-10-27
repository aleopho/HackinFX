import Foundation
struct CompositionCase:Decodable {
    let mode:String;let palette:[[Double]];let index:Int;let u:Double;let v:Double;let time:Double;let brightness:Double;let layers:[CenterLayer];let expected:[Double]
}
@main struct CompositionKernelTests {
    static func main()throws {
        let cases=try JSONDecoder().decode([CompositionCase].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
        for c in cases {
            let rgb=EffectMath.composite(mode:c.mode,palette:c.palette,index:c.index,u:c.u,v:c.v,coord:c.u,time:c.time,speed:65,scale:1,density:55,reverse:false,brightness:c.brightness,layers:c.layers)
            precondition(zip(rgb,c.expected).allSatisfy { abs($0-$1)<=1 },"Composition differs from Python hardware kernel")
        }
        print("\(cases.count) layer composition samples match the hardware renderer")
    }
}
