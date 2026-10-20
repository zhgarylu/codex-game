"""Record an actual realtime browser playthrough; no game-state injection or clock mocks."""
import base64
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts'
RAW = OUT / 'recording-raw'
RAW.mkdir(exist_ok=True)
events = []
errors = []
started = time.monotonic()

def stamp(label, caption=None):
    elapsed = round(time.monotonic() - started, 3)
    events.append({'time':elapsed,'event':label,'caption':caption or label})
    print(json.dumps(events[-1],ensure_ascii=False),flush=True)

def wait(page, ms):
    page.wait_for_timeout(ms)

def hold(page, key, ms):
    if ms <= 0:
        return
    page.keyboard.down(key)
    wait(page, ms)
    page.keyboard.up(key)

def position(page):
    return page.locator('#player').evaluate("e=>({x:parseFloat(e.style.left)*6.4,y:parseFloat(e.style.top)*4.2})")

def go(page, x):
    pos = position(page)
    if pos['y'] > 153:
        hold(page,'ArrowUp',(pos['y']-150)/190*1000)
    pos = position(page)
    hold(page,'ArrowRight' if x>pos['x'] else 'ArrowLeft',abs(x-pos['x'])/190*1000)
    hold(page,'ArrowUp',65)
    wait(page,150)

def interact(page):
    page.keyboard.press('z')

def choose(page, index, delay=240):
    expect(page.locator('#station-menu')).to_be_visible()
    wait(page,delay)
    for _ in range(index):
        page.keyboard.press('ArrowDown')
        wait(page,200)
    wait(page,delay)
    page.keyboard.press('z')
    expect(page.locator('#station-menu')).to_be_hidden()

