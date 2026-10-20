"""Real UI tests: keyboard and touch movement, stations, cooking and results.
Uses the environment's existing Python Playwright + /usr/bin/chromium.
Start npm run dev, then npm run test:e2e.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts'
OUT.mkdir(exist_ok=True)
URL = os.environ.get('RAMEN_TEST_URL', 'http://127.0.0.1:4173')
checks, errors = [], []

def check(condition, message):
    assert condition, message
    checks.append(message)

def observe(page):
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.clock.install()

def start(page):
    page.locator('#start').click()
    expect(page.locator('.kitchen-stage')).to_be_visible()

def position(page):
    # Inspect rendered position only; never mutate game state for tests.
    return page.locator('#player').evaluate("e=>({x:parseFloat(e.style.left)*6.4,y:parseFloat(e.style.top)*4.2})")

def hold(page, direction, milliseconds, touch=False):
    if milliseconds <= 0:
        return
    if touch:
        button = page.locator(f'[data-dir="{direction}"]')
        button.scroll_into_view_if_needed()
        box = button.bounding_box()
        x, y = box['x'] + box['width']/2, box['y'] + box['height']/2
        # CDP emits real touch events, converted to pointerdown/up by Chromium.
        client = page.context.new_cdp_session(page)
        client.send('Input.dispatchTouchEvent', {'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
        page.clock.run_for(int(milliseconds))
        client.send('Input.dispatchTouchEvent', {'type':'touchEnd','touchPoints':[]})
        client.detach()
    else:
        key = {'up':'ArrowUp','down':'ArrowDown','left':'ArrowLeft','right':'ArrowRight'}[direction]
        page.keyboard.down(key)
        page.clock.run_for(int(milliseconds))
        page.keyboard.up(key)

def go(page, x, touch=False):
    pos = position(page)
    if pos['y'] > 153:
        hold(page, 'up', (pos['y']-150)/190*1000, touch)
    pos = position(page)
    hold(page, 'right' if x > pos['x'] else 'left', abs(x-pos['x'])/190*1000, touch)
    # Face the station, as in the demonstrated interface.
    hold(page, 'up', 45, touch)

def interact(page, touch=False):
    if touch:
        page.locator('#interact').tap()
    else:
        page.keyboard.press('z')

def choose(page, index, touch=False):
    expect(page.locator('#station-menu')).to_be_visible()
    if touch:
        page.locator(f'[data-choice="{index}"]').tap()
    else:
        # The menu always opens at zero for a fresh bowl.
        for _ in range(index):
            page.keyboard.press('ArrowDown')
        page.keyboard.press('z')
    expect(page.locator('#station-menu')).to_be_hidden()

def recipe(page):
    vals = page.locator('.order-ticket p b').all_text_contents()
    return ['豚骨白汤','赤味噌','醇香酱油'].index(vals[0]), ['溏心蛋','叉烧肉','香菇'].index(vals[1])

def serve(page, touch=False, wrong=False):
    broth, topping = recipe(page)
    if wrong:
        broth = (broth+1)%3
    go(page, 566, touch)
    interact(page, touch)
    choose(page, broth, touch)
    go(page, 100, touch)
    interact(page, touch)
    check('STIR WITH LOVE' in page.locator('#station-menu').inner_text(), 'COOK opens the broth stirring menu')
    choose(page, 0, touch)
    page.clock.run_for(1800)
    interact(page, touch)
    check('完美火候' in page.locator('#cook-label').inner_text(), 'A at COOK stops cooking in the perfect window')
    go(page, 262, touch)
    interact(page, touch)
    choose(page, topping, touch)
    go(page, 424, touch)
    interact(page, touch)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    desktop = browser.new_context(viewport={'width':1440,'height':1100}, device_scale_factor=1)
    page = desktop.new_page()
    observe(page)
    response = page.goto(URL)
    check(response.status == 200, 'HTTP preview returns 200')
    check(page.locator('[data-chef]').count() == 4, 'BLUE GREEN YELLOW RED characters are available')
    page.screenshot(path=str(OUT/'01-character-select-desktop.png'), full_page=True)
    page.locator('[data-chef="green"]').click()
    page.keyboard.press('ArrowRight')
    check(page.locator('[data-chef="yellow"]').get_attribute('aria-checked') == 'true', 'Click and arrow keys select chef color')
    start(page)
    check('YELLOW' in page.locator('.chef-on-duty').inner_text(), 'Selected color carries into kitchen')
    page.screenshot(path=str(OUT/'02-game-desktop.png'), full_page=True)
    interact(page)
    check('靠近' in page.locator('#toast').inner_text(), 'Stations require proximity')
    before = position(page)
    hold(page, 'up', 1000)
    check(position(page)['y'] < before['y'], 'Arrow keys move the rendered player')
    hold(page, 'up', 1000)
    check(position(page)['y'] >= 139, 'Worktop collision prevents walking through stations')
    go(page, 424)
    interact(page)
    check('还没做好' in page.locator('#toast').inner_text(), 'Incomplete BOWL serving gives useful feedback')
    check(page.locator('#hearts').get_attribute('aria-label') == '剩余3次机会', 'Incomplete bowls do not lose a heart')
    page.keyboard.press('Enter')
    time = page.locator('#time').inner_text()
    page.clock.run_for(5000)
    check(page.locator('#time').inner_text() == time, 'Start pause freezes time')
    page.locator('#resume').click()
    page.locator('#help').click()
    page.clock.run_for(5000)
    check(page.locator('#time').inner_text() == time, 'Help pauses time')
    page.locator('.close-help').click()
    check(page.locator('#pause-overlay').is_hidden(), 'Closing help resumes gameplay')
    go(page, 566)
    interact(page)
    page.keyboard.press('x')
    check(page.locator('#station-menu').is_hidden(), 'X cancels station menu')
    page.locator('#sound').click()
    check(page.locator('#sound').get_attribute('aria-pressed') == 'true', 'Sound can be enabled')
    for _ in range(6):
        serve(page)
    check('温暖了六位客人' in page.locator('.result h1').inner_text(), 'Six keyboard-crafted bowls win the game')
    check(page.locator('.result-details strong').first.inner_text() == '6 / 6', 'Victory counts six bowls')
    check(page.locator('.star-rating').get_attribute('aria-label') == '5星', 'Perfect cooking gives five stars')
    check(int(page.locator('.result-score strong').inner_text()) == 1125, 'Perfect six-bowl score and combo match rules')
    check(int(page.evaluate('localStorage.getItem("ramen-best")')) == 1125, 'Best score persists locally')
    page.screenshot(path=str(OUT/'03-victory-desktop.png'), full_page=True)
    page.locator('#restart').click()
    check(page.locator('#score').inner_text() == '0', 'Restart resets score')
    check(page.locator('#served').inner_text().startswith('0'), 'Restart resets bowls')
    for _ in range(3):
        serve(page, wrong=True)
    check('小店打烊' in page.locator('.result h1').inner_text(), 'Three wrong bowls show loss result')
    page.screenshot(path=str(OUT/'06-loss-desktop.png'), full_page=True)
    page.locator('#restart').click()
    page.clock.run_for(73000)
    check('小店打烊' in page.locator('.result h1').inner_text(), 'Three unattended customers end the shift')
    page.locator('#reselect').click()
    check(page.locator('[data-chef="yellow"]').get_attribute('aria-checked') == 'true', 'Result returns to selection and retains color')
    for width in [320,375,390,768,1024]:
        page.set_viewport_size({'width':width,'height':1000})
        check(page.evaluate('document.documentElement.scrollWidth') == width, f'Selection fits {width}px viewport')
        start(page)
        check(page.evaluate('document.documentElement.scrollWidth') == width, f'Kitchen fits {width}px viewport')
        page.locator('#pause').click()
        page.locator('#quit').click()
    desktop.close()

    mobile = browser.new_context(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True, device_scale_factor=1)
    mp = mobile.new_page()
    observe(mp)
    mp.goto(URL)
    mp.screenshot(path=str(OUT/'04-character-select-mobile.png'), full_page=True)
    mp.locator('[data-chef="red"]').tap()
    mp.locator('#start').tap()
    mp.screenshot(path=str(OUT/'05-game-mobile.png'), full_page=True)
    for _ in range(6):
        serve(mp, touch=True)
    check('温暖了六位客人' in mp.locator('.result h1').inner_text(), 'Real touch D-pad and station buttons can complete six bowls')
    check(mp.locator('.star-rating').get_attribute('aria-label') == '5星', 'Touch play earns five stars')
    mp.screenshot(path=str(OUT/'07-victory-mobile.png'), full_page=True)
    mp.locator('#restart').tap()
    mp.locator('#pause').tap()
    check(mp.locator('#pause-overlay').is_visible(), 'Touch pause works')
    mp.locator('#quit').tap()
    check(mp.locator('.chef-grid').is_visible(), 'Touch quit returns to selection')
    mobile.close()

    # Environment Chromium policy blocks file:// navigation. Execute the actual
    # standalone HTML contents offline, verifying it needs no server or assets.
    offline = browser.new_context(viewport={'width':1280,'height':1000}, offline=True)
    op = offline.new_page()
    observe(op)
    requests = []
    op.on('request', lambda r: requests.append(r.url) if r.url.startswith('http') else None)
    op.set_content((ROOT/'dist'/'index.html').read_text(), wait_until='load')
    start(op)
    serve(op)
    check(op.locator('#served').inner_text().startswith('1'), 'Production single HTML contents are playable offline')
    check(not requests, 'Production game makes no HTTP requests')
    offline.close()
    check(not errors, f'No browser JavaScript or console errors: {errors}')
    browser.close()

report={'status':'passed','count':len(checks),'checks':checks,'console_errors':errors,'browser':'Chromium / Playwright','url':URL,'file_navigation':'Blocked by environment Chromium policy; standalone HTML contents tested offline instead.'}
(OUT/'browser-test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
