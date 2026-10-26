# SPDX-License-Identifier: GPL-2.0-or-later
"""Deterministic shared-clock effect kernel. No device I/O or random mutable state."""
import colorsys
import json
import math
from pathlib import Path
CATALOG=json.loads(Path(__file__).with_name('effects_catalog.json').read_text())
MODES=frozenset(e['id'] for e in CATALOG['effects'])
TAU=math.tau

def fract(v):return v-math.floor(v)
def noise(v):return fract(math.sin(v*12.9898+78.233)*43758.5453)
def smooth(v):v=max(0,min(1,v));return v*v*(3-2*v)
def field(x,y,t):
    return (math.sin(x*4.7+t*.7)+math.cos(y*5.3-t*.43)+math.sin((x+y)*3.1+t*.31))/6+.5

def sample(mode,palette,index,u,v,coord,time,speed,scale=1,density=55,reverse=False):
    """Return unclipped RGB at full scene brightness. Coordinates are canvas-aware."""
    t=time*speed/100*(-1 if reverse else 1);q=coord*scale;xx=(u-.5)*scale;yy=(v-.5)*scale
    radius=math.hypot(xx,yy);angle=math.atan2(yy,xx)/TAU;den=density/100
    def pal(f,cycle=False):
        p=fract(f)*len(palette) if cycle else max(0,min(1,f))*(len(palette)-1)
        a=min(len(palette)-1,int(p));b=(a+1)%len(palette) if cycle else min(len(palette)-1,a+1);d=p-int(p)
        return tuple(palette[a][k]*(1-d)+palette[b][k]*d for k in range(3))
    def hsv(h,s=0.8,l=1):return tuple(c*255 for c in colorsys.hsv_to_rgb(fract(h),s,max(0,min(1,l))))
    rgb=palette[0];level=1
    if mode=='gradient':rgb=pal(q)
    elif mode=='spectrum':rgb=hsv(t*.2)
    elif mode=='breathing':level=.08+.92*(.5-.5*math.cos(t*math.pi))
    elif mode=='wave':rgb=pal(q+t*.25,True)
    elif mode=='aurora':rgb=hsv(.38+fract(q*.28+t*.06)*.36,.78,.6+.4*math.sin(q*5+t)**2)
    elif mode=='comet':level=math.exp(-fract(t*.25-q)*12)
    elif mode=='twinkle':rgb=palette[index%len(palette)];level=.08+.92*max(0,math.sin(index*12.9898+q*78.233+t*3))**(12+(55-density)*.14)
    elif mode=='color shift':rgb=pal(t*.12,True)
    elif mode=='rainbow wave':rgb=hsv(q*.55-t*.15,.72)
    elif mode=='pulse':level=.06+.94*(.5+.5*math.sin(t*TAU))**3
    elif mode=='heartbeat':
        phase=fract(t*.65);level=.04+.75*math.exp(-((phase-.16)/.055)**2)+.5*math.exp(-((phase-.36)/.075)**2)
    elif mode=='scanner':level=.025+.975*math.exp(-((q-(.5-.5*math.cos(t*1.8)))/.075)**2)
    elif mode=='bounce':rgb=pal(t*.05,True);level=.02+.98*math.exp(-((q-(1-abs(fract(t*.24)*2-1)))/.16)**2)
    elif mode=='ripple':rgb=pal(radius-t*.12,True);level=.05+.95*(.5+.5*math.cos(radius*18-t*4))**5
    elif mode=='orbit':level=.03+.97*math.exp(-((xx-.3*math.cos(t*2))**2+(yy-.3*math.sin(t*2))**2)/.022)
    elif mode=='marquee':level=.06+.94*(.5+.5*math.cos(q*TAU*(3+den*5)-t*3))**8
    elif mode=='chase':rgb=pal(fract(q*3-t*.2),True);level=.12+.88*smooth(math.sin(q*TAU*3-t*TAU))
    elif mode=='fire':rgb=pal(max(0,min(1,.23+.62*field(u*scale,v*scale,t*2)+.15*math.sin(index*2.3+t*6))));level=.55+.45*field(q,0,t*2)
    elif mode=='candle':rgb=pal(.55+.25*math.sin(t*3.4)+.12*math.sin(t*8.7+index*.14));level=.55+.25*math.sin(t*4.2)+.12*math.sin(t*10.7+index*.03)
    elif mode=='ocean':rgb=pal(.5+.25*math.sin(q*7-t*.8)+.2*math.cos(v*4+t*.6));level=.5+.5*(.5+.5*math.sin(q*12-t*1.4))
    elif mode=='sunset':rgb=pal(.5+.4*math.sin(v*scale*2.5+t*.12));level=.55+.45*smooth(1-v)
    elif mode=='ice':rgb=pal(field(u*scale*2,v*scale*2,t*.35));level=.45+.55*max(0,math.sin(index*4.31+q*7+t))**4
    elif mode=='plasma':rgb=pal(field(u*scale*2,v*scale*2,t*1.2),True)
    elif mode=='nebula':rgb=pal(field(u*scale,v*scale,t*.6));level=.25+.75*field(v*scale,u*scale,t*.43)
    elif mode=='fog':rgb=pal(field(q,v,t*.3));level=.35+.3*field(q,v,t*.5)
    elif mode=='starfield':rgb=palette[index%len(palette)];level=.015+.985*max(0,math.sin(index*7.77+q*31+t*.7))**(36-24*den)
    elif mode=='fireflies':rgb=pal(noise(index+3));level=.02+.98*max(0,math.sin(t*(.4+noise(index)*.8)+index*5.23))**(10-6*den)
    elif mode=='meteor shower':
        level=.015
        for i in range(3):level+=math.exp(-fract(t*(.16+i*.04)-q-i*.31)*(14-i*2))*.6
        rgb=pal(q+t*.08,True)
    elif mode=='rain':
        lane=math.floor(u*scale*10);drop=fract(t*(.3+noise(lane)*.35)+noise(lane+7)-v*scale)
        rgb=pal(noise(lane));level=.015+.985*math.exp(-drop*(22-12*den))
    elif mode=='digital rain':
        lane=math.floor(u*scale*12);head=fract(t*(.18+noise(lane)*.2)+noise(lane+11)-v*scale)
        rgb=pal(1-head);level=.01+.99*math.exp(-head*(12-6*den))
    elif mode=='confetti':rgb=pal(noise(index*3+5),True);level=.025+.975*max(0,math.sin(index*2.47+q*23+t*(1+noise(index)*2)))**(16-10*den)
    elif mode=='fireworks':
        cycle=math.floor(t*.35);phase=fract(t*.35);cx=noise(cycle+2)-.5;cy=noise(cycle+9)-.5
        distance=math.hypot(xx-cx*.65,yy-cy*.65);rgb=pal(noise(cycle+4),True)
        level=.01+math.exp(-((distance-phase*.85)/.045)**2)*(1-phase)*(.3+.7*noise(index+cycle))
    elif mode=='snow':rgb=pal(noise(index+1));level=.03+.97*max(0,math.sin(index*3.19+q*9+t*.7))**(18-12*den)
    elif mode=='stripes':rgb=pal(q*(2+den*5)-t*.12,True)
    elif mode=='checkerboard':rgb=palette[(math.floor(u*scale*6+t*.4)+math.floor(v*scale*6))%len(palette)];level=.35+.65*(.5+.5*math.cos(t+q))
    elif mode=='spiral':rgb=pal(angle*3+radius*4-t*.18,True)
    elif mode=='pinwheel':rgb=pal(angle*5-t*.15,True);level=.2+.8*(.5+.5*math.sin(angle*TAU*5-t))
    elif mode=='vortex':rgb=pal(angle*2+radius*6-t*.2,True);level=.15+.85*(.5+.5*math.sin(radius*22-t*3))**2
    elif mode=='radar':level=.03+.97*math.exp(-fract(t*.16-angle)*10)*(.4+.6*min(1,radius*2))
    return tuple(c*max(0,min(1,level)) for c in rgb)

def frame(scene,count,position,elapsed):
    palette=[tuple(bytes.fromhex(v)) for v in scene['palette']];brightness=scene['brightness']/100;out=[]
    points=position.get('led_positions',[]);spatial=scene.get('mapping','mirror')=='canvas'
    for index in range(count):
        point=points[index] if len(points)==count else None
        u=point['x'] if point else index/max(1,count-1);v=point['y'] if point else u
        if spatial:
            u=position.get('x',.5)+(u-.5)*position.get('width',.3)
            v=position.get('y',.5)+((v-.5)*position.get('width',.3) if point else 0)
        coord=u if scene['axis']=='x' else v
        rgb=sample(scene['mode'],palette,index,u,v,coord,elapsed,scene['speed'],scene.get('scale',1),scene.get('density',55),scene.get('reverse',False))
        out.append(tuple(max(0,min(255,round(c*brightness))) for c in rgb))
    return out
