"""Release checks against real browser engines; no screenshot mocks."""
import asyncio, json, os
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path('test-results')
OUT.mkdir(exist_ok=True)
BASE = os.environ.get('TEST_BASE_URL', 'http://127.0.0.1:3000')
RESULTS = []

async def record(name, condition, detail=''):
    RESULTS.append({'name':name, 'pass':bool(condition), 'detail':detail})
    print(('PASS ' if condition else 'FAIL ') + name + (' '+str(detail) if detail else ''), flush=True)
    if not condition:
        raise AssertionError(f'{name}: {detail}')

async def metrics(page):
    return await page.evaluate('''()=>{
      const box=s=>{let r=document.querySelector(s).getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};
      let canvas=document.querySelector('#renderHost canvas'), sample=document.createElement('canvas');
      sample.width=64;sample.height=64;let ctx=sample.getContext('2d');ctx.drawImage(canvas,0,0,64,64);
      let pixels=ctx.getImageData(0,0,64,64).data, visible=0;
      for(let i=3;i<pixels.length;i+=4)if(pixels[i]>20)visible++;
      return {width:document.documentElement.scrollWidth,innerWidth,innerHeight,stage:box('#renderHost'),caption:box('#fixedCaption'),dock:box('#controls'),title:box('.stage-typography'),visible,
       controls:[...document.querySelectorAll('.site-header button,.chapter,.dock-actions button,#nextBtn')].filter(e=>e.getBoundingClientRect().width>0).map(e=>({id:e.id||e.className,...{w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height}})),
       backend:window.__NOCTURNE__.state.rendererName};}''')

async def open_page(context, native=False):
    page=await context.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
    await page.goto(BASE+('/?renderer=native' if native else '/'),wait_until='networkidle')
    await page.wait_for_function("window.__NOCTURNE__ && window.__NOCTURNE__.renderer && document.querySelector('#renderHost canvas')",timeout=45000)
    await page.wait_for_timeout(1900)
    return page,errors

