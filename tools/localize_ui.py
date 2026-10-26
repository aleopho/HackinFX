#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Extract source UI messages and explicitly localize presentation, never data IDs."""
from pathlib import Path
import ast,json,re
ROOT=Path(__file__).resolve().parents[1]
FILES=['CommunityRGB.swift','ControlCenter.swift','EffectGallery.swift']
CALLS={'Text','Label','Button','Toggle','Picker','Menu','TextField','ColorPicker','DisclosureGroup','Link','help','accessibilityLabel','accessibilityHint','navigationTitle'}
def quoted(s,i):
    j=i+1;value='';slot=0
    while j<len(s):
        if s[j]=='"':return j+1,value
        if s[j]=='\\':
            if j+1<len(s) and s[j+1]=='(':
                k=argument_end(s,j+2,split=False);value+='{'+str(slot)+'}';slot+=1;j=k+1;continue
            if j+1<len(s):value+={'n':'\n','t':'\t','r':'\r','"':'"','\\':'\\'}.get(s[j+1],s[j+1]);j+=2;continue
        value+=s[j];j+=1
    raise ValueError('Unterminated Swift string')
def argument_end(s,i,split=True):
    paren=1;bracket=brace=0
    while i<len(s):
        c=s[i]
        if c=='"':i,_=quoted(s,i);continue
        if s.startswith('//',i):i=s.find('\n',i) if '\n' in s[i:] else len(s);continue
        if c=='(':paren+=1
        elif c==')':
            paren-=1
            if paren==0:return i
        elif c=='[':bracket+=1
        elif c==']':bracket-=1
        elif c=='{':brace+=1
        elif c=='}':brace-=1
        elif split and c==',' and paren==1 and bracket==0 and brace==0:return i
        i+=1
    raise ValueError('Unbalanced Swift call')
def literals(s):
    i=0
    while i<len(s):
        if s.startswith('//',i):i=s.find('\n',i) if '\n' in s[i:] else len(s);continue
        if s.startswith('/*',i):i=s.index('*/',i)+2;continue
        if s[i]=='"':i,value=quoted(s,i);yield value;continue
        i+=1
def display_key(s):
    if not re.search('[A-Za-z]',s) or len(s)>650 or len(s)<2:return False
    if s.startswith(('http','/','com.','sample:','native:','--','{','[')) and not re.search(r'^\{[0-9]+\}.+[A-Za-z]',s):return False
    if any(v in s for v in ['.json','.plist','.swift','.py','appendingPath','\\','[A-Za-z','[a-z']):return False
    if re.fullmatch(r'[a-z0-9_.:/-]+',s):return False
    if re.fullmatch(r'[A-Za-z0-9_.]+',s) and (s.endswith(('Controller','Tests','Status')) or len(s)>32):return False
    if any(v in s for v in ['ASUS ROG','PNY XLR8','GIGABYTE Device','Corsair Dominator','Fractal Design']) and len(s)<90:return False
    if s in {'HackinFX','OpenRGB','NullMoth','NVRM','macUSPCIO','Nanoleaf','RGB','USB','PCI','GPU','RAM','JSON','LED','FPS','ISO','ANSI'}:return False
    if re.fullmatch(r'[0-9A-Fa-f]{6,}',s):return False
    return True
def wrap(s):
    edits=[];i=0
    while i<len(s):
        if s.startswith('//',i):i=s.find('\n',i) if '\n' in s[i:] else len(s);continue
        if s.startswith('/*',i):i=s.index('*/',i)+2;continue
        if s[i]=='"':i,_=quoted(s,i);continue
        match=re.match(r'\b([A-Za-z][A-Za-z0-9_]*)\(',s[i:])
        if match and match.group(1) in CALLS:
            a=i+len(match.group());b=argument_end(s,a);arg=s[a:b].strip()
            if arg and not re.match(r'[A-Za-z_][A-Za-z0-9_]*\s*:',arg) and not arg.startswith(('L10n.text(', 'verbatim:','Image(')):
                edits.append((a,b,'L10n.text('+s[a:b]+')'))
            i=b+1;continue
        i+=1
    for a,b,value in reversed(edits):s=s[:a]+value+s[b:]
    return s
if __name__=='__main__':
    keys=set()
    for name in FILES:
        p=ROOT/'app'/name;s=p.read_text()
        keys.update(v for v in literals(s) if display_key(v));p.write_text(wrap(s))
    catalog=json.loads((ROOT/'app/effects_catalog.json').read_text())
    for item in catalog['effects']+catalog['looks']:
        keys.update(item[k] for k in ['name','description','category'] if k in item)
    # Backend user-facing messages; runtime technical diagnostics remain intact.
    for name in ['center_core.py','ram_control.py','nanoleaf_control.py','usb_devices.py']:
        tree=ast.parse((ROOT/'app'/name).read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and display_key(node.value) and '\n' not in node.value:keys.add(node.value)
    # Canonicalize printf messages to numbered placeholders, matching rendered strings.
    clean={}
    for value in sorted(keys):
        n=[0]
        def replace(m):i=n[0];n[0]+=1;return '{'+str(i)+'}'
        key=re.sub(r'%(?:[0-9]+\$)?[.0-9]*[df@su]',replace,value)
        clean[key]=key
    dest=ROOT/'app/Localization';dest.mkdir(exist_ok=True);(dest/'en.json').write_text(json.dumps(clean,ensure_ascii=False,indent=2)+'\n')
    print('Extracted',len(clean),'presentation messages')
