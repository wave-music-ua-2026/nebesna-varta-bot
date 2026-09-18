import asyncio, json, logging, os
from pathlib import Path
import aiohttp
from dotenv import load_dotenv

load_dotenv()
TG_TOKEN=os.environ['TELEGRAM_BOT_TOKEN']
ALERT_TOKEN=os.environ['ALERTS_API_TOKEN']
CHANNEL=os.getenv('TELEGRAM_CHANNEL','@NebesnaVartaUA')
POLL=max(int(os.getenv('POLL_SECONDS','10')),7)
API='https://api.alerts.in.ua/v1/alerts/active.json'
STATE=Path(os.getenv('STATE_FILE','state.json'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log=logging.getLogger('nebesna-varta')

def key(a):
    return str(a.get('id') or '|'.join(str(a.get(x,'')) for x in ('location_title','location_type','alert_type','started_at')))

def normalize(data):
    arr=data.get('alerts',[]) if isinstance(data,dict) else data
    return {key(a):a for a in arr if isinstance(a,dict)}

def title(a): return a.get('location_title') or a.get('location_title_en') or 'Україна'
def typ(a): return str(a.get('alert_type') or a.get('type') or 'air_raid').lower()

def start_msg(a):
    t=typ(a); loc=title(a)
    if 'artillery' in t: head='⚠️ ЗАГРОЗА АРТОБСТРІЛУ'
    elif 'urban' in t or 'chemical' in t: head='⚠️ ЗАГРОЗА'
    else: head='🚨 ПОВІТРЯНА ТРИВОГА'
    return f"<b>{head}</b>\n📍 {loc}\n\nПерейдіть в укриття та стежте за офіційними повідомленнями.\n\n🛡 <b>Небесна Варта | Україна</b>"

def end_msg(a):
    return f"🟢 <b>ВІДБІЙ ТРИВОГИ</b>\n📍 {title(a)}\n\nСтежте за офіційними повідомленнями.\n\n🛡 <b>Небесна Варта | Україна</b>"

async def send(session,text):
    url=f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage'
    async with session.post(url,json={'chat_id':CHANNEL,'text':text,'parse_mode':'HTML','disable_web_page_preview':True},timeout=15) as r:
        body=await r.text()
        if r.status!=200: raise RuntimeError(f'Telegram {r.status}: {body}')

def load_state():
    try: return json.loads(STATE.read_text('utf-8'))
    except Exception: return {}

def save_state(s):
    tmp=STATE.with_suffix('.tmp'); tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2),'utf-8'); tmp.replace(STATE)

async def main():
    headers={'Authorization':f'Bearer {ALERT_TOKEN}','User-Agent':'NebesnaVartaUA/1.0'}
    timeout=aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout,headers=headers) as session:
        previous=load_state(); initialized=bool(previous)
        etag=lastmod=None; backoff=POLL
        while True:
            try:
                h={}
                if etag: h['If-None-Match']=etag
                if lastmod: h['If-Modified-Since']=lastmod
                async with session.get(API,headers=h) as r:
                    if r.status==304:
                        await asyncio.sleep(POLL); continue
                    if r.status==429:
                        retry=int(r.headers.get('Retry-After','60')); log.warning('Rate limited; sleeping %ss',retry); await asyncio.sleep(retry); continue
                    if r.status in (401,403): raise RuntimeError(f'alerts.in.ua authorization error HTTP {r.status}')
                    r.raise_for_status(); data=await r.json(content_type=None)
                    etag=r.headers.get('ETag',etag); lastmod=r.headers.get('Last-Modified',lastmod)
                current=normalize(data)
                if not initialized:
                    # Baseline only: prevents a flood of old active alerts on first launch.
                    previous=current; save_state(previous); initialized=True
                    log.info('Baseline saved: %d active alerts',len(current))
                else:
                    for k,a in current.items():
                        if k not in previous:
                            await send(session,start_msg(a)); log.info('START %s',title(a))
                    for k,a in previous.items():
                        if k not in current:
                            await send(session,end_msg(a)); log.info('END %s',title(a))
                    previous=current; save_state(previous)
                backoff=POLL
            except asyncio.CancelledError: raise
            except Exception as e:
                log.exception('Loop error: %s',e); await asyncio.sleep(backoff); backoff=min(backoff*2,120); continue
            await asyncio.sleep(POLL)

if __name__=='__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
