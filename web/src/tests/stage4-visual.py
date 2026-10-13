"""Real frontend / isolated HTTP fixtures. No live provider or backend mutation."""
import asyncio
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright

OUT = Path(__file__).resolve().parents[2] / 'test-results' / 'inkline-stage4'
MEMORIES = [
    {'id': 'persona', 'category': 'fact', 'content': '人设：语气自然、直接；拿不准的地方坦诚说明。', 'confidence': 1},
    {'id': 'preference', 'category': 'preference', 'content': '讨论旅行时，把预算与步行距离放在一起比较。', 'confidence': .92},
    {'id': 'constraint', 'category': 'constraint', 'content': '不喜欢过早出发，上午十点以后安排活动。', 'confidence': .8},
    {'id': 'memory', 'category': 'project', 'content': '十一月的京都旅行，想留一个下午逛书店。', 'confidence': .86},
]
for item in MEMORIES:
    item.update(workspace_id='personal', subject_user_id='local', source_type='user', source_id='local', created_at='2026-10-10T05:00:00Z', updated_at='2026-10-11T05:00:00Z')

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'kind': 'PRESENTATION FIXTURE, NOT LIVE BACKEND E2E', 'screenshots': [], 'checks': [], 'errors': [], 'contrast': {}}
    state = {'scene': 'chat', 'writes': []}
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        context = await browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = await context.new_page()
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        async def fixture(route):
            path = urlparse(route.request.url).path
            body = {}
            if path.endswith('/memories'):
                if state['scene'] == 'memory-error':
                    await route.fulfill(status=503, json={'error': {'message': '记忆暂时无法读取，请稍后重试。'}}); return
                body = {'memories': [] if state['scene'] == 'memory-empty' else MEMORIES}
                if state['scene'] == 'memory-loading': await asyncio.sleep(.7)
            elif path.endswith('/folders'): body = {'folders': [] if 'no-workspace' in state['scene'] else [{'id': '', 'name': 'MaigoKite', 'root_path': '/workspace/MaigoKite'}]}
            elif path.endswith('/conversations'): body = {'conversations': []}
            elif path.endswith('/approvals'): body = {'approvals': []}
            elif path.endswith('/questions'): body = {'questions': []}
            elif path.endswith('/models'): body = {'models': [], 'default_model_id': ''}
            elif path.endswith('/preferences'): body = {'assistant_name': 'sakiko'}
            elif path.endswith('/credentials'): body = {'credentials': []}
            if route.request.method != 'GET': state['writes'].append({'method': route.request.method, 'path': path})
            await route.fulfill(json=body)
        await page.route('**/api/v1/**', fixture)
        await page.goto('http://127.0.0.1:5173/chat')
        await page.locator('.composer textarea').wait_for()
        async def reset(scene='chat', theme='light'):
            state['scene'] = scene
            if page.url.endswith('/memory') or '/memory?' in page.url:
                await page.evaluate("async () => { const m=await import('/src/tests/stage4-fixture.ts'); await m.navigate('/chat') }")
            await page.evaluate("async args => { const m = await import('/src/tests/stage4-fixture.ts'); await m.install(...args) }", [scene, theme])
            await page.wait_for_timeout(650)
        async def shot(name):
            await page.screenshot(path=str(OUT / (name + '.png')))
            report['screenshots'].append(name + '.png')
        def check(name, passed): report['checks'].append({'name': name, 'pass': bool(passed)})
        for theme in ['light', 'dark']:
            for width in [1440, 1100, 719]:
                await page.set_viewport_size({'width': width, 'height': 1000})
                for scene in ['chat', 'records', 'records-empty', 'memory', 'memory-empty', 'memory-error']:
                    await reset(scene, theme)
                    await shot(f'{scene}-{theme}-{width}')
                    check(f'no horizontal overflow {scene}/{theme}/{width}', await page.evaluate('() => document.documentElement.scrollWidth <= innerWidth'))
                    if scene == 'records-empty': check('empty records route to chat ' + theme + '/' + str(width), page.url.endswith('/chat'))
        await page.set_viewport_size({'width': 1440, 'height': 1000})
        await reset('chat')
        draft = page.locator('.composer textarea')
        original_quote = await page.locator('.workpaper-epigraph p').inner_text()
        for key in ['1', '2', '3', '4']:
            await draft.fill('')
            await page.locator('.workpaper-signature a').focus()
            await page.keyboard.press(key)
            check('starter ' + key + ' prefills and focuses, without sending', bool(await draft.input_value()) and await draft.evaluate('(el) => el === document.activeElement'))
            await shot('starter-key-' + key)
        await draft.fill('typing 1234')
        await draft.press('1')
        check('numbers in composer stay text', await draft.input_value() == 'typing 12341')
        check('quote stable while typing', original_quote == await page.locator('.workpaper-epigraph p').inner_text())
        await draft.fill('')
        await reset('chat-no-workspace')
        check('only workspace-dependent starters disabled', await page.locator('.workpaper-starters button').evaluate_all('(els) => els.map(el => el.disabled)') == [True, False, True, False])
        await shot('chat-no-workspace')
        await reset('memory')
        await page.evaluate("async () => { const m=await import('/src/tests/stage4-fixture.ts'); await m.navigate('/memory?focus=memory') }")
        await page.wait_for_timeout(300); await shot('memory-focus')
        report['focus_debug'] = await page.evaluate('() => ({url:location.href,active:document.activeElement?.outerHTML,classes:document.getElementById("memory-memory")?.className})')
        check('focus query locates memory', await page.evaluate('() => document.activeElement?.id === "memory-memory"'))
        await page.locator('#memory-memory footer button').nth(1).click()
        await shot('memory-inline-edit')
        check('editor stays within entry', await page.locator('#memory-memory .memory-editor').count() == 1)
        await reset('memory-loading')
        # Capture while an actual deferred fixture response is loading.
        await page.evaluate("async () => { const {default:p}=await import('/src/stores/index.ts'); const {useMemoryStore}=await import('/src/stores/memory.ts'); void useMemoryStore(p).load() }")
        await page.wait_for_timeout(80); await shot('memory-loading')
        await page.wait_for_timeout(750)
        for theme in ['light', 'dark']:
            await reset('chat', theme)
            for period in ['morning', 'noon', 'evening', 'night']:
                await page.locator('.workpaper').evaluate('(el, period) => el.dataset.light = period', period)
                report['contrast'][theme + '/' + period] = await page.evaluate(r"""() => {
                  const paper = document.querySelector('.workpaper'), styles = getComputedStyle(paper);
                  function rgb(s) { const numbers = s.match(/[\d.]+/g).slice(0,3).map(Number); return s.startsWith('color(srgb') ? numbers : numbers.map(x=>x/255) }
                  function lum(s) { return rgb(s).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((v,x,i)=>v+x*[.2126,.7152,.0722][i],0) }
                  const bg=lum(styles.backgroundColor);
                  function contrast(sel) { const fg=lum(getComputedStyle(document.querySelector(sel)).color); return Number(((Math.max(bg,fg)+.05)/(Math.min(bg,fg)+.05)).toFixed(2)) }
                  return { surface:styles.backgroundColor, body:contrast('.workpaper-hero h1'), secondary:contrast('.workpaper-epigraph'), metadata:contrast('.workpaper-epigraph small') }
                }""")
                await shot('light-' + theme + '-' + period)
        await page.emulate_media(reduced_motion='reduce')
        await reset('chat', 'dark'); await shot('chat-reduced-motion')
        check('reduced motion is short fade', await page.locator('.workpaper').evaluate('(el) => getComputedStyle(el).animationName === "paper-fade"'))
        await page.emulate_media(reduced_motion='no-preference')
        for theme in ['light', 'dark']:
            await page.set_viewport_size({'width': 719, 'height': 1000})
            await reset('memory', theme)
            await page.locator('.main-content').evaluate('(el) => el.scrollTop = el.scrollHeight')
            await shot('memory-lower-' + theme + '-719')
        await page.set_viewport_size({'width': 1440, 'height': 1000})
        await reset('memory-error')
        state['scene'] = 'memory'
        await page.locator('.memory-error button').click()
        await page.locator('.memory-item').first.wait_for()
        check('memory error retries through existing API', await page.locator('.memory-error').count() == 0)
        await shot('memory-retry-success')
        await reset('chat')
        await draft.fill('已有草稿')
        await page.locator('.workpaper-starters button').nth(1).click()
        check('starter appends without discarding existing draft', (await draft.input_value()).startswith('已有草稿\n\n'))
        await shot('starter-existing-draft')
        await draft.fill(''); await draft.evaluate('(el) => el.blur()')
        await page.evaluate("async () => { const m=await import('/src/tests/stage4-fixture.ts'); await m.navigate('/chat/new-fixture') }")
        check('subsequent empty chat does not replay full introduction', await page.locator('.workpaper.first-welcome').count() == 0)
        await reset('chat')
        quote = await page.locator('.workpaper-epigraph p').inner_text()
        await page.evaluate("async () => { const {default:p}=await import('/src/stores/index.ts'); const {useUIStore}=await import('/src/stores/ui.ts'); useUIStore(p).setAppearance({theme:'dark'}) }")
        check('theme switch keeps the same welcome quote', quote == await page.locator('.workpaper-epigraph p').inner_text())
        await page.evaluate("async () => { const {default:p}=await import('/src/stores/index.ts'); const {useUIStore}=await import('/src/stores/ui.ts'); useUIStore(p).setAppearance({language:'en',theme:'light'}) }")
        await page.wait_for_timeout(200); await shot('chat-english')
        check('English starter copy available', 'Read the workspace' in await page.locator('.workpaper-starters').inner_text())
        await page.evaluate("async () => { const {default:p}=await import('/src/stores/index.ts'); const {useUIStore}=await import('/src/stores/ui.ts'); useUIStore(p).setAppearance({language:'zh-CN'}) }")
        await reset('chat')
        # Sample the actual production keyframes at deterministic timeline positions.
        await page.evaluate('() => document.activeElement?.blur()')
        for moment in [0, 120, 240, 480, 600]:
            await page.evaluate("ms => { const p=document.querySelector('.workpaper'); p.classList.add('first-welcome'); for(const a of p.getAnimations({subtree:true})){a.pause(); a.currentTime=ms} }", moment)
            await shot('intro-frame-' + str(moment))
        report['fixture_http_writes'] = state['writes']
        (OUT / 'visual-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        await browser.close()

asyncio.run(main())
