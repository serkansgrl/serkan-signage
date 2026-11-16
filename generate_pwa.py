"""Generate default PWA icons, manifest and service worker with standard Python."""
import json
import os
from pathlib import Path
import struct
import zlib

pwa=Path(os.environ.get('SIGNAGE_DATA_DIR','/data'))/'pwa'
pwa.mkdir(parents=True,exist_ok=True)
manifest={'name':'Serkan Signage - Digital Display','short_name':'Serkan Signage','start_url':'/','scope':'/','display':'standalone','background_color':'#192630','theme_color':'#192630','icons':[{'src':f'/pwa/icon-{size}.png','sizes':f'{size}x{size}','type':'image/png'} for size in (192,512)]}
files={'manifest.webmanifest':json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','sw.js':"self.addEventListener('install', () => self.skipWaiting());\nself.addEventListener('activate', event => event.waitUntil(self.clients.claim()));\n"}
for name,body in files.items():
    path=pwa/name
    if not path.exists(): path.write_text(body,encoding='utf8')

def chunk(name,data):
    return struct.pack('!I',len(data))+name+data+struct.pack('!I',zlib.crc32(name+data)&0xffffffff)

def make_icon(n):
    dark=(25,38,48); panel=(41,59,73); burgundy=(139,30,36); light=(211,234,247)
    rows=[]
    for y in range(n):
        row=bytearray([0])
        for x in range(n):
            inside=n//9<x<n*8//9 and n//5<y<n*4//5
            border=inside and (x<n//9+n//25 or x>n*8//9-n//25 or y<n//5+n//25 or y>n*4//5-n//25)
            stripe=n*3//10<y<n*7//10 and abs((x-y//3)-(n//3))<n//30
            c=burgundy if border else (light if inside and stripe else (panel if inside else dark))
            row.extend(c)
        rows.append(bytes(row))
    raw=zlib.compress(b''.join(rows),9)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',n,n,8,2,0,0,0))+chunk(b'IDAT',raw)+chunk(b'IEND',b'')

for size in (192,512):
    path=pwa/f'icon-{size}.png'
    if not path.exists():path.write_bytes(make_icon(size))
