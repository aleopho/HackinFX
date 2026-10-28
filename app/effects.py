# SPDX-License-Identifier: GPL-2.0-or-later
"""Deterministic shared-clock effect kernel. No device I/O or random mutable state."""
import colorsys
import json
import math
from math import sin,cos,exp,pow,floor
from pathlib import Path
CATALOG=json.loads(Path(__file__).with_name('effects_catalog.json').read_text())
MODES=frozenset(e['id'] for e in CATALOG['effects'])
TAU=math.tau

def fract(v):return v-math.floor(v)
def noise(v):return fract(math.sin(v*12.9898+78.233)*43758.5453)
def smooth(v):v=max(0,min(1,v));return v*v*(3-2*v)
def field(x,y,t):
    return (math.sin(x*4.7+t*.7)+math.cos(y*5.3-t*.43)+math.sin((x+y)*3.1+t*.31))/6+.5

def cloud(x,y,t):return .65*field(x,y,t)+.35*field(x*2.03+1.7,y*2.03-2.1,t*1.37)
def bell(p,width):return exp(-pow(sin(math.pi*p)/width,2))
def trail(p,sharpness):
    phase=fract(p);return exp(-phase*sharpness)*smooth(phase/.12)*smooth((1-phase)/.12)*2.4
def spark(seed,t,density,rate):
    phase=t*rate*(.7+noise(seed)*.6)+noise(seed+17)*TAU
    return smooth((.5+.5*sin(phase)-(.55-.30*density))/(.45+.30*density))**2
def heat(x,y,t):
    # Advected multi-scale flame field, warm embers; no frame-based random flicker.
    return max(0,min(1,.12+.66*cloud(x*2.4,y*1.8-t*.35,t*.60)+.18*(1-y)+.10*sin(x*8+t*.8)))
def warm(h):
    # Deep red -> burnt orange -> amber. No white hot / blue flashes.
    f=smooth(h);return (95+160*f,4+76*f*f,1+5*f*f)
def burst(x,y,t,seed):
    phase=fract(t*.20);cycle=floor(t*.20)
    r=math.hypot(x-(noise(cycle+2)-.5)*.65,y-(noise(cycle+9)-.5)*.65)
    return .02+exp(-pow((r-phase*.85)/.09,2))*sin(math.pi*phase)**2*(.55+.45*noise(seed+cycle))