AUDIO_RECORDER = r"""
(() => {
  const NativeContext = window.AudioContext || window.webkitAudioContext;
  const connect = AudioNode.prototype.connect;
  const chunks = [];
  let recorder;
  window.AudioContext = class RecordedAudioContext extends NativeContext {
    constructor(...args) {
      super(...args);
      const destination = this.createMediaStreamDestination();
      this.__recordDestination = destination;
      recorder = new MediaRecorder(destination.stream, {mimeType:'audio/webm;codecs=opus', audioBitsPerSecond:96000});
      recorder.ondataavailable = event => { if(event.data.size) chunks.push(event.data); };
      window.__recordedAudioStartEpoch = Date.now()/1000;
      recorder.start(500);
    }
  };
  if(window.webkitAudioContext) window.webkitAudioContext = window.AudioContext;
  AudioNode.prototype.connect = function(destination, ...args) {
    if(destination === this.context.destination && this.context.__recordDestination) {
      connect.call(this,this.context.__recordDestination);
    }
    return connect.call(this,destination,...args);
  };
  window.__finishActualGameAudio = async () => {
    if(!recorder) return null;
    await new Promise(resolve => { recorder.onstop=resolve;recorder.stop(); });
    const bytes = new Uint8Array(await new Blob(chunks,{type:'audio/webm'}).arrayBuffer());
    let binary='';
    for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
    return {base64:btoa(binary),start_epoch:window.__recordedAudioStartEpoch,bytes:bytes.length};
  };
})();
"""

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
    context = browser.new_context(viewport={'width':1600,'height':1000},device_scale_factor=1,record_video_dir=str(RAW),record_video_size={'width':1600,'height':1000})
    context.add_init_script(AUDIO_RECORDER)
    video_start_epoch = time.time()
    started = time.monotonic()
    page = context.new_page()
    video = page.video
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:4173/',wait_until='networkidle')
    # Browser view scaling only, so the whole real game fits in the recording.
    page.evaluate("document.body.style.zoom='0.75'")
    stamp('进入游戏','真实浏览器试玩｜方向键移动，Z 互动，X 返回')
    wait(page,1400)
    page.locator('#sound').click()
    wait(page,400)
    stamp('展示四色角色','BLUE / GREEN / YELLOW / RED：选择喜欢的厨师颜色')
    for color in ['green','yellow','red','blue']:
        page.locator(f'[data-chef="{color}"]').click()
        wait(page,750)
    stamp('选择 BLUE 开始','本轮选择 BLUE，开始 90 秒拉面挑战')
    wait(page,700)
    page.locator('#start').click()
    wait(page,600)
    for bowl in range(1,7):
        recipe = page.locator('.order-ticket h2').inner_text()
        ingredients = page.locator('.order-ticket p b').all_text_contents()
        broth = ['豚骨白汤','赤味噌','醇香酱油'].index(ingredients[0])
        topping = ['溏心蛋','叉烧肉','香菇'].index(ingredients[1])
        stamp(f'第{bowl}碗：{recipe}',f'第 {bowl} 碗：{recipe}｜按左侧订单准备食材')
        if bowl == 1:
            wait(page,1200)
        go(page,566)
        if bowl == 1:
            stamp('冰箱取材','靠近 FRIDGE，面朝冰箱按 Z，选择对应汤底与拉面')
        interact(page)
        choose(page,broth,500 if bowl==1 else 180)
        go(page,100)
        if bowl == 1:
            stamp('煮汤菜单','到 COOK 按 Z，选择轻柔搅拌，开始煮汤和面')
        interact(page)
        choose(page,0,650 if bowl==1 else 180)
        if bowl == 1:
            stamp('实际火候控制','指针进入绿色区间，再按 Z 捞面；过久会煮糊')
        wait(page,1800)
        interact(page)
        expect(page.locator('#cook-label')).to_contain_text('完美火候')
        wait(page,300)
        go(page,262)
        if bowl == 1:
            stamp('切配','移动到 CHOP，选择订单所需配料，按 Z 确认')
        interact(page)
        choose(page,topping,500 if bowl==1 else 180)
        go(page,424)
        if bowl == 1:
            stamp('装碗出餐','到 BOWL 按 Z 出餐，配方正确和完美火候都有加分')
            wait(page,500)
        interact(page)
        if bowl<6:
            expect(page.locator('#served')).to_contain_text(str(bowl))
            wait(page,650)
        else:
            expect(page.locator('.result h1')).to_contain_text('温暖了六位客人')
    result = {'title':page.locator('.result h1').inner_text(),'score':page.locator('.result-score strong').inner_text(),'stars':page.locator('.star-rating').get_attribute('aria-label'),'details':page.locator('.result-details').inner_text()}
    stamp('五星结算','6 碗全部完成！本局 1125 分、5 星，随时可以重新开店')
    page.screenshot(path=str(OUT/'recorded-playthrough-result.png'),full_page=False)
    wait(page,5500)
    audio = page.evaluate('() => window.__finishActualGameAudio()')
    audio_path = RAW/'actual-game-audio.webm'
    if audio:
        audio_path.write_bytes(base64.b64decode(audio['base64']))
        audio_offset=max(0,audio['start_epoch']-video_start_epoch)
    else:
        audio_offset=None
    duration=time.monotonic()-started
    context.close()
    video.save_as(str(RAW/'actual-playthrough.webm'))
    browser.close()

metadata={'capture':'Playwright browser viewport recording of the actual realtime game','video':'recording-raw/actual-playthrough.webm','audio':'recording-raw/actual-game-audio.webm' if audio else None,'audio_offset_seconds':audio_offset,'viewport':[1600,1000],'view_zoom':0.75,'game_state_modified':False,'clock_mocked':False,'result':result,'duration_wall_seconds':duration,'browser_errors':errors,'events':events}
(OUT/'playthrough-recording.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
assert not errors, errors
assert result['score']=='1125' and result['stars']=='5星', result
print(json.dumps({'status':'recorded','duration':duration,'audio_bytes':audio['bytes'] if audio else 0,'audio_offset':audio_offset,'result':result},ensure_ascii=False),flush=True)
