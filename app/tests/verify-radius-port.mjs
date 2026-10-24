// SPDX-License-Identifier: GPL-2.0-or-later
// Compare the native port against the original MIT plugin, not a duplicate implementation.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
const source=fs.readFileSync('vendor/radius/FractalRadius.js','utf8').replace(/^export /gm,'');
const context=vm.createContext({});new vm.Script(source).runInContext(context);
for(const fanCount of [0,1,16,60,255]) {
 const zones=[{id:1,count:22,type:1},...(fanCount?[{id:0x11,count:fanCount,type:1}]:[])];
 const colors=Array.from({length:22+fanCount},(_,i)=>[(i*11)%256,(255-i)%256&255,(i*7)%256]);
 context.inputZones=zones;context.inputColors=colors;
 const js=vm.runInContext('(()=>{zones=inputZones;let n=0;return zones.flatMap(z=>{let frame=inputColors.slice(n,n+z.count).flat();n+=z.count;return stillReports(z,frame)})})()',context);
 const py=JSON.parse(execFileSync('python3',['-c',"import json,sys;sys.path.insert(0,'app');from radius_protocol import packets;x=json.load(sys.stdin);print(json.dumps([list(p) for p in packets(x['zones'],x['colors'])]))"],{input:JSON.stringify({zones,colors}),encoding:'utf8'}));
 assert.equal(JSON.stringify(js),JSON.stringify(py));
}
console.log('Radius Python packets match the original SignalRGB plugin across pump/fan sizes');
