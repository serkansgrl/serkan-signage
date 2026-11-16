import os, json, time, hmac, hashlib, secrets, html, mimetypes, urllib.request, urllib.parse, datetime, threading, re
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from email.parser import BytesParser
from email.policy import default

# Paths and network settings are supplied by the Docker deployment, not hard-coded for a home LAN.
ROOT=Path(os.environ.get('SIGNAGE_DATA_DIR', '/data'))
PHOTOS=ROOT/'photos'
NAS=Path(os.environ.get('SIGNAGE_NAS_DIR', '/nas-photos'))
CONFIG=ROOT/'config.json'
SECRET=ROOT/'secret'
PASSFILE=ROOT/'password.json'
HTTP_HOST=os.environ.get('SIGNAGE_HOST', '0.0.0.0')
HTTP_PORT=int(os.environ.get('SIGNAGE_PORT', '8080'))
FRAME_ANCESTORS=os.environ.get('FRAME_ANCESTORS', '').strip()
if FRAME_ANCESTORS and (any(ch in FRAME_ANCESTORS for ch in '\r\n;') or not all(re.fullmatch(r'https?://[a-zA-Z0-9.:-]+', origin) for origin in FRAME_ANCESTORS.split())):
    raise RuntimeError('FRAME_ANCESTORS must be a space-separated list of HTTP(S) origins')
COOKIE_SECURE=os.environ.get('COOKIE_SECURE', 'false').lower() in ('true','1','yes')
COOKIE_FLAGS='; HttpOnly; Path=/; SameSite=Lax'+('; Secure' if COOKIE_SECURE else '')
ROOT.mkdir(parents=True,exist_ok=True)

PHOTOS.mkdir(parents=True,exist_ok=True)
DAYS=['Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag']
DEFAULT={'meals':['—']*7, 'interval':20,'city':'Berlin','lat':52.52,'lon':13.405}
if not CONFIG.exists(): CONFIG.write_text(json.dumps(DEFAULT,ensure_ascii=False))
if not SECRET.exists(): SECRET.write_text(secrets.token_hex(32))
SECRET.chmod(0o600)
SECRET_BYTES=bytes.fromhex(SECRET.read_text().strip())
if not PASSFILE.exists():
    pwd=os.environ.get('INITIAL_ADMIN_PASSWORD','')
    if not pwd: raise RuntimeError('INITIAL_ADMIN_PASSWORD missing')
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac('sha256',pwd.encode(),salt,260000)
    PASSFILE.write_text(json.dumps({'salt':salt.hex(),'hash':digest.hex()})); PASSFILE.chmod(0o600)
lock=threading.RLock(); weather_cache={'at':0,'data':None}; fails={}

def read_config():
    with lock: return json.loads(CONFIG.read_text())

def save_config(d):
    temp=CONFIG.with_suffix('.tmp'); temp.write_text(json.dumps(d,ensure_ascii=False)); os.replace(temp,CONFIG)

def verify(p):
    a=json.loads(PASSFILE.read_text()); b=hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(a['salt']),260000)
    return hmac.compare_digest(b.hex(),a['hash'])

def session_value(ts,nonce):
    msg=f'{ts}.{nonce}'; sig=hmac.new(SECRET_BYTES,msg.encode(),hashlib.sha256).hexdigest(); return msg+'.'+sig

def good_session(cookie):
    m=re.search(r'(?:^|;\s*)sd_session=([^;]+)',cookie)
    if not m: return False
    try:
        ts,nonce,sig=m.group(1).split('.')
        if abs(time.time()-int(ts))>86400: return False
        return hmac.compare_digest(session_value(ts,nonce).split('.')[-1],sig)
    except (ValueError,TypeError): return False

def weather():
    with lock:
        if weather_cache['data'] and time.time()-weather_cache['at']<1800: return weather_cache['data']
    c=read_config(); query=urllib.parse.urlencode({'latitude':c['lat'],'longitude':c['lon'],'daily':'temperature_2m_max,temperature_2m_min,weather_code','timezone':'Europe/Berlin','forecast_days':7})
    try:
        req=urllib.request.Request('https://api.open-meteo.com/v1/forecast?'+query,headers={'User-Agent':'SerkanSignage/1.0'})
        with urllib.request.urlopen(req,timeout=8) as r: d=json.load(r)['daily']
        result=[{'date':d['time'][i],'hi':round(d['temperature_2m_max'][i]),'lo':round(d['temperature_2m_min'][i]),'code':d['weather_code'][i]} for i in range(len(d['time']))]
        with lock: weather_cache.update(at=time.time(),data=result)
        return result
    except Exception:
        with lock: return weather_cache['data'] or []

def photos():
    found=[]
    for directory,source in ((PHOTOS,'local'),(NAS,'nas')):
        if directory.exists():
            for p in sorted(directory.iterdir(),key=lambda x:x.name.lower()):
                if p.is_file() and p.suffix.lower() in ('.jpg','.jpeg','.png','.gif','.webp') and not p.is_symlink():
                    found.append({'name':p.name,'url':'/photo/'+source+'/'+urllib.parse.quote(p.name),'source':source})
                    if len(found)>=400: return found
    return found

