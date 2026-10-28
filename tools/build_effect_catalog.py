#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
import json
from pathlib import Path
spec=[
('Essentials', [('static','Solid color','circle.fill','One steady color across the setup.'),('gradient','Gradient','slider.horizontal.3','Blend your palette through space.'),('spectrum','Spectrum','circle.lefthalf.filled','A seamless full-spectrum color cycle.'),('breathing','Breathing','waveform.path','A slow, soft fade in and out.'),('color shift','Color shift','circle.hexagongrid','Crossfade smoothly between palette colors.'),('pulse','Pulse','waveform','A rounded pulse with a gentle afterglow.'),('heartbeat','Heartbeat','waveform.path.ecg','Two soft beats followed by a quiet pause.')]),
('Motion',[('wave','Wave','water.waves','Move your palette across the canvas.'),('comet','Comet','sparkle','One bright head with a fading tail.'),('rainbow wave','Rainbow wave','rainbow','A spatial ribbon through the full spectrum.'),('scanner','Scanner','viewfinder','A narrow beam sweeps back and forth.'),('bounce','Bounce','arrow.left.and.right','A soft light orb bounces between edges.'),('ripple','Ripple','dot.radiowaves.left.and.right','Expanding circular waves from the center.'),('orbit','Orbit','circle.dotted','A light point circles the canvas.'),('marquee','Marquee','ellipsis','Evenly spaced lights travel in formation.'),('chase','Chase','chevron.right.2','Alternating palette lanes move across devices.')]),
('Atmosphere',[('aurora','Aurora','sparkles','Slow green and violet northern lights.'),('fire','Fire','flame','Layered heat, embers and gentle turbulence.'),('candle','Candlelight','flame.fill','Warm, irregular flicker without hard flashes.'),('ocean','Ocean','water.waves','Overlapping swells and luminous sea foam.'),('sunset','Sunset','sun.horizon','A warm horizon slowly moves through space.'),('ice','Ice','snowflake','A cold crystalline shimmer.'),('plasma','Plasma','circle.hexagongrid.fill','Interfering color fields flow across the canvas.'),('nebula','Nebula','cloud','Clouds of color drift through a soft field.'),('fog','Fog','cloud.fog','A diffuse low-contrast wash of moving color.')]),
('Particles',[('twinkle','Twinkle','star','Independent soft sparkles on every LED.'),('starfield','Starfield','sparkles','Scattered stars with long, quiet fades.'),('fireflies','Fireflies','lightbulb','Small lights appear, glow and fade.'),('meteor shower','Meteor shower','sparkle','Several trails drift at different speeds.'),('rain','Rain','cloud.rain','Narrow droplets fall through the canvas.'),('digital rain','Digital rain','terminal','Columns of light leave fading digital trails.'),('confetti','Confetti','party.popper','Palette-colored specks drift and dissolve.'),('fireworks','Fireworks','burst','Soft expanding bursts with fading sparks.'),('snow','Snowfall','snowflake','Slow, scattered flakes in a quiet background.')]),
('Geometry',[('stripes','Stripes','line.3.horizontal','Smooth palette bands slide through space.'),('checkerboard','Checkerboard','square.grid.3x3','A moving two-dimensional palette grid.'),('spiral','Spiral','hurricane','Palette ribbons curl outward from the center.'),('pinwheel','Pinwheel','fanblades','Rotating arms meet at the center.'),('vortex','Vortex','tornado','A soft tunnel of rotating light.'),('radar','Radar','scope','A sweeping beam with a fading radial trail.')])]
palettes={
'Essentials':(['a7f3d0','42d6ce','9f8bff'],['ff6b92','ffb36b','fff0c2']),
'Motion':(['13d7ff','4866ff','bc67ff'],['ff4d6d','ffc857','fff4d4']),
'Atmosphere':(['17295c','5065c7','b48eff','75e4db'],['2a0400','ff3c09','ffb435','fff0b4']),
'Particles':(['a7f3d0','66dfce','d3fff1'],['302357','8d6dff','e8b9ff']),
'Geometry':(['ff4f87','9a59ff','42d6ff'],['f6ca62','ee825b','954bc6'])}
looks_names={'static':['Mint','Warm ivory'],'gradient':['Coastal glass','Golden hour'],'spectrum':['Slow spectrum','Color current'],'breathing':['Quiet mint','Rose lantern'],'color shift':['Sea glass','Peach glow'],'pulse':['Soft signal','Coral pulse'],'heartbeat':['Emerald beat','Amber heartbeat'],'wave':['Ocean current','Solar ribbon'],'comet':['Ion trail','Ember trail'],'rainbow wave':['Pastel ribbon','Chromatic flow'],'scanner':['Blue sweep','Golden scanner'],'bounce':['Orbit blue','Amber orb'],'ripple':['Tidal rings','Solar ripples'],'orbit':['Lunar orbit','Solar orbit'],'marquee':['Night train','Festival lights'],'chase':['Neon lanes','Sunset chase'],'aurora':['Northern sky','Polar drift'],'fire':['Blue flame','Ember hearth'],'candle':['Moon candle','Candlelit amber'],'ocean':['Deep water','Amber tides'],'sunset':['Violet horizon','Desert dusk'],'ice':['Glacier','Opal frost'],'plasma':['Ionic field','Solar plasma'],'nebula':['Violet cloud','Rose nebula'],'fog':['Coastal mist','Warm haze'],'twinkle':['Mint starlight','Amethyst stars'],'starfield':['Deep space','Lavender sky'],'fireflies':['Garden lights','Violet lanterns'],'meteor shower':['Mint meteors','Violet trails'],'rain':['Night rain','Amethyst rain'],'digital rain':['Mint terminal','Violet terminal'],'confetti':['Sea confetti','Orchid confetti'],'fireworks':['Emerald bloom','Violet bloom'],'snow':['Mint snowfall','Lavender snow'],'stripes':['Neon ribbons','Amber ribbons'],'checkerboard':['Neon tiles','Warm mosaic'],'spiral':['Chromatic spiral','Golden spiral'],'pinwheel':['Prism wheel','Sun wheel'],'vortex':['Neon tunnel','Amber tunnel'],'radar':['Neon radar','Amber radar']}
effects=[];looks=[]
for cat,rows in spec:
 for key,name,symbol,desc in rows:
  colors=key not in ('spectrum','aurora','rainbow wave')
  base=list(palettes[cat][0]);speed=35 if cat=='Atmosphere' else 65 if key=='twinkle' else 45
  if key in ('fire','candle','sunset'):base=list(palettes[cat][1])
  if key=='ice':base=['082449','45bfff','c3f5ff','ffffff']
  if key=='digital rain':base=['061b16','12b873','a7f3d0']
  effects.append(dict(id=key,name=name,category=cat,symbol=symbol,description=desc,palette=base,speed=speed,scale=1,density=55,colors=colors))
  for n,title in enumerate(looks_names[key]):
   pal=list(base if n==0 else palettes[cat][1])
   if not colors:pal=base
   looks.append(dict(id=key.replace(' ','-')+'-'+str(n),name=title,effect=key,category=cat,palette=pal,speed=speed if n==0 else min(85,speed+20),scale=1 if n==0 else 1.7,density=45 if n==0 else 75))
# Refined metadata and the fixed warm Fireplace are part of the reproducible source.
for effect in effects:
 if effect['id']=='fire':
  effect.update(palette=['580501','b92402','f56a06'],description='Smooth rising flame field with a customizable heat palette.')
 if effect['id']=='twinkle':effect['description']='Soft, staggered sparkles distributed over physical LED positions.'
effects.insert(next(i for i,e in enumerate(effects) if e['id']=='fire')+1,dict(id='fireplace',name='Fireplace',category='Atmosphere',symbol='flame.fill',description='Slow molten embers and rising flames. Deep red, burnt orange and amber without white flashes.',palette=['601001','c62d03','ff7008'],speed=55,scale=1,density=65,colors=False))
for n,speed in enumerate((35,65)):
 looks.append(dict(id='fireplace-'+str(n),name=['Ember hearth','Crackling glow'][n],effect='fireplace',category='Atmosphere',palette=['601001','c62d03','ff7008'],speed=speed,scale=1+n*.4,density=65))
assert len(effects)==41 and len(looks)==82
(Path(__file__).resolve().parents[1]/'app/effects_catalog.json').write_text(json.dumps(dict(schema=1,categories=[c for c,_ in spec],effects=effects,looks=looks),indent=2)+'\n')