async def main():
  async with async_playwright() as p:
    for engine in ['chromium','webkit']:
      args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'] if engine=='chromium' else []
      browser=await getattr(p,engine).launch(headless=True,args=args)
      for name,w,h,touch in [('phone',390,844,True),('small',320,568,True),('short',375,667,True),('android',360,740,True),('wide',430,932,True),('landscape',844,390,True),('tablet',768,1024,True),('desktop',1440,900,False)]:
        context=await browser.new_context(viewport={'width':w,'height':h},device_scale_factor=1,is_mobile=touch,has_touch=touch,reduced_motion='reduce',accept_downloads=True)
        page,errors=await open_page(context)
        m=await metrics(page)
        tag=f'{engine}/{name}'
        await record(tag+'/three-renderer',m['backend']=='Three.js r180',m['backend'])
        await record(tag+'/sculpture-visible',m['visible']>100,m['visible'])
        await record(tag+'/no-horizontal-overflow',m['width']<=w+1,m['width'])
        await record(tag+'/dock-visible',m['dock']['bottom']<=h and m['dock']['y']>=0)
        if touch:
          await record(tag+'/touch-targets',all(x['w']>=43.9 and x['h']>=43.9 for x in m['controls']),m['controls'])
          if h>w:
            await record(tag+'/composition-no-overlap',m['title']['bottom']<=m['stage']['y']+1 and m['stage']['bottom']<=m['caption']['y']+1 and m['caption']['bottom']<=m['dock']['y']+1,m)
        await page.screenshot(path=str(OUT/f'{engine}-{name}.png'))
        if name=='phone':
          for chapter in [1,2,0]:
            await page.locator(f'[data-chapter="{chapter}"]').tap()
            await page.wait_for_timeout(700)
            state=await page.evaluate('({chapter:__NOCTURNE__.state.chapter,morph:__NOCTURNE__.state.morph})')
            await record(tag+f'/chapter-{chapter+1}',state['chapter']==chapter and abs(state['morph']-chapter)<.02,state)
            if chapter==2:await page.screenshot(path=str(OUT/f'{engine}-third.png'))
          await page.locator('#pauseBtn').tap()
          await record(tag+'/play-toggle',not await page.evaluate('__NOCTURNE__.state.paused'))
          await page.locator('#pauseBtn').tap()
          await page.locator('#notesBtn').tap()
          await record(tag+'/notes-open',await page.locator('#notesDialog').is_visible())
          await page.screenshot(path=str(OUT/f'{engine}-notes.png'))
          await page.locator('#notesDialog').evaluate('(e)=>e.scrollTop=e.scrollHeight')
          await page.locator('#closeNotes').evaluate('(e)=>e.click()')
          await record(tag+'/notes-close',not await page.locator('#notesDialog').is_visible())
          await page.locator('#focusBtn').tap();await page.wait_for_timeout(300)
          await record(tag+'/focus-mode',await page.evaluate('__NOCTURNE__.state.focused'))
          await page.locator('#leaveFocus').tap();await page.wait_for_timeout(300)
          await record(tag+'/focus-exit',not await page.evaluate('__NOCTURNE__.state.focused'))
          await page.locator('#saveBtn').tap()
          await page.locator('#exportDialog').wait_for(state='visible',timeout=45000)
          dimensions=await page.locator('#exportImage').evaluate('(e)=>[e.naturalWidth,e.naturalHeight]')
          await record(tag+'/poster-export',dimensions==[1080,1440],dimensions)
          await page.screenshot(path=str(OUT/f'{engine}-export.png'))
          await page.locator('#closeExport').tap()
          # Safe area regression: emulate a device with top and bottom insets.
          await page.evaluate("document.documentElement.style.setProperty('--safe-top','47px');document.documentElement.style.setProperty('--safe-bottom','34px');window.dispatchEvent(new Event('resize'))")
          await page.wait_for_timeout(400);safe=await metrics(page)
          await record(tag+'/safe-areas',safe['dock']['bottom']<=h-34 and safe['stage']['bottom']<=safe['caption']['y']+1)
          await page.screenshot(path=str(OUT/f'{engine}-safe-area.png'))
          await page.evaluate("document.documentElement.style.removeProperty('--safe-top');document.documentElement.style.removeProperty('--safe-bottom')")
          for rw,rh in [(390,640),(844,390),(390,844)]:
            await page.set_viewport_size({'width':rw,'height':rh});await page.wait_for_timeout(450)
            size=await page.evaluate('({w:__NOCTURNE__.state.width,h:__NOCTURNE__.state.height,rect:document.querySelector("#renderHost").getBoundingClientRect().toJSON()})')
            await record(tag+f'/resize-{rw}x{rh}',abs(size['w']-size['rect']['width'])<1 and abs(size['h']-size['rect']['height'])<1,size)
          # Pointer lifecycle, including browser gesture cancellation.
          r=await page.locator('#renderHost').bounding_box();x=r['x']+r['width']/2;y=r['y']+r['height']/2
          await page.locator('#renderHost').dispatch_event('pointerdown',{'pointerId':8,'pointerType':'touch','isPrimary':True,'clientX':x,'clientY':y,'button':0})
          await page.wait_for_timeout(450)
          await record(tag+'/hold-start',await page.evaluate('__NOCTURNE__.state.holdTarget==1'))
          await page.dispatch_event('body','pointercancel',{'pointerId':8,'pointerType':'touch','isPrimary':True})
          await record(tag+'/hold-cancel',await page.evaluate('__NOCTURNE__.state.holdTarget==0 && !__NOCTURNE__.state.dragging'))
          if engine=='chromium':
            cdp=await context.new_cdp_session(page)
            await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
            await cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x+55,'y':y+2}]})
            await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            await record(tag+'/real-horizontal-touch',await page.evaluate('Math.abs(__NOCTURNE__.state.targetRotation[0])>.1'))
            await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y+65}]})
            for delta in [20,40,60,80,100,120]:
              await cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y+65-delta}]})
              await page.wait_for_timeout(35)
            await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            await page.wait_for_timeout(250)
            await record(tag+'/real-vertical-scroll',await page.evaluate('scrollY>20'),await page.evaluate('scrollY'))
        await record(tag+'/no-js-errors',not errors,errors)
        await context.close()
      # A working native fallback remains available without external modules.
      if engine=='chromium':
        context=await browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,reduced_motion='reduce')
        page,errors=await open_page(context,True);m=await metrics(page)
        await record('native-fallback',m['visible']>100 and m['backend'].startswith('WebGL') and not errors,m['backend'])
        await context.close()
      await browser.close()

if __name__=='__main__':
  try:asyncio.run(main())
  finally:
    (OUT/'report.json').write_text(json.dumps({'checks':RESULTS,'passed':sum(x['pass'] for x in RESULTS),'failed':sum(not x['pass'] for x in RESULTS)},ensure_ascii=False,indent=2))
