// SPDX-License-Identifier: GPL-3.0-or-later
import Foundation
import CoreGraphics
import CoreText
import ImageIO
import UniformTypeIdentifiers

@main struct RenderBrandIcon {
    static func main() {
        let size=1024
        let context=CGContext(data:nil,width:size,height:size,bitsPerComponent:8,bytesPerRow:size*4,space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue)!
        context.translateBy(x:0,y:1024);context.scaleBy(x:1,y:-1)
        let black=CGColor(red:0.012,green:0.016,blue:0.02,alpha:1),white=CGColor(red:0.97,green:0.985,blue:0.98,alpha:1)
        context.setFillColor(black);context.addPath(CGPath(roundedRect:CGRect(x:64,y:64,width:896,height:896),cornerWidth:196,cornerHeight:196,transform:nil));context.fillPath()
        drawHackinFXMark(context,center:CGPoint(x:512,y:420),radius:345,weight:46,color:white,background:black)
        let font=CTFontCreateWithName("HelveticaNeue-Bold" as CFString,140,nil)
        let line=CTLineCreateWithAttributedString(NSAttributedString(string:"FX",attributes:[NSAttributedString.Key(kCTFontAttributeName as String):font,NSAttributedString.Key(kCTForegroundColorAttributeName as String):white,NSAttributedString.Key(kCTKernAttributeName as String):16]))
        let width=CTLineGetTypographicBounds(line,nil,nil,nil)
        context.textMatrix=CGAffineTransform(scaleX:1,y:-1);context.textPosition=CGPoint(x:(1024-width)/2,y:858);CTLineDraw(line,context)
        let output=URL(fileURLWithPath:CommandLine.arguments[1]);let destination=CGImageDestinationCreateWithURL(output as CFURL,UTType.png.identifier as CFString,1,nil)!
        CGImageDestinationAddImage(destination,context.makeImage()!,nil);if !CGImageDestinationFinalize(destination){exit(1)}
    }
}
