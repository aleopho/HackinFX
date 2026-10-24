// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
let size=1024
let context=CGContext(data:nil,width:size,height:size,bitsPerComponent:8,bytesPerRow:size*4,space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue)!
context.translateBy(x:0,y:1024);context.scaleBy(x:1,y:-1)
let background=CGColor(red:0.035,green:0.047,blue:0.055,alpha:1)
context.setFillColor(background)
context.addPath(CGPath(roundedRect:CGRect(x:64,y:64,width:896,height:896),cornerWidth:196,cornerHeight:196,transform:nil));context.fillPath()
context.setStrokeColor(CGColor(red:0.48,green:0.61,blue:0.59,alpha:0.16));context.setLineWidth(2)
context.addPath(CGPath(roundedRect:CGRect(x:193,y:193,width:638,height:638),cornerWidth:84,cornerHeight:84,transform:nil));context.strokePath()
func hsv(_ hue:Double)->CGColor {
 let h=hue*6,i=Int(h),f=CGFloat(h-Double(i)),p:CGFloat=0.24,q:CGFloat=1-0.76*f,t:CGFloat=0.24+0.76*f
 let rgb:[CGFloat]
 switch i%6 {case 0:rgb=[1,t,p];case 1:rgb=[q,1,p];case 2:rgb=[p,1,t];case 3:rgb=[p,q,1];case 4:rgb=[t,p,1];default:rgb=[1,p,q]}
 return CGColor(red:rgb[0]*0.82,green:rgb[1]*0.82,blue:rgb[2]*0.82,alpha:1)
}
context.setLineCap(.round)
for i in 0..<240 {
 let a=Double(i)*2*Double.pi/240,b=Double(i+1)*2*Double.pi/240
 let color=hsv((Double(i)/240+0.24).truncatingRemainder(dividingBy:1));context.saveGState();context.setStrokeColor(color);context.setShadow(offset:.zero,blur:17,color:color.copy(alpha:0.40));context.setLineWidth(12);context.addArc(center:CGPoint(x:512,y:512),radius:270,startAngle:a,endAngle:b,clockwise:false);context.strokePath();context.restoreGState()
}
context.setStrokeColor(CGColor(red:0.74,green:0.84,blue:0.80,alpha:0.68));context.setFillColor(CGColor(red:0.43,green:0.57,blue:0.53,alpha:0.055));context.setLineWidth(6)
for i in 0..<7 {
 context.saveGState();context.translateBy(x:512,y:512);context.rotate(by:CGFloat(i)*2*CGFloat.pi/7)
 let path=CGMutablePath();path.move(to:CGPoint(x:40,y:-45));path.addCurve(to:CGPoint(x:193,y:-117),control1:CGPoint(x:84,y:-137),control2:CGPoint(x:141,y:-167));path.addCurve(to:CGPoint(x:194,y:18),control1:CGPoint(x:229,y:-79),control2:CGPoint(x:239,y:-17));path.addCurve(to:CGPoint(x:55,y:32),control1:CGPoint(x:153,y:57),control2:CGPoint(x:91,y:18));path.addCurve(to:CGPoint(x:40,y:-45),control1:CGPoint(x:47,y:5),control2:CGPoint(x:41,y:-10));path.closeSubpath();context.addPath(path);context.drawPath(using:.fillStroke);context.restoreGState()
}
context.setFillColor(background);context.fillEllipse(in:CGRect(x:454,y:454,width:116,height:116));context.setStrokeColor(CGColor(red:0.76,green:0.88,blue:0.82,alpha:0.9));context.setLineWidth(6);context.strokeEllipse(in:CGRect(x:454,y:454,width:116,height:116))
for x in [229,795] {for y in [229,795] {context.setStrokeColor(CGColor(red:0.51,green:0.65,blue:0.60,alpha:0.4));context.setLineWidth(3);context.strokeEllipse(in:CGRect(x:x-8,y:y-8,width:16,height:16))}}
let output=URL(fileURLWithPath:CommandLine.arguments[1]);let destination=CGImageDestinationCreateWithURL(output as CFURL,UTType.png.identifier as CFString,1,nil)!
CGImageDestinationAddImage(destination,context.makeImage()!,nil)
if !CGImageDestinationFinalize(destination){exit(1)}