def page(title,content):
    return '<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>body{font-family:Arial,sans-serif;background:#17232d;color:#edf2f5;margin:0;padding:22px}a{color:#82cdf1}input,textarea,button{font:inherit;padding:10px;border-radius:6px;border:1px solid #65727d}input,textarea{background:#f8fafb;color:#17232d;max-width:95%}textarea{width:95%;height:50px}button{background:#2884ae;color:white;cursor:pointer}section{background:#283b48;padding:18px;border-radius:12px;margin:12px 0}label{display:block;margin:12px 0 4px}.hint{color:#bccbd3;font-size:13px}.error{color:#ffc0b7}</style></head><body>'+content+'</body></html>'

def esc(x): return html.escape(str(x),quote=True)

# SERKAN_NEWS_QUIZ_V1: public, read-only BR24 feed + daily German quiz.
import xml.etree.ElementTree as SERKAN_ET
import random as SERKAN_RANDOM
SERKAN_NEWS_FEEDS=[u.strip() for u in os.environ.get('NEWS_FEEDS', 'https://nachrichtenfeeds.br.de/rdf/boards/UZlMIJH,https://nachrichtenfeeds.br.de/rss/nachrichten/seiten/QXAPkQJ').split(',') if u.strip().startswith('https://')]
NEWS_ALLOWED_HOSTS={h.strip().lower() for h in os.environ.get('NEWS_ALLOWED_HOSTS','www.br.de,br.de').split(',') if h.strip()}
SERKAN_NEWS_LOCK=threading.RLock()
SERKAN_NEWS={'at':0,'items':[]}
# Question bank: question, four answers, correct index. Curated general knowledge.
SERKAN_QUESTIONS=[
 ('Wie heißt die Landeshauptstadt Bayerns?',['Berlin','München','Nürnberg','Regensburg'],1),
 ('Welcher Fluss fließt durch Passau?',['Elbe','Oder','Donau','Weser'],2),
 ('Wie viele Bundesländer hat Deutschland?',['14','15','16','17'],2),
 ('Welche Farben hat die bayerische Flagge?',['Rot und Weiß','Blau und Weiß','Grün und Weiß','Schwarz und Gelb'],1),
 ('Was ist die Hauptstadt von Deutschland?',['Bonn','Hamburg','Berlin','Dresden'],2),
 ('Wie viele Minuten hat eine Stunde?',['30','45','60','90'],2),
 ('Welcher Planet ist der Sonne am nächsten?',['Venus','Mars','Merkur','Erde'],2),
 ('Wie heißt unser Stern?',['Sirius','Sonne','Polarstern','Mond'],1),
 ('Wie viele Beine hat eine Spinne?',['6','8','10','12'],1),
 ('Welcher Kontinent ist der flächenmäßig größte?',['Afrika','Europa','Asien','Australien'],2),
 ('Welche Stadt liegt in Schwaben?',['Berlin','Kiel','Rostock','Potsdam'],0),
 ('Was misst ein Thermometer?',['Druck','Geschwindigkeit','Temperatur','Helligkeit'],2),
 ('Wie viele Tage hat eine normale Woche?',['5','6','7','8'],2),
 ('Welches Gas benötigen Menschen zum Atmen?',['Helium','Sauerstoff','Stickstoff','Argon'],1),
 ('Welche Jahreszeit kommt nach dem Frühling?',['Winter','Herbst','Sommer','Frühling'],2),
 ('In welchem Land steht der Eiffelturm?',['Italien','Frankreich','Spanien','Belgien'],1),
 ('Welche Zahl ist die kleinste Primzahl?',['0','1','2','4'],2),
 ('Wie viele Ecken hat ein Dreieck?',['2','3','4','5'],1),
 ('Welcher Ozean liegt zwischen Europa und Nordamerika?',['Pazifik','Indischer Ozean','Atlantik','Arktischer Ozean'],2),
 ('Wie heißt die Währung in Deutschland?',['Franken','Euro','Krone','Pfund'],1),
 ('Welches Organ pumpt Blut durch den Körper?',['Leber','Lunge','Herz','Magen'],2),
 ('Welche Farbe entsteht aus Blau und Gelb?',['Orange','Violett','Grün','Rot'],2),
 ('Wie viele Monate hat ein Jahr?',['10','11','12','13'],2),
 ('Welche Stadt ist für den Kölner Dom bekannt?',['Berlin','Köln','Mainz','Erfurt'],1),
 ('Wie heißt gefrorenes Wasser?',['Dampf','Eis','Nebel','Tau'],1),
 ('Welches Tier ist ein Säugetier?',['Forelle','Frosch','Delfin','Eidechse'],2),
 ('Wie lautet die chemische Formel von Wasser?',['CO2','O2','H2O','NaCl'],2),
 ('Welcher Tag folgt auf Freitag?',['Montag','Donnerstag','Samstag','Sonntag'],2),
 ('Wie viele Zentimeter hat ein Meter?',['10','50','100','1000'],2),
 ('Welche Stadt ist die Hauptstadt Österreichs?',['Graz','Salzburg','Wien','Linz'],2),
 ('Welcher Vogel kann rückwärts fliegen?',['Adler','Kolibri','Pinguin','Schwan'],1),
 ('Was ist die Quadratwurzel aus 81?',['7','8','9','10'],2),
 ('Welches Land hat die Hauptstadt Rom?',['Griechenland','Italien','Portugal','Frankreich'],1),
 ('Wie viele Saiten hat eine gewöhnliche Gitarre?',['4','5','6','7'],2),
 ('Welche Pflanzenteile nehmen meist Wasser aus dem Boden auf?',['Blüten','Blätter','Wurzeln','Früchte'],2),
 ('Welche Einheit wird für elektrische Spannung verwendet?',['Ampere','Volt','Watt','Ohm'],1),
 ('Was ist die Einheit des elektrischen Widerstands?',['Volt','Watt','Ohm','Joule'],2),
 ('Welches Metall hat das chemische Symbol Fe?',['Gold','Eisen','Silber','Kupfer'],1),
 ('Wie viele Sekunden hat eine Minute?',['30','45','60','90'],2),
 ('In welcher Himmelsrichtung geht die Sonne ungefähr auf?',['Norden','Süden','Osten','Westen'],2),
 ('Wie heißt der höchste Berg Deutschlands?',['Watzmann','Feldberg','Zugspitze','Brocken'],2),
 ('Was bedeutet das Verkehrszeichen STOP?',['Langsam fahren','Vorfahrt gewähren und anhalten','Nur rechts abbiegen','Parken erlaubt'],1),
 ('Welcher Fluss fließt durch München?',['Isar','Rhein','Elbe','Mosel'],0),
 ('Wie viele Grad hat ein rechter Winkel?',['45','60','90','180'],2),
 ('Wie heißt die größte Stadt Bayerns?',['Nürnberg','München','Berlin','Würzburg'],1),
 ('Welcher Himmelskörper umkreist die Erde?',['Mars','Sonne','Mond','Venus'],2),
 ('Was ist die Hauptstadt der Schweiz?',['Zürich','Genf','Bern','Basel'],2),
 ('In welchem Monat beginnt das Kalenderjahr?',['März','Januar','Dezember','Februar'],1),
 ('Welches Instrument misst den Luftdruck?',['Barometer','Thermometer','Tachometer','Voltmeter'],0),
 ('Wie heißt die Hauptstadt von Baden-Württemberg?',['Karlsruhe','Stuttgart','Ulm','Freiburg'],1),
 ('Was ist 12 mal 12?',['124','144','132','154'],1),
]
def serkan_daily_quiz():
    day=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1))).astimezone().date().isoformat()
    # Date follows host local timezone (Europe/Berlin on this server).
    day=datetime.datetime.now().date().isoformat()
    yesterday=(datetime.datetime.now()-datetime.timedelta(days=1)).date().isoformat()
    previous=SERKAN_RANDOM.Random('serkan-home-'+yesterday).sample(SERKAN_QUESTIONS,5)
    pool=[q for q in SERKAN_QUESTIONS if q not in previous]
    rng=SERKAN_RANDOM.Random('serkan-home-'+day)
    entries=rng.sample(pool,5)
    return {'date':day,'questions':[{'question':q,'options':opts,'answer':idx} for q,opts,idx in entries]}
