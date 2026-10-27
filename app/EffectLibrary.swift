// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
struct LibraryEffect:Codable,Identifiable { let id:String;let name:String;let category:String;let symbol:String;let description:String;let palette:[String];let speed:Double;let scale:Double;let density:Double;let colors:Bool }
struct LibraryLook:Codable,Identifiable { let id:String;let name:String;let effect:String;let category:String;let palette:[String];let speed:Double;let scale:Double;let density:Double }
struct EffectCatalog:Codable { let schema:Int;let categories:[String];let effects:[LibraryEffect];let looks:[LibraryLook] }
struct CenterLayer:Codable,Equatable {
    var mode="twinkle";var palette=["9bed4b"];var brightness=100.0;var speed=65.0;var scale=1.0;var density=55.0;var reverse=false;var axis="x";var mapping="canvas";var blend="screen";var opacity=50.0
}

enum EffectLibrary {
    static let catalog:EffectCatalog = {
        guard let url=Bundle.main.url(forResource:"effects_catalog",withExtension:"json"),let data=try? Data(contentsOf:url),let catalog=try? JSONDecoder().decode(EffectCatalog.self,from:data),catalog.schema==1 else { return EffectCatalog(schema:1,categories:[],effects:[],looks:[]) }
        return catalog
    }()
    static func favoriteIDs(_ raw:String)->Set<String> {
        guard let data=raw.data(using:.utf8),let ids=try? JSONDecoder().decode([String].self,from:data) else { return [] };return Set(ids)
    }
    static func encodedFavorites(_ ids:Set<String>)->String { String(decoding:(try? JSONEncoder().encode(ids.sorted())) ?? Data("[]".utf8),as:UTF8.self) }
    static func effect(_ id:String)->LibraryEffect? { catalog.effects.first { $0.id==id } }
    static func palette(_ values:[String])->[[Double]] { values.map { let v=UInt32($0,radix:16) ?? 0;return [Double(v>>16&255),Double(v>>8&255),Double(v&255)] } }
}
enum EffectMath {
    static let tau=Double.pi*2
    static func fract(_ v:Double)->Double { v-floor(v) }
    static func noise(_ v:Double)->Double { fract(sin(v*12.9898+78.233)*43758.5453) }
    static func smooth(_ v:Double)->Double { let n=max(0,min(1,v));return n*n*(3-2*n) }
    static func field(_ x:Double,_ y:Double,_ t:Double)->Double { (sin(x*4.7+t*0.7)+cos(y*5.3-t*0.43)+sin((x+y)*3.1+t*0.31))/6+0.5 }
    static func composite(mode:String,palette:[[Double]],index:Int,u:Double,v:Double,coord:Double,time:Double,speed:Double,scale:Double,density:Double,reverse:Bool,brightness:Double,layers:[CenterLayer])->[Double] {
        var rgb=sample(mode:mode,palette:palette,index:index,u:u,v:v,coord:coord,time:time,speed:speed,scale:scale,density:density,reverse:reverse).map { max(0,min(255,($0*(layers.isEmpty ? brightness:100)/100).rounded(.toNearestOrEven))) }
        for layer in layers {
            let overlay=sample(mode:layer.mode,palette:EffectLibrary.palette(layer.palette),index:index,u:u,v:v,coord:layer.axis == "x" ? u:v,time:time,speed:layer.speed,scale:layer.scale,density:layer.density,reverse:layer.reverse).map { max(0,min(255,($0*layer.brightness/100).rounded(.toNearestOrEven))) }
            for k in 0..<3 {
                let a=rgb[k],b=overlay[k],opacity=layer.opacity/100
                let merged:Double
                switch layer.blend { case "add":merged=min(255,a+b);case "multiply":merged=a*b/255;case "normal":merged=b;default:merged=255-(255-a)*(255-b)/255 }
                rgb[k]=max(0,min(255,(a*(1-opacity)+merged*opacity).rounded(.toNearestOrEven)))
            }
        }
        if !layers.isEmpty { rgb=rgb.map { ($0*brightness/100).rounded(.toNearestOrEven) } }
        return rgb
    }
    static func sample(mode:String,palette:[[Double]],index:Int,u:Double,v:Double,coord:Double,time:Double,speed:Double,scale:Double=1,density:Double=55,reverse:Bool=false)->[Double] {
        guard !palette.isEmpty else { return [0,0,0] }
        let t=time*speed/100*(reverse ? -1.0:1.0),q=coord*scale,xx=(u-0.5)*scale,yy=(v-0.5)*scale
        let radius=hypot(xx,yy),angle=atan2(yy,xx)/tau,den=density/100,i=Double(index)
        func pal(_ f:Double,_ cycle:Bool=false)->[Double] {
            let p=cycle ? fract(f)*Double(palette.count):max(0,min(1,f))*Double(palette.count-1)
            let a=min(palette.count-1,Int(p)),b=cycle ? (a+1)%palette.count:min(palette.count-1,a+1),d=p-floor(p)
            return (0..<3).map { palette[a][$0]*(1-d)+palette[b][$0]*d }
        }
        func hsv(_ hue:Double,_ saturation:Double=0.8,_ value:Double=1)->[Double] {
            let h=fract(hue)*6,s=saturation,l=max(0,min(1,value)),f=h-floor(h)
            let p=l*(1-s),q=l*(1-s*f),t=l*(1-s*(1-f))
            let rgb:[[Double]]=[[l,t,p],[q,l,p],[p,l,t],[p,q,l],[t,p,l],[l,p,q]]
            return rgb[Int(h)%6].map {$0*255}
        }
        var rgb=palette[0],level=1.0
        switch mode {
        case "gradient":rgb=pal(q)
        case "spectrum":rgb=hsv(t*0.2)
        case "breathing":level=0.08+0.92*(0.5-0.5*cos(t*Double.pi))
        case "wave":rgb=pal(q+t*0.25,true)
        case "aurora":rgb=hsv(0.38+fract(q*0.28+t*0.06)*0.36,0.78,0.6+0.4*pow(sin(q*5+t),2))
        case "comet":level=exp(-fract(t*0.25-q)*12)
        case "twinkle":rgb=palette[index%palette.count];level=0.08+0.92*pow(max(0,sin(i*12.9898+q*78.233+t*3)),12+(55-density)*0.14)
        case "color shift":rgb=pal(t*0.12,true)
        case "rainbow wave":rgb=hsv(q*0.55-t*0.15,0.72)
        case "pulse":level=0.06+0.94*pow(0.5+0.5*sin(t*tau),3)
        case "heartbeat":let phase=fract(t*0.65);level=0.04+0.75*exp(-pow((phase-0.16)/0.055,2))+0.5*exp(-pow((phase-0.36)/0.075,2))
        case "scanner":level=0.025+0.975*exp(-pow((q-(0.5-0.5*cos(t*1.8)))/0.075,2))
        case "bounce":rgb=pal(t*0.05,true);level=0.02+0.98*exp(-pow((q-(1-abs(fract(t*0.24)*2-1)))/0.16,2))
        case "ripple":rgb=pal(radius-t*0.12,true);level=0.05+0.95*pow(0.5+0.5*cos(radius*18-t*4),5)
        case "orbit":level=0.03+0.97*exp(-(pow(xx-0.3*cos(t*2),2)+pow(yy-0.3*sin(t*2),2))/0.022)
        case "marquee":level=0.06+0.94*pow(0.5+0.5*cos(q*tau*(3+den*5)-t*3),8)
        case "chase":rgb=pal(fract(q*3-t*0.2),true);level=0.12+0.88*smooth(sin(q*tau*3-t*tau))
        case "fire":rgb=pal(max(0,min(1,0.23+0.62*field(u*scale,v*scale,t*2)+0.15*sin(i*2.3+t*6))));level=0.55+0.45*field(q,0,t*2)
        case "candle":rgb=pal(0.55+0.25*sin(t*3.4)+0.12*sin(t*8.7+i*0.14));level=0.55+0.25*sin(t*4.2)+0.12*sin(t*10.7+i*0.03)
        case "ocean":rgb=pal(0.5+0.25*sin(q*7-t*0.8)+0.2*cos(v*4+t*0.6));level=0.5+0.5*(0.5+0.5*sin(q*12-t*1.4))
        case "sunset":rgb=pal(0.5+0.4*sin(v*scale*2.5+t*0.12));level=0.55+0.45*smooth(1-v)
        case "ice":rgb=pal(field(u*scale*2,v*scale*2,t*0.35));level=0.45+0.55*pow(max(0,sin(i*4.31+q*7+t)),4)
        case "plasma":rgb=pal(field(u*scale*2,v*scale*2,t*1.2),true)
        case "nebula":rgb=pal(field(u*scale,v*scale,t*0.6));level=0.25+0.75*field(v*scale,u*scale,t*0.43)
        case "fog":rgb=pal(field(q,v,t*0.3));level=0.35+0.3*field(q,v,t*0.5)
        case "starfield":rgb=palette[index%palette.count];level=0.015+0.985*pow(max(0,sin(i*7.77+q*31+t*0.7)),36-24*den)
        case "fireflies":rgb=pal(noise(i+3));level=0.02+0.98*pow(max(0,sin(t*(0.4+noise(i)*0.8)+i*5.23)),10-6*den)
        case "meteor shower":level=0.015;for n in 0..<3 { let j=Double(n);level+=exp(-fract(t*(0.16+j*0.04)-q-j*0.31)*(14-j*2))*0.6 };rgb=pal(q+t*0.08,true)
        case "rain":let lane=floor(u*scale*10),drop=fract(t*(0.3+noise(lane)*0.35)+noise(lane+7)-v*scale);rgb=pal(noise(lane));level=0.015+0.985*exp(-drop*(22-12*den))
        case "digital rain":let lane=floor(u*scale*12),head=fract(t*(0.18+noise(lane)*0.2)+noise(lane+11)-v*scale);rgb=pal(1-head);level=0.01+0.99*exp(-head*(12-6*den))
        case "confetti":rgb=pal(noise(i*3+5),true);level=0.025+0.975*pow(max(0,sin(i*2.47+q*23+t*(1+noise(i)*2))),16-10*den)
        case "fireworks":let cycle=floor(t*0.35),phase=fract(t*0.35),cx=noise(cycle+2)-0.5,cy=noise(cycle+9)-0.5,distance=hypot(xx-cx*0.65,yy-cy*0.65);rgb=pal(noise(cycle+4),true);level=0.01+exp(-pow((distance-phase*0.85)/0.045,2))*(1-phase)*(0.3+0.7*noise(i+cycle))
        case "snow":rgb=pal(noise(i+1));level=0.03+0.97*pow(max(0,sin(i*3.19+q*9+t*0.7)),18-12*den)
        case "stripes":rgb=pal(q*(2+den*5)-t*0.12,true)
        case "checkerboard":let k=Int(floor(u*scale*6+t*0.4)+floor(v*scale*6));rgb=palette[(k%palette.count+palette.count)%palette.count];level=0.35+0.65*(0.5+0.5*cos(t+q))
        case "spiral":rgb=pal(angle*3+radius*4-t*0.18,true)
        case "pinwheel":rgb=pal(angle*5-t*0.15,true);level=0.2+0.8*(0.5+0.5*sin(angle*tau*5-t))
        case "vortex":rgb=pal(angle*2+radius*6-t*0.2,true);level=0.15+0.85*pow(0.5+0.5*sin(radius*22-t*3),2)
        case "radar":level=0.03+0.97*exp(-fract(t*0.16-angle)*10)*(0.4+0.6*min(1,radius*2))
        default:break
        }
        return rgb.map { $0*max(0,min(1,level)) }
    }
}
