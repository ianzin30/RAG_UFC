from pathlib import Path
import json,subprocess,tempfile,time,sys,base64
from urllib.request import urlopen
import websocket
STATE=Path('/tmp/spark_fixture_browser_20261019.json')
OUT=Path('/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/docs/analises/correcao_chat_spark_2026-10-19/screenshots');OUT.mkdir(parents=True,exist_ok=True)
if not STATE.exists():
 root=Path(tempfile.mkdtemp(prefix='streamlit-audit-browser-'));log=(root/'chrome.log').open('w')
 p=subprocess.Popen(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0','--user-data-dir='+str(root/'profile'),'about:blank'],stdout=log,stderr=log,start_new_session=True)
 for _ in range(100):
  f=root/'profile/DevToolsActivePort'
  if f.exists():break
  time.sleep(.1)
 STATE.write_text(json.dumps({'pid':p.pid,'root':str(root),'port':int(f.read_text().splitlines()[0])}))
state=json.loads(STATE.read_text());targets=json.load(urlopen(f'http://127.0.0.1:{state["port"]}/json/list'))
page=next(t for t in targets if t['type']=='page');ws=websocket.create_connection(page['webSocketDebuggerUrl'],suppress_origin=True,timeout=30)
serial=0

def call(method,params=None):
 global serial
 serial+=1;ident=serial;ws.send(json.dumps({'id':ident,'method':method,'params':params or {}}))
 while True:
  msg=json.loads(ws.recv())
  if msg.get('id')==ident:
   if msg.get('error'):raise RuntimeError(msg['error'])
   return msg.get('result',{})

def js(expression):
 r=call('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True})
 if 'exceptionDetails' in r:raise RuntimeError(r['exceptionDetails'])
 return r['result'].get('value')

def wait(expression,seconds=12):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  if js(expression):return
  time.sleep(.15)
 raise RuntimeError('UI wait timed out: '+expression)

def shot(name):
 result=call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
 (OUT/(name+'.png')).write_bytes(base64.b64decode(result['data']))

def click(selector):
 p=js('(()=>{const e=document.querySelector('+json.dumps(selector)+');if(!e)throw new Error("missing element");e.scrollIntoView();const r=e.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2}})()')
 for typ in ['mousePressed','mouseReleased']:call('Input.dispatchMouseEvent',{'type':typ,**p,'button':'left','clickCount':1})

def key(name):
 for typ in ['keyDown','keyUp']:call('Input.dispatchKeyEvent',{'type':typ,'key':name,'code':name,'windowsVirtualKeyCode':{'Enter':13,'ArrowDown':40,'Escape':27}.get(name,0)})


action=sys.argv[1] if len(sys.argv)>1 else 'inspect'
call('Page.enable');call('Runtime.enable')
call('Emulation.setDeviceMetricsOverride',{'width':1280,'height':1000,'deviceScaleFactor':1,'mobile':False})
if action=='open':
 call('Page.navigate',{'url':'http://127.0.0.1:8519'})
 time.sleep(2);shot('10-fixture-loading')
if action=='inspect':
 print(js('JSON.stringify({text:document.body.innerText.slice(-2500),input:!!document.querySelector("textarea"),disabled:document.querySelector("textarea")?.disabled})'))
 shot('11-fixture-state')
if action=='mobile':
 call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True});time.sleep(.3);shot('12-fixture-mobile')
 print(js('JSON.stringify({width:innerWidth,document:document.documentElement.scrollWidth})'))
if action=='send':
 assert not js('document.querySelector("textarea")?.disabled')
 click('textarea');call('Input.insertText',{'text':sys.argv[2]});key('Enter')
 time.sleep(.6);shot('13-fixture-generating')
 print('Submission sent once; await persisted turn before any next submission.')
if action=='error':
 js('document.querySelector("[data-testid=stExpandSidebarButton]")?.click();true');time.sleep(.2)
 click('[data-testid=stSidebar] [data-baseweb=select]');time.sleep(.2)
 js('[...document.querySelectorAll("[role=option]")].find(e=>e.innerText==="error").click();true');time.sleep(.4)
 click('textarea');call('Input.insertText',{'text':'Pergunta com falha simulada'});key('Enter');time.sleep(3)
 shot('14-fixture-error')
if action=='reload':
 call('Page.reload');time.sleep(3);shot('15-fixture-restored')
 print(js('JSON.stringify({restored:document.body.innerText.includes("Atlas é financiado por Aurora."),exceptions:document.querySelectorAll("[data-testid=stException]").length})'))
ws.close()