def serkan_news():
    with SERKAN_NEWS_LOCK:
        if time.time()-SERKAN_NEWS['at']<1800:return SERKAN_NEWS['items']
    try:
        items=[]
        for feed in SERKAN_NEWS_FEEDS:
            try:
                req=urllib.request.Request(feed,headers={'User-Agent':'SerkanSignage/1.0 (RSS reader)','Accept':'application/rss+xml,application/xml,text/xml'})
                with urllib.request.urlopen(req,timeout=8) as resp:
                    raw=resp.read(500000)
                root=SERKAN_ET.fromstring(raw)
                for item in root.iter():
                    if item.tag.rsplit('}',1)[-1]!='item':continue
                    fields={child.tag.rsplit('}',1)[-1]:(child.text or '').strip() for child in item}
                    headline=fields.get('title','')
                    link=fields.get('link','')
                    if not headline or urllib.parse.urlsplit(link).scheme!='https' or (urllib.parse.urlsplit(link).hostname or '').lower() not in NEWS_ALLOWED_HOSTS:continue
                    # RSS provides short summaries, not full copyrighted article text.
                    raw_summary=fields.get('description') or fields.get('summary') or fields.get('encoded') or ''
                    raw_summary=re.sub(r'<[^>]+>',' ',raw_summary)
                    raw_summary=html.unescape(raw_summary)
                    summary=' '.join(raw_summary.split())[:450]
                    items.append({'title':headline[:190],'summary':summary,'url':link,'published':fields.get('pubDate','')[:45]})
                    if len(items)>=7:break
                if items:break
            except Exception:
                continue
        if not items:raise ValueError('Keine passenden BR24 Nachrichten im RSS-Feed')
        with SERKAN_NEWS_LOCK:SERKAN_NEWS.update(at=time.time(),items=items)
    except Exception as err:
        print('BR24 RSS derzeit nicht verfuegbar:',type(err).__name__,flush=True)
        with SERKAN_NEWS_LOCK:SERKAN_NEWS['at']=time.time()
    with SERKAN_NEWS_LOCK:return SERKAN_NEWS['items']

