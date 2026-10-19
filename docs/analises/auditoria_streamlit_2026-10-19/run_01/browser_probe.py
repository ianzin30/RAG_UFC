from pathlib import Path
import json,subprocess,tempfile,time,sys,base64
from urllib.request import urlopen
import websocket
STATE=Path('/tmp/streamlit_audit_browser_20261019.json')
OUT=Path('/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC/docs/analises/auditoria_streamlit_2026-10-19/run_01/screenshots');OUT.mkdir(exist_ok=True)
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
if action=='start':
 call('Emulation.setDeviceMetricsOverride',{'width':1280,'height':1000,'deviceScaleFactor':1,'mobile':False})
 call('Page.navigate',{'url':'http://127.0.0.1:8519'})
 wait('document.querySelector("textarea")!==null')
 shot('01-ready')
if action=='send':
 key('Escape')
 click('textarea');call('Input.insertText',{'text':sys.argv[2] if len(sys.argv)>2 else 'Quem financia Atlas?'})
 key('Enter');time.sleep(.6);shot('02-progress')
 wait('document.body.innerText.includes("Resposta pronta.")',15);time.sleep(.2);shot('03-response-sources')
if action=='buttons':
 print(js('JSON.stringify([...document.querySelectorAll("button,[role=combobox]")].map(e=>({text:e.innerText,label:e.getAttribute("aria-label"),testid:e.getAttribute("data-testid"),x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y})))'))
if action=='inspect' or action=='start':
 print(js('JSON.stringify({text:document.body.innerText,inputs:[...document.querySelectorAll("textarea,input,select,[role=combobox]")].map(e=>({tag:e.tagName,role:e.getAttribute("role"),testid:e.getAttribute("data-testid"),label:e.getAttribute("aria-label")}))})'))
if action=='scenario':
 js('document.querySelector("[data-testid=stExpandSidebarButton]")?.click();true');time.sleep(.3)
 click('[data-testid=stSidebar] [data-baseweb=select]');time.sleep(.2)
 print(js('JSON.stringify([...document.querySelectorAll("[role=option]")].map(e=>({text:e.innerText})))'))
if action=='error':
 js('location.hash="";true');time.sleep(.2)
 js('document.querySelector("[data-testid=stExpandSidebarButton]")?.click();true');time.sleep(.2)
 if not js('document.querySelectorAll("[role=option]").length'):click('[data-testid=stSidebar] [data-baseweb=select]')
 time.sleep(.2)
 options=js('JSON.stringify([...document.querySelectorAll("[role=option]")].map(e=>({text:e.innerText})))')
 print(options)
 js('[...document.querySelectorAll("[role=option]")].find(e=>e.innerText==="error").click()');time.sleep(.4)
 click('textarea');call('Input.insertText',{'text':'Pergunta com erro simulado'});key('Enter')
 wait('document.body.innerText.includes("Nao consegui gerar")',15);shot('04-generation-error')
if action=='source':
 key('Escape')
 js('document.querySelector("a.source-preview-link").click();true');time.sleep(.3);shot('06-source-preview')
 print(js('JSON.stringify({hash:location.hash,modalText:document.querySelector(".markdown-preview-modal:target")?.innerText})'))
if action=='mobile':
 call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True});time.sleep(.4)
 shot('05-mobile');print(js('JSON.stringify({width:innerWidth,doc:document.documentElement.scrollWidth})'))
if action=='report':
 call('Page.navigate',{'url':Path('/Users/fernandotrinta/.agent/diagrams/auditoria_chat_streamlit_2026-10-19.html').as_uri()})
 wait('document.querySelectorAll("figure").length===6')
 metrics=[]
 for width,height,theme,name in [(1280,1000,'light','07-report-desktop'),(390,844,'light','08-report-mobile'),(1280,1000,'dark','09-report-dark')]:
  call('Emulation.setDeviceMetricsOverride',{'width':width,'height':height,'deviceScaleFactor':1,'mobile':False})
  call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-color-scheme','value':theme}]})
  time.sleep(.2);shot(name)
  m=js('({width:innerWidth,scroll:document.documentElement.scrollWidth,figures:document.querySelectorAll("figure").length,brokenImages:[...document.images].filter(i=>i.complete&&!i.naturalWidth).length})')
  m['theme']=theme;metrics.append(m)
  assert m['width']==m['scroll'],m
 js('document.querySelectorAll("details").forEach(d=>d.open=true);true');time.sleep(.2)
 assert js('document.documentElement.scrollWidth===innerWidth')
 print(json.dumps(metrics))
 (OUT.parent/'report_visual_verification.json').write_text(json.dumps({'viewports':metrics,'expanded_details_no_document_overflow':True},indent=2))
ws.close()
