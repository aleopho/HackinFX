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
    static func cloud(_ x:Double,_ y:Double,_ t:Double)->Double { 0.65*field(x,y,t)+0.35*field(x*2.03+1.7,y*2.03-2.1,t*1.37) }
    static func bell(_ p:Double,_ width:Double)->Double { exp(-pow(sin(Double.pi*p)/width,2)) }
    static func trail(_ p:Double,_ sharpness:Double)->Double { let phase=fract(p);return exp(-phase*sharpness)*smooth(phase/0.12)*smooth((1-phase)/0.12)*2.4 }
    static func spark(_ seed:Double,_ t:Double,_ density:Double,_ rate:Double)->Double { let phase=t*rate*(0.7+noise(seed)*0.6)+noise(seed+17)*tau;return pow(smooth((0.5+0.5*sin(phase)-(0.55-0.30*density))/(0.45+0.30*density)),2) }
    static func heat(_ x:Double,_ y:Double,_ t:Double)->Double { max(0,min(1,0.12+0.66*cloud(x*2.4,y*1.8-t*0.35,t*0.60)+0.18*(1-y)+0.10*sin(x*8+t*0.8))) }
    static func warm(_ h:Double)->[Double] { let f=smooth(h);return [95+160*f,4+76*f*f,1+5*f*f] }
    static func burst(_ x:Double,_ y:Double,_ t:Double,_ seed:Double)->Double { let phase=fract(t*0.20),cycle=floor(t*0.20);let r=hypot(x-(noise(cycle+2)-0.5)*0.65,y-(noise(cycle+9)-0.5)*0.65);return 0.02+exp(-pow((r-phase*0.85)/0.09,2))*pow(sin(Double.pi*phase),2)*(0.55+0.45*noise(seed+cycle)) }
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
        let radius=hypot(xx,yy),angle=atan2(yy,xx)/tau,den=density/100,seed=u*127.1+v*311.7
        func pal(_ f:Double,_ cycle:Bool=false)->[Double] {
            let p=cycle ? fract(f)*Double(palette.count):max(0,min(1,f))*Double(palette.count-1)
            let a=min(palette.count-1,Int(p)),b=cycle ? (a+1)%palette.count:min(palette.count-1,a+1),d=smooth(p-floor(p))
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
        case "static":rgb=palette[0];level=1.0
        case "gradient":rgb=pal(q);level=1.0
        case "spectrum":rgb=hsv(t*0.10);level=1.0
        case "breathing":rgb=palette[0];level=0.12+0.88*(0.5-0.5*cos(t*1.5))
        case "wave":rgb=pal(q-t*0.16,true);level=0.8+0.2*sin(q*3.0-t*0.8)
        case "aurora":rgb=pal(0.5+0.30*sin(q*2.8-t*0.20)+0.18*sin(v*4.0+t*0.31));level=0.32+0.68*cloud(u*scale,v*scale,t*0.35)
        case "comet":rgb=pal(q*0.5+t*0.04,true);level=0.025+0.975*trail(t*0.16-q,9.0)
        case "twinkle":rgb=pal(noise(seed));level=0.05+0.95*spark(seed,t,den,0.95)
        case "color shift":rgb=pal(t*0.07,true);level=1.0
        case "rainbow wave":rgb=hsv(q*0.70-t*0.12,0.90);level=1.0
        case "pulse":rgb=pal(t*0.035,true);level=0.06+0.94*pow(0.5-0.5*cos(t*2.2),2.0)
        case "heartbeat":rgb=palette[0];level=0.05+0.60*bell(t*0.32-0.18,0.24)+0.32*bell(t*0.32-0.40,0.30)
        case "scanner":rgb=pal(q);level=0.025+0.975*exp(-pow((q-(0.5-0.5*cos(t*1.15)))/0.14,2.0))
        case "bounce":rgb=pal(t*0.045,true);level=0.025+0.975*exp(-pow((q-(0.5-0.5*cos(t*0.90)))/0.22,2.0))
        case "ripple":rgb=pal(radius-t*0.08,true);level=0.08+0.92*pow(0.5+0.5*cos(radius*15.0-t*2.0),2.0)
        case "orbit":rgb=pal(angle-t*0.04,true);level=0.04+0.96*exp(-(pow(xx-0.30*cos(t*0.85),2.0)+pow(yy-0.30*sin(t*0.85),2.0))/0.045)
        case "marquee":rgb=pal(q-t*0.035,true);level=0.08+0.92*pow(0.5+0.5*cos(q*tau*(2.0+den*3.0)-t*1.8),3.0)
        case "chase":rgb=pal(q*2.0-t*0.12,true);level=0.10+0.90*trail(t*0.18-q*2.0,5.0)
        case "fire":rgb=pal(heat(u*scale,v*scale,t));level=0.35+0.65*heat(u*scale,v*scale,t)
        case "fireplace":rgb=warm(heat(u*scale,v*scale,t));level=0.42+0.58*heat(u*scale,v*scale,t)
        case "candle":rgb=pal(0.45+0.35*cloud(0.0,0.0,t*0.65));level=0.55+0.30*cloud(0.0,0.0,t*0.9)+0.15*cloud(u,v,t*0.5)
        case "ocean":rgb=pal(0.5+0.28*sin(q*5.0-t*0.65)+0.18*cos(v*4.0+t*0.4));level=0.45+0.55*pow(0.5+0.5*sin(q*8.0-t*0.85),2.0)
        case "sunset":rgb=pal(0.5+0.40*sin(v*scale*2.2+t*0.09));level=0.65+0.35*smooth(1.0-v)
        case "ice":rgb=pal(cloud(u*scale*2.0,v*scale*2.0,t*0.25));level=0.35+0.65*spark(seed,t,den,0.40)
        case "plasma":rgb=pal(cloud(u*scale*2.0,v*scale*2.0,t*0.65),true);level=0.85+0.15*sin(q*3.0+t*0.4)
        case "nebula":rgb=pal(cloud(u*scale,v*scale,t*0.25));level=0.20+0.80*cloud(v*scale,u*scale,t*0.31)
        case "fog":rgb=pal(cloud(u*scale,v*scale,t*0.12));level=0.35+0.40*cloud(q,v,t*0.22)
        case "starfield":rgb=pal(noise(seed+1.0));level=0.015+0.985*spark(seed+12.0,t,den,0.28)
        case "fireflies":rgb=pal(noise(seed+3.0));level=0.025+0.975*spark(seed+7.0,t,den,0.55)
        case "meteor shower":rgb=pal(q+t*0.04,true);level=0.02+0.38*trail(t*0.15-q,8.0)+0.35*trail(t*0.19-q-0.33,10.0)+0.25*trail(t*0.12-q-0.68,7.0)
        case "rain":rgb=pal(noise(floor(u*scale*10.0)));level=0.02+0.98*trail(t*(0.22+noise(floor(u*scale*10.0))*0.16)-v*scale+noise(floor(u*scale*10.0)+7.0),8.0)
        case "digital rain":rgb=pal(1.0-fract(t*0.23-v*scale+noise(floor(u*scale*12.0))));level=0.025+0.975*trail(t*(0.16+noise(floor(u*scale*12.0))*0.12)-v*scale+noise(floor(u*scale*12.0)+11.0),5.0)
        case "confetti":rgb=pal(noise(seed*3.0+5.0),true);level=0.04+0.96*spark(seed+21.0,t,den,1.25)
        case "fireworks":rgb=pal(noise(floor(t*0.20)+4.0),true);level=burst(xx,yy,t,seed)
        case "snow":rgb=pal(noise(seed+1.0));level=0.06+0.94*spark(seed+5.0,t,den,0.32)
        case "stripes":rgb=pal(q*(2.0+den*4.0)-t*0.10,true);level=1.0
        case "checkerboard":rgb=pal((0.5+0.5*sin(u*scale*tau*3.0-t*0.65))*(0.5+0.5*sin(v*scale*tau*3.0+t*0.50)));level=0.65+0.35*cloud(u,v,t*0.2)
        case "spiral":rgb=pal(angle*2.0+radius*3.5-t*0.10,true);level=0.7+0.3*smooth(min(1.0,radius*3.0))
        case "pinwheel":rgb=pal(angle*4.0-t*0.10,true);level=0.25+0.75*(0.5+0.5*sin(angle*tau*4.0-t*0.65))
        case "vortex":rgb=pal(angle*2.0+radius*5.0-t*0.12,true);level=0.18+0.82*pow(0.5+0.5*sin(radius*16.0-t*1.5),2.0)
        case "radar":rgb=pal(radius);level=0.035+0.965*trail(t*0.12-angle,6.0)*(0.4+0.6*min(1.0,radius*2.0))
        default:break
        }
        return rgb.map { $0*max(0,min(1,level)) }
    }
}