class Handler(BaseHTTPRequestHandler):
    server_version='SerkanSignage'
    def log_message(self,fmt,*args): print('%s %s'%(self.address_string(),fmt%args),flush=True)
    def send(self,code,data,content_type='text/html; charset=utf-8',headers=None):
        if isinstance(data,str): data=data.encode()
        self.send_response(code);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(data)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');(self.send_header('Content-Security-Policy', 'frame-ancestors '+FRAME_ANCESTORS)
 if FRAME_ANCESTORS and urllib.parse.urlsplit(self.path).path == '/'
 else self.send_header('X-Frame-Options','DENY'));self.send_header('Referrer-Policy','no-referrer')
        for k,v in (headers or {}).items():self.send_header(k,v)
        self.end_headers();self.wfile.write(data)
    def form(self):
        length=int(self.headers.get('Content-Length','0'))
        if length>16000000: raise ValueError('Dosya çok büyük (en fazla 15 MB)')
        raw=self.rfile.read(length)
        ct=self.headers.get('Content-Type','')
        if ct.startswith('multipart/form-data'):
            msg=BytesParser(policy=default).parsebytes(('Content-Type: '+ct+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+raw)
            out={}
            for part in msg.iter_parts():
                key=part.get_param('name',header='content-disposition')
                if key:out[key]=(part.get_filename(),part.get_payload(decode=True)) if part.get_filename() is not None else part.get_content()
            return out
        return {k:v[0] for k,v in urllib.parse.parse_qs(raw.decode(),keep_blank_values=True).items()}
    def redirect(self,path,cookie=None): self.send(303,b'',headers={'Location':path,**({'Set-Cookie':cookie} if cookie else {})})
    def authorized(self): return good_session(self.headers.get('Cookie',''))
    def csrf(self): return hmac.new(SECRET_BYTES,b'admin-form',hashlib.sha256).hexdigest()
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        # SERKAN_PWA_V1
        if path in ('/pwa/manifest.webmanifest','/pwa/sw.js','/pwa/icon-192.png','/pwa/icon-512.png'):
            f=ROOT/'pwa'/path.rsplit('/',1)[1]
            if not f.is_file():return self.send(404,'Not found')
            typ='application/manifest+json' if path.endswith('.webmanifest') else ('application/javascript' if path.endswith('.js') else 'image/png')
            extra={'Service-Worker-Allowed':'/'} if path.endswith('/sw.js') else {}
            return self.send(200,f.read_bytes(),typ,extra)
        if path=='/api/extras':
            data={'news':serkan_news(),'quiz':serkan_daily_quiz(),'source':os.environ.get('NEWS_SOURCE_LABEL','BR24')}
            return self.send(200,json.dumps(data,ensure_ascii=False),'application/json; charset=utf-8')
        if path=='/health':return self.send(200,'ok','text/plain')
        if path=='/':return self.send(200,DISPLAY)
        if path=='/api/state':
            c=read_config();now=datetime.datetime.now().astimezone()
            data={'meals':c['meals'],'interval':c['interval'],'city':c['city'],'photos':photos(),'weather':weather(),'now':now.isoformat()}
            return self.send(200,json.dumps(data,ensure_ascii=False),'application/json; charset=utf-8')
        if path.startswith('/photo/'):
            bits=path.split('/')
            if len(bits)!=4 or bits[2] not in ('local','nas'):return self.send(404,'Not found')
            name=urllib.parse.unquote(bits[3]); folder=PHOTOS if bits[2]=='local' else NAS
            if '/' in name or '\\' in name or name.startswith('.') or Path(name).suffix.lower() not in ('.jpg','.jpeg','.png','.gif','.webp'):return self.send(404,'Not found')
            p=folder/name
            if not p.is_file() or p.is_symlink() or p.stat().st_size>16000000:return self.send(404,'Not found')
            return self.send(200,p.read_bytes(),mimetypes.guess_type(str(p))[0] or 'application/octet-stream')
        if path=='/serkan':
            if not self.authorized():return self.send(200,page('Anmelden','<h1>Serkan Signage Verwaltung</h1><form method="post" action="/login"><label>Administratorpasswort</label><input type="password" name="password" required><button>Anmelden</button></form>'))
            c=read_config();token=self.csrf(); meals=''.join('<label>'+esc(DAYS[i])+'</label><textarea name="meal'+str(i)+'">'+esc(c['meals'][i])+'</textarea>' for i in range(7))
            cards=''.join('<div>'+esc(p['name'])+' ('+esc(p['source'])+') '+ ('<form method="post" action="/delete" style="display:inline"><input type="hidden" name="csrf" value="'+token+'"><input type="hidden" name="name" value="'+esc(p['name'])+'"><button>Löschen</button></form>' if p['source']=='local' else '')+'</div>' for p in photos())
            content='<h1>Serkan Signage — Verwaltung</h1><p><a href="/">Anzeige öffnen</a> · <a href="/logout">Abmelden</a></p><section><h2>Speiseplan / Einstellungen</h2><form method="post" action="/save"><input type="hidden" name="csrf" value="'+token+'">'+meals+'<label>Bildwechsel (Sekunden)</label><input type="number" name="interval" min="5" max="3600" value="'+esc(c['interval'])+'"><label>Stadt</label><input name="city" value="'+esc(c['city'])+'"><label>Breitengrad</label><input name="lat" value="'+esc(c['lat'])+'"><label>Längengrad</label><input name="lon" value="'+esc(c['lon'])+'"><p><button>Speichern</button></p></form></section><section><h2>Foto hinzufügen</h2><p class="hint">NAS-Fotos werden automatisch aus dem verbundenen Signage-Ordner angezeigt. Du kannst auch eigene Bilder hochladen.</p><form action="/upload" method="post" enctype="multipart/form-data"><input type="hidden" name="csrf" value="'+token+'"><input type="file" name="image" accept="image/*" required><button>Hochladen</button></form><h3>Fotos</h3>'+cards+'</section><section><h2>Administratorpasswort</h2><form method="post" action="/password"><input type="hidden" name="csrf" value="'+token+'"><label>Aktuelles Passwort</label><input type="password" name="old" required><label>Neues Passwort (mindestens 12 Zeichen)</label><input type="password" name="new" required><button>Ändern</button></form></section>'
            return self.send(200,page('Yönetim',content))
        if path=='/logout':return self.redirect('/serkan','sd_session=; Max-Age=0'+COOKIE_FLAGS)
        return self.send(404,'Not found')
    def do_POST(self):
        path=urllib.parse.urlsplit(self.path).path
        try: f=self.form()
        except Exception as e:return self.send(400,page('Hata','<p class="error">'+esc(e)+'</p>'))
        if path=='/login':
            ip=self.client_address[0];recent=[x for x in fails.get(ip,[]) if time.time()-x<600]
            if len(recent)>=8:return self.send(429,page('Yavaşla','<p>Çok fazla deneme; 10 dakika sonra tekrar dene.</p>'))
            if not verify(str(f.get('password',''))):
                fails[ip]=recent+[time.time()]
                return self.send(401,page('Anmeldefehler','<p>Falsches Passwort. <a href="/serkan">Erneut versuchen</a></p>'))
            fails.pop(ip,None);cookie='sd_session='+session_value(int(time.time()),secrets.token_hex(12))+COOKIE_FLAGS
            return self.redirect('/serkan',cookie)
        if not self.authorized():return self.send(403,'Yetkisiz')
        if not hmac.compare_digest(str(f.get('csrf','')),self.csrf()):return self.send(403,'Geçersiz form')
        try:
            if path=='/save':
                c=read_config();c['meals']=[str(f.get('meal'+str(i),''))[:160] for i in range(7)]
                c['interval']=min(3600,max(5,int(f.get('interval','20'))));c['city']=str(f.get('city','Berlin'))[:60]
                c['lat']=float(f.get('lat','52.52'));c['lon']=float(f.get('lon','13.405'))
                if not -90<=c['lat']<=90 or not -180<=c['lon']<=180:raise ValueError('Ungültige Koordinaten')
                save_config(c)
                with lock:weather_cache['at']=0
            elif path=='/upload':
                name,data=f.get('image',(None,None));ext=Path(name or '').suffix.lower()
                if not name or ext not in ('.jpg','.jpeg','.png','.gif','.webp') or not data or len(data)>15000000:raise ValueError('Ungültige Datei (en fazla 15 MB)')
                checks={'.jpg':data.startswith(b'\xff\xd8\xff'),'.jpeg':data.startswith(b'\xff\xd8\xff'),'.png':data.startswith(b'\x89PNG\r\n\x1a\n'),'.gif':data.startswith((b'GIF87a',b'GIF89a')),'.webp':data.startswith(b'RIFF') and data[8:12]==b'WEBP'}
                if not checks[ext]:raise ValueError('Die Datei ist kein gültiges Bild')
                dest=PHOTOS/(secrets.token_hex(6)+ext);dest.write_bytes(data)
            elif path=='/delete':
                name=str(f.get('name',''))
                if not re.fullmatch(r'[0-9a-f]{12}\.(jpg|jpeg|png|gif|webp)',name):raise ValueError('Silme reddedildi')
                (PHOTOS/name).unlink(missing_ok=True)
            elif path=='/password':
                if not verify(str(f.get('old',''))):raise ValueError('Aktuelles Passwort yanlış')
                new=str(f.get('new',''))
                if len(new)<12:raise ValueError('Das neue Passwort muss mindestens 12 Zeichen haben')
                salt=secrets.token_bytes(16);digest=hashlib.pbkdf2_hmac('sha256',new.encode(),salt,260000)
                PASSFILE.write_text(json.dumps({'salt':salt.hex(),'hash':digest.hex()})); PASSFILE.chmod(0o600)
            else:return self.send(404,'Not found')
        except Exception as e:return self.send(400,page('Hata','<h2>Vorgang fehlgeschlagen</h2><p>'+esc(e)+'</p><a href="/serkan">Zurück</a>'))
        return self.redirect('/serkan')

DISPLAY='''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><title>SERKAN SIGNAGE</title><link rel="manifest" href="/pwa/manifest.webmanifest"><meta name="theme-color" content="#192630"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes"><style>
*{box-sizing:border-box}body{margin:0;background:#f5f6f7;font-family:Arial,sans-serif;color:#dce5eb}.frame{background:#192630;border-radius:16px;margin:2vh auto;padding:12px;width:96%;max-width:1400px;min-height:94vh}.top{height:34px;font-size:17px;font-weight:bold}.top span{float:right}.main{overflow:hidden}.left{width:59%;float:left;padding-right:8px}.right{width:41%;float:left}.panel{background:#293b49;border-radius:11px;padding:11px}.photo{height:58vh;min-height:200px;position:relative;background:#24323c;border-radius:8px;overflow:hidden}.photo img{width:100%;height:100%;object-fit:contain}.placeholder{position:absolute;top:45%;width:100%;text-align:center;color:#a9bdca}.under{height:25px;padding-top:8px;font-size:13px}.meals{height:calc(58vh + 49px);overflow:hidden}.heading{font-weight:bold;margin:0 0 15px}.meal{margin-bottom:12px}.day{font-size:11px;color:#a9bdcc}.food{font-size:14px;padding-top:4px}.weather{clear:both;padding-top:8px;overflow:hidden}.wday{width:14.285%;float:left;padding-right:7px;text-align:center}.wday:last-child{padding-right:0}.wbox{background:#293b49;border-radius:9px;height:95px;padding:9px 2px}.wdate{font-size:12px}.wicon{font-size:24px;margin:9px 0}.temp{font-size:15px;font-weight:bold}.foot{font-size:11px;color:#a9bdcc;margin-top:9px}.muted{color:#a9bdcc}@media(max-width:570px){.frame{margin:0;width:100%;border-radius:0;min-height:100vh}.left,.right{width:100%;float:none;padding:0}.right{margin-top:8px}.photo{height:42vh}.meals{height:auto;min-height:160px}.meal{display:inline-block;vertical-align:top;width:32%;margin-bottom:8px}.wday{width:25%;margin-bottom:7px}.weather{padding-top:8px}.top{font-size:14px}}
</style><style>/* SERKAN_NEWS_QUIZ_V1 */
.serkan-extras{clear:both;display:table;width:100%;table-layout:fixed;margin-top:10px}
.serkan-extra{display:table-cell;width:50%;vertical-align:top;background:#293b49;border-radius:10px;padding:13px 16px}
.serkan-extra:first-child{border-right:7px solid #192630}
.sx-title{font-size:16px;font-weight:bold;margin-bottom:10px;color:#edf2f5}
.sx-small{font-weight:normal;font-size:11px;color:#a9c3d4;margin-left:7px}
.sx-news-item{padding:7px 0;border-bottom:1px solid #425362;line-height:1.35;font-size:14px}
.sx-news-item:last-child{border-bottom:0}
.sx-news-item a{color:#e8f3ff;text-decoration:none}
.sx-news-item a:hover{text-decoration:underline}
.sx-text{font-size:14px;color:#e0edf5}
.sx-question{font-weight:bold;margin:8px 0 10px;line-height:1.5}
.sx-choice,.sx-next{display:block;width:100%;max-width:100%;padding:8px 10px;margin:5px 0;background:#39576a;border:1px solid #65869a;border-radius:6px;color:#fff;font-family:Arial;font-size:13px;cursor:pointer;text-align:left}
.sx-choice:disabled{opacity:.75;cursor:default}
.sx-result{font-size:13px;padding:9px 0;font-weight:bold}
.sx-next{background:#24799b;text-align:center;font-weight:bold}
@media(max-width:650px){.serkan-extra{display:block;width:100%;border-right:0!important;margin-bottom:8px}}
</style><style>/* SERKAN_TV_AUTOPLAY_V2 */
.sx-news-headline{font-size:17px;font-weight:bold;color:#fff;line-height:1.4;margin:10px 0 12px}
.sx-news-detail{font-size:15px;line-height:1.55;color:#deedf6;min-height:100px;overflow-wrap:break-word}
.sx-rotation-info{font-size:11px;color:#a9c3d4;margin-top:12px}
.sx-tv-choice{display:block;width:auto;padding:8px 10px;margin:5px 0;background:#39576a;border:1px solid #65869a;border-radius:6px;color:white;font-size:13px}
.sx-tv-correct{background:#187044!important;border-color:#70dfa4!important;font-weight:bold}
.sx-tv-result{font-size:13px;color:#c6e2ed;font-weight:bold;padding-top:8px}
.serkan-extra{min-height:245px}



/* SERKAN_BORDO_FRAME_V2 */
.frame {
  border: 3px solid #8B1E24 !important;
  box-sizing: border-box !important;
}
.frame .panel,
.frame .weather,
.frame .serkan-extra,
.frame .top,
.frame #pwa-tools {
  border: 2px solid #8B1E24 !important;
  box-sizing: border-box !important;
}
.frame .panel,
.frame .weather,
.frame .serkan-extra {
  box-shadow: 0 0 9px rgba(139,30,36,0.22) !important;
}
</style>
<style>/* SERKAN_TV_SINGLE_STAGE_V3 */
#serkan-extras.serkan-extras{
 display:block!important;
 width:100%!important;
 margin-top:10px!important;
}
#serkan-extras>.serkan-extra{
 display:none!important;
 width:100%!important;
 min-height:245px!important;
 box-sizing:border-box!important;
 border:2px solid #8B1E24!important;
 border-radius:10px!important;
 background:#293b49!important;
 padding:15px 18px!important;
}
#serkan-extras>.serkan-extra.sx-active{
 display:block!important;
}
</style>
</head><body><div class="frame"><div id="pwa-tools" style="background:#293b49;padding:6px 10px;border-radius:8px;margin:0 0 6px;min-height:26px;font:12px Arial,sans-serif"><button id="geo-btn" type="button" style="padding:4px 8px;background:#315a70;border:0;border-radius:5px;color:white">📍 Standort verwenden</button> <button id="full-btn" type="button" style="padding:4px 8px;background:#315a70;border:0;border-radius:5px;color:white">⛶ Vollbild</button> <span id="geo-status" style="padding-left:5px;color:#cbd9e2">Wetter: gespeicherter Ort</span></div><div class="top">SERKAN SIGNAGE <span id="clock">—</span></div><div class="main"><div class="left"><div class="panel"><div class="photo"><img id="pic" style="display:none" alt="Fotoğraf"><div class="placeholder" id="empty">Fotos können in der Verwaltung hinzugefügt werden</div></div><div class="under">NAS-Fotos <span id="count" style="float:right">● ○ ○</span></div></div></div><div class="right"><div class="panel meals"><div class="heading">Wöchentlicher Speiseplan</div><div id="meals"></div></div></div></div><div class="weather" id="weather"></div><div id="serkan-extras" class="serkan-extras"><div class="serkan-extra"><div class="sx-title">📰 Aktuelles aus Bayern <span class="sx-small">BR24</span></div><div id="sx-news" class="sx-text">Nachrichten werden geladen …</div></div><div class="serkan-extra"><div class="sx-title">🧠 5 Fragen des Tages <span class="sx-small" id="sx-progress"></span></div><div id="sx-quiz" class="sx-text">Tagesquiz wird geladen …</div></div></div><div class="foot">Serkan Signage · <span id="city">—</span> · Wird automatisch aktualisiert</div></div><script>
(function(){var state=null,index=0,lastSlide=0,days=['Mo','Di','Mi','Do','Fr','Sa','So'];function id(x){return document.getElementById(x)}function clear(x){while(x.firstChild)x.removeChild(x.firstChild)}function txt(parent,tag,text,cls){var e=document.createElement(tag);if(cls)e.className=cls;e.appendChild(document.createTextNode(text));parent.appendChild(e);return e}function icon(c){if(c===0)return '☀';if(c<4)return '🌤';if(c<50)return '☁';if(c<70)return '🌧';if(c<80)return '❄';return '⛈'}function render(){if(!state)return;if(window.serkanGeoWeather){state.weather=window.serkanGeoWeather;state.city=window.serkanGeoCity||state.city;}id('city').innerHTML='';txt(id('city'),'span',state.city);var m=id('meals');clear(m);for(var i=0;i<7;i++){var box=txt(m,'div','', 'meal');txt(box,'div',['Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag'][i],'day');txt(box,'div',state.meals[i]||'—','food')}var w=id('weather');clear(w);for(var j=0;j<7;j++){var x=state.weather[j]||null;var outer=txt(w,'div','','wday');var card=txt(outer,'div','','wbox');txt(card,'div',x?days[(new Date(x.date+'T12:00:00').getDay()+6)%7]:'—','wdate');txt(card,'div',x?icon(x.code):'–','wicon');txt(card,'div',x?x.hi+'°':'—','temp')}show()}function show(){if(!state||!state.photos.length){id('pic').style.display='none';id('empty').style.display='block';id('count').innerHTML='○ ○ ○';return}index=index%state.photos.length;id('pic').src=state.photos[index].url;id('pic').style.display='block';id('empty').style.display='none';id('count').innerHTML=(index+1)+' / '+state.photos.length}window.serkanForceRefresh=function(){refresh();};function refresh(){var xhr=new XMLHttpRequest();xhr.open('GET','/api/state?t='+new Date().getTime(),true);xhr.onreadystatechange=function(){if(xhr.readyState===4&&xhr.status===200){try{state=JSON.parse(xhr.responseText);render()}catch(e){}}};xhr.send(null)}function tick(){var d=new Date();var two=function(n){return n<10?'0'+n:''+n};id('clock').innerHTML=['Sonntag','Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag'][d.getDay()]+' · '+d.getDate()+'.'+two(d.getMonth()+1)+'.'+d.getFullYear()+' · '+two(d.getHours())+':'+two(d.getMinutes());if(state&&state.photos.length&&d.getTime()-lastSlide>(state.interval||20)*1000){index++;show();lastSlide=d.getTime()}}refresh();tick();setInterval(tick,1000);setInterval(refresh,60000)})();
</script><script>/* SERKAN_PWA_V1 */
(function(){
 function byid(x){return document.getElementById(x);}
 function status(msg){byid('geo-status').textContent=msg;}
 function full(){var el=document.documentElement;var f=el.requestFullscreen||el.webkitRequestFullscreen||el.mozRequestFullScreen||el.msRequestFullscreen;if(f){f.call(el);}else{status('Vollbild: im Browser „Zum Startbildschirm“ wählen');}}
 function useLocation(){
   if(!window.isSecureContext && location.protocol!=='https:' && location.hostname!=='localhost'){status('Standort benötigt HTTPS (gesicherte Verbindung)');return;}
   if(!navigator.geolocation){status('Standort auf diesem Browser nicht verfügbar');return;}
   status('Standortfreigabe wird angefragt …');
   navigator.geolocation.getCurrentPosition(function(pos){
     var lat=pos.coords.latitude,lon=pos.coords.longitude;
     var url='https://api.open-meteo.com/v1/forecast?latitude='+encodeURIComponent(lat)+'&longitude='+encodeURIComponent(lon)+'&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=auto&forecast_days=7';
     var x=new XMLHttpRequest();x.open('GET',url,true);x.onreadystatechange=function(){if(x.readyState!==4)return;if(x.status!==200){status('Wetter konnte nicht geladen werden');return;}try{var d=JSON.parse(x.responseText).daily,a=[];for(var i=0;i<d.time.length;i++){a.push({date:d.time[i],hi:Math.round(d.temperature_2m_max[i]),lo:Math.round(d.temperature_2m_min[i]),code:d.weather_code[i]});}window.serkanGeoWeather=a;window.serkanGeoCity='Mein Standort';status('Wetter: aktueller Standort');if(typeof window.serkanForceRefresh==='function')window.serkanForceRefresh();}catch(e){status('Wetterdaten ungültig');}};x.send(null);
   },function(err){status(err.code===1?'Standort nicht freigegeben':'Standort nicht ermittelbar');},{enableHighAccuracy:false,timeout:12000,maximumAge:1800000});
 }
 byid('geo-btn').onclick=useLocation;
 byid('full-btn').onclick=full;
 if('serviceWorker' in navigator && (location.protocol==='https:'||location.hostname==='localhost'))navigator.serviceWorker.register('/pwa/sw.js').catch(function(){});
 /* Geolocation is opt-in via the location button. */
})();
</script><script>/* SERKAN_TV_SINGLE_STAGE_V3 */
(function(){
var news=[],quiz=[],day="",ni=0,qi=0;
var stage="news",started=Date.now(),last=-1;

function id(x){return document.getElementById(x);}
function clear(e){if(e)while(e.firstChild)e.removeChild(e.firstChild);}
function add(e,tag,text,cls){
 var n=document.createElement(tag);
 if(cls)n.className=cls;
 n.appendChild(document.createTextNode(text));
 e.appendChild(n);
 return n;
}
function switchPanel(){
 var e=id("serkan-extras");
 if(!e||e.children.length<2)return;
 e.children[0].className="serkan-extra"+(stage==="news"?" sx-active":"");
 e.children[1].className="serkan-extra"+(stage==="quiz"?" sx-active":"");
}
function showNews(){
 var e=id("sx-news");if(!e)return;clear(e);
 if(!news.length){
   add(e,"div","BR24-Nachrichten werden geladen ...");
   return;
 }
 var n=news[ni%news.length];
 add(e,"div",n.title||"BR24","sx-news-headline");
 add(e,"div",n.summary||"Keine Kurzbeschreibung verfügbar.","sx-news-detail");
 add(e,"div","BR24 · Meldung "+((ni%news.length)+1)+" / "+news.length,"sx-rotation-info");
}
function showQuiz(now){
 var e=id("sx-quiz");if(!e)return;clear(e);
 if(!quiz.length){
   add(e,"div","Tagesfragen werden geladen ...");
   return;
 }
 var q=quiz[qi%quiz.length];
 var remain=Math.max(0,10000-(now-started));
 var reveal=remain<=2000;
 var progress=id("sx-progress");
 if(progress)progress.textContent=((qi%quiz.length)+1)+" / "+quiz.length;
 add(e,"div",q.question,"sx-question");
 for(var i=0;i<q.options.length;i++){
   var cls="sx-tv-choice";
   if(reveal&&i===q.answer)cls+=" sx-tv-correct";
   add(e,"div",String.fromCharCode(65+i)+". "+q.options[i],cls);
 }
 var message=reveal?
   "✓ Richtige Antwort: "+String.fromCharCode(65+q.answer)+". "+q.options[q.answer]:
   "Antwort in "+Math.ceil(Math.max(0,remain-2000)/1000)+" Sekunden";
 add(e,"div",message,"sx-tv-result");
}
function load(){
 var x=new XMLHttpRequest();
 x.open("GET","/api/extras?t="+Date.now(),true);
 x.onreadystatechange=function(){
   if(x.readyState!==4||x.status!==200)return;
   try{
     var d=JSON.parse(x.responseText);
     if(d.news&&d.news.length){
       news=d.news;
       if(stage==="news")showNews();
     }
     if(d.quiz&&d.quiz.questions&&d.quiz.questions.length){
       if(d.quiz.date!==day){
         day=d.quiz.date;
         qi=0;
       }
       quiz=d.quiz.questions;
       if(stage==="quiz")showQuiz(Date.now());
     }
   }catch(err){}
 };
 x.send(null);
}
function tick(){
 var now=Date.now();
 if(now-started>=10000){
   if(stage==="news"){
     stage="quiz";
   }else{
     stage="news";
     if(news.length)ni=(ni+1)%news.length;
     if(quiz.length)qi=(qi+1)%quiz.length;
   }
   started=now;
   last=-1;
   switchPanel();
   if(stage==="news")showNews();
   else showQuiz(now);
   return;
 }
 if(stage==="quiz"){
   var second=Math.floor((now-started)/1000);
   if(second!==last){
     last=second;
     showQuiz(now);
   }
 }
}
switchPanel();
showNews();
load();
setInterval(tick,250);
setInterval(load,300000);
})();
</script></body></html>'''

if __name__=='__main__':ThreadingHTTPServer((HTTP_HOST,HTTP_PORT),Handler).serve_forever()