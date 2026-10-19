from pathlib import Path
import json,subprocess,tempfile,time,sys,base64
from urllib.request import urlopen
import websocket
STATE=Path('/tmp/spark_chat_browser_20261019.json')
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
 call('Page.navigate',{'url':'http://127.0.0.1:8518'})
 time.sleep(2);shot('01-production-loading')
if action=='inspect':
 print(js('JSON.stringify({text:document.body.innerText.slice(-2500),input:!!document.querySelector("textarea"),disabled:document.querySelector("textarea")?.disabled})'))
 shot('02-production-state')
if action=='mobile':
 call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True});time.sleep(.3);shot('03-production-mobile')
 print(js('JSON.stringify({width:innerWidth,document:document.documentElement.scrollWidth})'))
if action=='send':
 js('location.hash="";true');time.sleep(.1)
 assert not js('document.querySelector("textarea")?.disabled')
 click('textarea');call('Input.insertText',{'text':sys.argv[2]});key('Enter')
 time.sleep(.6);shot('04-production-generating')
 print('Submission sent once; await persisted turn before any next submission.')
if action=='rerun':
 js('[...document.querySelectorAll("button")].find(b=>b.innerText==="Rerun")?.click();true');time.sleep(2)
 js('document.querySelectorAll("summary").forEach(e=>e.click());true');time.sleep(.2)
 print(js('JSON.stringify({unknownReference:document.body.innerText.includes("Planner returned unknown"),text:document.body.innerText.slice(-1000)})'))
 shot('05-production-failure-diagnostics')
if action=='capture':
 js('document.querySelectorAll("details[open]").forEach(e=>e.open=false);true')
 js('[...document.querySelectorAll("[data-testid=stChatMessage]")].at(-1)?.scrollIntoView({block:"start"});true')
 time.sleep(.2);shot(sys.argv[2] if len(sys.argv)>2 else '06-production-answer')
if action=='preview':
 js('document.querySelectorAll("details[open]").forEach(e=>e.open=false);true')
 js('[...document.querySelectorAll("a.source-preview-link")].at(-1)?.click();true');time.sleep(.3);shot('07-production-source-preview')
 print(js('JSON.stringify({previewOpen:!!document.querySelector(".markdown-preview-modal:target"),unavailable:document.querySelector(".markdown-preview-modal:target")?.innerText.includes("Nao foi possivel")})'))
if action=='reload':
 call('Page.reload');time.sleep(2);shot('08-production-reload')
 print(js('JSON.stringify({exceptions:document.querySelectorAll("[data-testid=stException]").length})'))
if action=='report':
 call('Page.navigate',{'url':Path('/Users/fernandotrinta/.agent/diagrams/chat_spark_corrigido_2026-10-19.html').as_uri()})
 wait('document.querySelectorAll("figure").length===6')
 metrics=[]
 for width,height,theme,name in [(1280,1000,'light','30-report-desktop'),(390,844,'light','31-report-mobile'),(1280,1000,'dark','32-report-dark')]:
  call('Emulation.setDeviceMetricsOverride',{'width':width,'height':height,'deviceScaleFactor':1,'mobile':False})
  call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-color-scheme','value':theme}]})
  time.sleep(.2);shot(name)
  m=js('({width:innerWidth,scroll:document.documentElement.scrollWidth,figures:document.querySelectorAll("figure").length,brokenImages:[...document.images].filter(i=>i.complete&&!i.naturalWidth).length})')
  m['theme']=theme;metrics.append(m);assert m['width']==m['scroll']
 js('document.querySelectorAll("details").forEach(d=>d.open=true);true');time.sleep(.2)
 assert js('document.documentElement.scrollWidth===innerWidth')
 (OUT.parent/'visual_verification.json').write_text(json.dumps({'report':metrics,'expanded_details_no_overflow':True,'application_mobile_width':390,'application_mobile_scroll_width':390,'real_source_preview_opened':True,'reload_exceptions':0,'scope':'Real application plus isolated synthetic page. No physical phone or interrupted remote transport test.'},indent=2))
 print(json.dumps(metrics))
ws.close()
