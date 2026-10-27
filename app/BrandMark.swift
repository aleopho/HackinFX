// SPDX-License-Identifier: GPL-3.0-or-later
import CoreGraphics

/// Code-owned, interlaced orbital mark. Scales cleanly from menu bar to app icon.
func drawHackinFXMark(_ context:CGContext,center:CGPoint,radius:CGFloat,weight:CGFloat,color:CGColor,background:CGColor?) {
    context.saveGState();context.translateBy(x:center.x,y:center.y)
    context.setLineCap(.round);context.setLineJoin(.round)
    for (index,angle) in [CGFloat.pi/4,-CGFloat.pi/4].enumerated() {
        context.saveGState();context.rotate(by:angle)
        let rect=CGRect(x:-radius,y:-radius*0.39,width:radius*2,height:radius*0.78)
        if index==1 {
            context.saveGState();if let background=background { context.setStrokeColor(background) } else { context.setBlendMode(.clear) }
            context.setLineWidth(weight*1.6);context.strokeEllipse(in:rect);context.restoreGState()
        }
        context.setStrokeColor(color);context.setLineWidth(weight);context.strokeEllipse(in:rect);context.restoreGState()
    }
    context.saveGState();if let background=background { context.setFillColor(background) } else { context.setBlendMode(.clear) }
    context.fillEllipse(in:CGRect(x:-radius*0.31,y:-radius*0.31,width:radius*0.62,height:radius*0.62));context.restoreGState()
    context.setStrokeColor(color);context.setLineWidth(weight*0.82);context.strokeEllipse(in:CGRect(x:-radius*0.22,y:-radius*0.22,width:radius*0.44,height:radius*0.44))
    context.setFillColor(color);context.fillEllipse(in:CGRect(x:-radius*0.085,y:-radius*0.085,width:radius*0.17,height:radius*0.17));context.restoreGState()
}