def sample(mode,palette,index,u,v,coord,time,speed,scale=1,density=55,reverse=False):
    """Return unclipped RGB at full scene brightness. Coordinates are canvas-aware."""
    t=time*speed/100*(-1 if reverse else 1);q=coord*scale;xx=(u-.5)*scale;yy=(v-.5)*scale
    radius=math.hypot(xx,yy);angle=math.atan2(yy,xx)/TAU;den=density/100;seed=u*127.1+v*311.7
    def pal(f,cycle=False):
        p=fract(f)*len(palette) if cycle else max(0,min(1,f))*(len(palette)-1)
        a=min(len(palette)-1,int(p));b=(a+1)%len(palette) if cycle else min(len(palette)-1,a+1);d=smooth(p-int(p))
        return tuple(palette[a][k]*(1-d)+palette[b][k]*d for k in range(3))
    def hsv(h,s=0.8,l=1):return tuple(c*255 for c in colorsys.hsv_to_rgb(fract(h),s,max(0,min(1,l))))
    rgb=palette[0];level=1
    if mode=='static':rgb=palette[0];level=1.0
    elif mode=='gradient':rgb=pal(q);level=1.0
    elif mode=='spectrum':rgb=hsv(t*0.10);level=1.0
    elif mode=='breathing':rgb=palette[0];level=0.12+0.88*(0.5-0.5*cos(t*1.5))
    elif mode=='wave':rgb=pal(q-t*0.16,True);level=0.8+0.2*sin(q*3.0-t*0.8)
    elif mode=='aurora':rgb=pal(0.5+0.30*sin(q*2.8-t*0.20)+0.18*sin(v*4.0+t*0.31));level=0.32+0.68*cloud(u*scale,v*scale,t*0.35)
    elif mode=='comet':rgb=pal(q*0.5+t*0.04,True);level=0.025+0.975*trail(t*0.16-q,9.0)
    elif mode=='twinkle':rgb=pal(noise(seed));level=0.05+0.95*spark(seed,t,den,0.95)
    elif mode=='color shift':rgb=pal(t*0.07,True);level=1.0
    elif mode=='rainbow wave':rgb=hsv(q*0.70-t*0.12,0.90);level=1.0
    elif mode=='pulse':rgb=pal(t*0.035,True);level=0.06+0.94*pow(0.5-0.5*cos(t*2.2),2.0)
    elif mode=='heartbeat':rgb=palette[0];level=0.05+0.60*bell(t*0.32-0.18,0.24)+0.32*bell(t*0.32-0.40,0.30)
    elif mode=='scanner':rgb=pal(q);level=0.025+0.975*exp(-pow((q-(0.5-0.5*cos(t*1.15)))/0.14,2.0))
    elif mode=='bounce':rgb=pal(t*0.045,True);level=0.025+0.975*exp(-pow((q-(0.5-0.5*cos(t*0.90)))/0.22,2.0))
    elif mode=='ripple':rgb=pal(radius-t*0.08,True);level=0.08+0.92*pow(0.5+0.5*cos(radius*15.0-t*2.0),2.0)
    elif mode=='orbit':rgb=pal(angle-t*0.04,True);level=0.04+0.96*exp(-(pow(xx-0.30*cos(t*0.85),2.0)+pow(yy-0.30*sin(t*0.85),2.0))/0.045)
    elif mode=='marquee':rgb=pal(q-t*0.035,True);level=0.08+0.92*pow(0.5+0.5*cos(q*TAU*(2.0+den*3.0)-t*1.8),3.0)
    elif mode=='chase':rgb=pal(q*2.0-t*0.12,True);level=0.10+0.90*trail(t*0.18-q*2.0,5.0)
    elif mode=='fire':rgb=pal(heat(u*scale,v*scale,t));level=0.35+0.65*heat(u*scale,v*scale,t)
    elif mode=='fireplace':rgb=warm(heat(u*scale,v*scale,t));level=0.42+0.58*heat(u*scale,v*scale,t)
    elif mode=='candle':rgb=pal(0.45+0.35*cloud(0.0,0.0,t*0.65));level=0.55+0.30*cloud(0.0,0.0,t*0.9)+0.15*cloud(u,v,t*0.5)
    elif mode=='ocean':rgb=pal(0.5+0.28*sin(q*5.0-t*0.65)+0.18*cos(v*4.0+t*0.4));level=0.45+0.55*pow(0.5+0.5*sin(q*8.0-t*0.85),2.0)
    elif mode=='sunset':rgb=pal(0.5+0.40*sin(v*scale*2.2+t*0.09));level=0.65+0.35*smooth(1.0-v)
    elif mode=='ice':rgb=pal(cloud(u*scale*2.0,v*scale*2.0,t*0.25));level=0.35+0.65*spark(seed,t,den,0.40)
    elif mode=='plasma':rgb=pal(cloud(u*scale*2.0,v*scale*2.0,t*0.65),True);level=0.85+0.15*sin(q*3.0+t*0.4)
    elif mode=='nebula':rgb=pal(cloud(u*scale,v*scale,t*0.25));level=0.20+0.80*cloud(v*scale,u*scale,t*0.31)
    elif mode=='fog':rgb=pal(cloud(u*scale,v*scale,t*0.12));level=0.35+0.40*cloud(q,v,t*0.22)
    elif mode=='starfield':rgb=pal(noise(seed+1.0));level=0.015+0.985*spark(seed+12.0,t,den,0.28)
    elif mode=='fireflies':rgb=pal(noise(seed+3.0));level=0.025+0.975*spark(seed+7.0,t,den,0.55)
    elif mode=='meteor shower':rgb=pal(q+t*0.04,True);level=0.02+0.38*trail(t*0.15-q,8.0)+0.35*trail(t*0.19-q-0.33,10.0)+0.25*trail(t*0.12-q-0.68,7.0)
    elif mode=='rain':rgb=pal(noise(floor(u*scale*10.0)));level=0.02+0.98*trail(t*(0.22+noise(floor(u*scale*10.0))*0.16)-v*scale+noise(floor(u*scale*10.0)+7.0),8.0)
    elif mode=='digital rain':rgb=pal(1.0-fract(t*0.23-v*scale+noise(floor(u*scale*12.0))));level=0.025+0.975*trail(t*(0.16+noise(floor(u*scale*12.0))*0.12)-v*scale+noise(floor(u*scale*12.0)+11.0),5.0)
    elif mode=='confetti':rgb=pal(noise(seed*3.0+5.0),True);level=0.04+0.96*spark(seed+21.0,t,den,1.25)
    elif mode=='fireworks':rgb=pal(noise(floor(t*0.20)+4.0),True);level=burst(xx,yy,t,seed)
    elif mode=='snow':rgb=pal(noise(seed+1.0));level=0.06+0.94*spark(seed+5.0,t,den,0.32)
    elif mode=='stripes':rgb=pal(q*(2.0+den*4.0)-t*0.10,True);level=1.0
    elif mode=='checkerboard':rgb=pal((0.5+0.5*sin(u*scale*TAU*3.0-t*0.65))*(0.5+0.5*sin(v*scale*TAU*3.0+t*0.50)));level=0.65+0.35*cloud(u,v,t*0.2)
    elif mode=='spiral':rgb=pal(angle*2.0+radius*3.5-t*0.10,True);level=0.7+0.3*smooth(min(1.0,radius*3.0))
    elif mode=='pinwheel':rgb=pal(angle*4.0-t*0.10,True);level=0.25+0.75*(0.5+0.5*sin(angle*TAU*4.0-t*0.65))
    elif mode=='vortex':rgb=pal(angle*2.0+radius*5.0-t*0.12,True);level=0.18+0.82*pow(0.5+0.5*sin(radius*16.0-t*1.5),2.0)
    elif mode=='radar':rgb=pal(radius);level=0.035+0.965*trail(t*0.12-angle,6.0)*(0.4+0.6*min(1.0,radius*2.0))
    return tuple(c*max(0,min(1,level)) for c in rgb)

