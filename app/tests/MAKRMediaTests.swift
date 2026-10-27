import Foundation
@main struct MAKRMediaTests {
    static func main(){
        var report=[UInt8](repeating:0,count:512);report[1]=5;report[4]=1;precondition(MAKRKnob.direction(report)==1)
        report[4]=255;precondition(MAKRKnob.direction(report)==(-1))
        report[4]=0;precondition(MAKRKnob.direction(report)==0)
        report[1]=2;report[4]=1;precondition(MAKRKnob.direction(report)==0)
        precondition(MAKRKnob.direction([0,5,0,0])==0);precondition(MAKRKnob.direction([UInt8](repeating:1,count:513))==0)
        print("MAKR dial parser accepts only documented direction events; no audio or HID devices opened")
    }
}
