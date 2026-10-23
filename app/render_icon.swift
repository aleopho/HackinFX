import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
let size = 1024
let context = CGContext(data:nil,width:size,height:size,bitsPerComponent:8,bytesPerRow:size*4,space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue)!
// SVG-like top-left coordinates, rendered without a GUI session.
context.translateBy(x:0,y:1024);context.scaleBy(x:1,y:-1)
let lime = CGColor(red:186/255,green:218/255,blue:139/255,alpha:1)
context.setFillColor(CGColor(red:22/255,green:27/255,blue:28/255,alpha:1))
context.addPath(CGPath(roundedRect:CGRect(x:64,y:64,width:896,height:896),cornerWidth:196,cornerHeight:196,transform:nil));context.fillPath()
context.setStrokeColor(lime);context.setLineWidth(18);context.setLineCap(.round);context.setLineJoin(.round)
context.addPath(CGPath(roundedRect:CGRect(x:217,y:344,width:616,height:326),cornerWidth:36,cornerHeight:36,transform:nil));context.strokePath()
func line(_ points:[CGPoint]) { context.beginPath();context.move(to:points[0]);for p in points.dropFirst(){context.addLine(to:p)};context.strokePath() }
line([CGPoint(x:182,y:314),CGPoint(x:182,y:700)])
for y in [314,700] {line([CGPoint(x:164,y:y),CGPoint(x:200,y:y)])}
line([CGPoint(x:248,y:702),CGPoint(x:598,y:702)])
line([CGPoint(x:616,y:670),CGPoint(x:616,y:702)])
line([CGPoint(x:654,y:670),CGPoint(x:654,y:702),CGPoint(x:741,y:702)])
line([CGPoint(x:239,y:638),CGPoint(x:809,y:638)])
for x in [388,662] {
 for radius in [106,24] { context.strokeEllipse(in:CGRect(x:x-radius,y:507-radius,width:radius*2,height:radius*2)) }
 context.setLineWidth(13)
 for points in [[CGPoint(x:x,y:477),CGPoint(x:x-21,y:423)],[CGPoint(x:x+30,y:507),CGPoint(x:x+84,y:486)],[CGPoint(x:x,y:537),CGPoint(x:x+21,y:591)],[CGPoint(x:x-30,y:507),CGPoint(x:x-84,y:528)]] {line(points)}
 context.setLineWidth(18)
}
context.setFillColor(lime)
for x in stride(from:286,through:518,by:29) {context.addPath(CGPath(roundedRect:CGRect(x:x,y:695,width:13,height:36),cornerWidth:4,cornerHeight:4,transform:nil));context.fillPath()}
let output = URL(fileURLWithPath:CommandLine.arguments[1])
let destination = CGImageDestinationCreateWithURL(output as CFURL,UTType.png.identifier as CFString,1,nil)!
CGImageDestinationAddImage(destination,context.makeImage()!,nil)
if !CGImageDestinationFinalize(destination) {exit(1)}