def frame(scene,count,position,elapsed):
    palette=[tuple(bytes.fromhex(v)) for v in scene['palette']];brightness=(100 if scene.get('layers') else scene['brightness'])/100;out=[]
    points=position.get('led_positions',[]);spatial=scene.get('mapping','mirror')=='canvas'
    for index in range(count):
        point=points[index] if len(points)==count else None
        u=point['x'] if point else index/max(1,count-1);v=point['y'] if point else u
        if spatial:
            dx=(u-.5)*position.get('width',.3)*(-1 if position.get('mirror_x') else 1)
            dy=((v-.5)*position.get('height',position.get('width',.3)) if point else 0)*(-1 if position.get('mirror_y') else 1)
            angle=math.radians(position.get('rotation',0));ca=math.cos(angle);sa=math.sin(angle)
            u=position.get('x',.5)+dx*ca-dy*sa
            v=position.get('y',.5)+dx*sa+dy*ca
        coord=u if scene['axis']=='x' else v
        rgb=sample(scene['mode'],palette,index,u,v,coord,elapsed,scene['speed'],scene.get('scale',1),scene.get('density',55),scene.get('reverse',False))
        out.append(tuple(max(0,min(255,round(c*brightness))) for c in rgb))
    for layer in scene.get('layers',[]):
        overlay=frame(dict(layer,mapping=scene.get('mapping','mirror'),layers=[]),count,position,elapsed);opacity=layer.get('opacity',50)/100;blend=layer.get('blend','screen')
        def mix(a,b):
            if blend=='screen':merged=255-(255-a)*(255-b)/255
            elif blend=='add':merged=min(255,a+b)
            elif blend=='multiply':merged=a*b/255
            else:merged=b
            return max(0,min(255,round(a*(1-opacity)+merged*opacity)))
        out=[tuple(mix(a,b) for a,b in zip(base,over)) for base,over in zip(out,overlay)]
    if scene.get('layers'):out=[tuple(round(c*scene['brightness']/100) for c in rgb) for rgb in out]
    return out
