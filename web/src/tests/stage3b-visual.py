"""Visual-only fixtures; no backend mutation or real model call."""
import asyncio
import json
import sys
from urllib.parse import urlparse
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(__file__).resolve().parents[2] / 'test-results' / 'inkline-stage3b'

async def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else 'after'
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'kind': 'VISUAL FIXTURE', 'screenshots': [], 'errors': [], 'checks': []}
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        page = await browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        async def diff_fixture(route):
            path = urlparse(route.request.url).path
            change = {'path': 'notes/config.md', 'status': 'modified', 'additions': 2, 'deletions': 1, 'diff': '--- a/notes/config.md\n+++ b/notes/config.md\n@@ -1,2 +1,3 @@\n # 配置\n-旧说明\n+工作区：Personal\n+模型：Qwen 3.5', 'diff_truncated': False}
            if path.endswith('/changes/diff'):
                await route.fulfill(json=change)
            elif path.endswith('/changes'):
                await route.fulfill(json={'git': True, 'truncated': False, 'changes': [change]})
            else:
                await route.continue_()
        await page.route('**/api/v1/**', diff_fixture)
        await page.goto('http://127.0.0.1:5173/chat')
        await page.locator('.composer textarea').wait_for()
        await page.wait_for_timeout(1000)
        async def shot(name):
            # Capture the settled panel, not an intermediate opacity frame.
            await page.wait_for_timeout(350)
            await page.screenshot(path=str(OUT / (name + '.png')))
            report['screenshots'].append(name + '.png')
        async def reset(scene, theme='light'):
            await page.evaluate("async ([scene, theme]) => { const m = await import('/src/tests/stage3b-fixture.ts'); await m.install(scene, theme) }", [scene, theme])
            await page.wait_for_timeout(300)
        def check(name, passed):
            report['checks'].append({'name': name, 'pass': bool(passed)})
        for theme in ['light', 'dark']:
            for width in [1440, 1100, 719]:
                await page.set_viewport_size({'width': width, 'height': 1000})
                await page.evaluate("async (theme) => { const m = await import('/src/tests/stage3b-fixture.ts'); await m.install('process', theme) }", theme)
                await page.locator('.process').first.evaluate('(el) => { el.open = true }')
                await page.locator('.message-list').evaluate('(el) => { el.scrollTop = 0 }')
                await page.wait_for_timeout(650)
                name = f'{phase}-{theme}-{width}.png'
                await page.screenshot(path=str(OUT / name))
                report['screenshots'].append(name)
                check(f'no horizontal overflow {width}/{theme}', await page.evaluate('() => document.documentElement.scrollWidth <= window.innerWidth'))
        if phase == 'after':
            await page.set_viewport_size({'width': 1440, 'height': 1000})
            for theme in ['light', 'dark']:
                await reset('pure', theme)
                check('pure chat is compact ' + theme, await page.locator('.receipt.compact').count() == 1 and await page.locator('.receipt-facts').count() == 0)
                await shot('pure-chat-' + theme)
                await reset('process', theme)
                await page.locator('.receipt').scroll_into_view_if_needed()
                await shot('receipt-code-' + theme)
                check('body 15px and 1.7 ' + theme, await page.locator('.markdown-content').evaluate('(el) => { const s = getComputedStyle(el); return s.fontSize === "15px" && s.lineHeight === "25.5px" }'))
                check('end button has no default border ' + theme, await page.locator('.end-glyph').evaluate('(el) => getComputedStyle(el).borderTopWidth === "0px"'))
                await reset('failure', theme)
                await page.locator('.rail-node.failed').first.scroll_into_view_if_needed()
                check('failure automatically expanded ' + theme, await page.locator('.rail-node.failed .node-button').first.get_attribute('aria-expanded') == 'true')
                await shot('failure-unused-input-' + theme)
                for scene in ['running', 'waiting', 'queued']:
                    await reset(scene, theme)
                    await page.locator('.message-list').evaluate('(el) => { el.scrollTop = el.scrollHeight }')
                    await shot('composer-' + scene + '-' + theme)
                    selector = '.is-waiting' if scene == 'waiting' else '.has-queue' if scene == 'queued' else '.is-running'
                    check('composer state ' + scene + '/' + theme, await page.locator('.composer-wrap' + selector).count() == 1)
            await reset('long')
            for details in await page.locator('.process').all():
                await details.evaluate('(el) => { el.open = true }')
            await page.locator('[data-rail-node="visual-task:command"]').click()
            await page.locator('.rail-node#rail-visual-task-command .code-footer button').click()
            check('terminal capped at 200 rendered lines', await page.locator('#rail-visual-task-command .terminal .code-line').count() == 200)
            await page.locator('#rail-visual-task-command').scroll_into_view_if_needed()
            await shot('long-process-terminal')
            check('minimap based on physical density', await page.locator('.rail-minimap button').count() > 1)
            await page.locator('.rail-minimap button').last.click()
            await page.wait_for_timeout(200)
            check('minimap jump focuses node', await page.evaluate('() => Boolean(document.activeElement?.hasAttribute("data-rail-node"))'))
            await reset('menus')
            draft = page.locator('.composer textarea')
            await draft.fill('/')
            await draft.press('ArrowDown')
            check('slash active descendant exists', await draft.evaluate('(el) => Boolean(document.getElementById(el.getAttribute("aria-activedescendant")))'))
            await shot('slash-keyboard')
            await draft.press('Escape')
            check('Esc closes menu without cancelling', await page.locator('.slash-menu').count() == 0)
            await draft.fill('')
            await page.locator('.model-trigger').click()
            await page.locator('.model-search input').press('End')
            check('model End highlights final model', await page.locator('.model-option[data-highlighted="true"]').inner_text() == 'DeepSeek')
            await shot('model-keyboard')
            await page.locator('.model-search input').press('Escape')
            check('model dialog returns focus', await page.evaluate('() => document.activeElement?.classList.contains("model-trigger")'))
            await draft.fill('@')
            await page.wait_for_timeout(600)
            await shot('mention-keyboard')
            await draft.press('Escape')
            await draft.fill('')
            for theme in ['light', 'dark']:
                await reset('process', theme)
                await page.locator('.receipt').scroll_into_view_if_needed()
                await page.locator('.changes-link').click()
                await page.locator('.diff-preview .code-block').wait_for()
                check('diff has actual before/after gutters ' + theme, await page.locator('.diff-preview code.addition').count() == 2 and await page.locator('.diff-preview code.deletion').count() == 1)
                await shot('diff-drawer-' + theme)
                await page.locator('.drawer-toggle').click()
            await reset('process')
            await page.locator('.receipt').scroll_into_view_if_needed()
            await page.evaluate('() => Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async (text) => { window.__visualCopied = text } } })')
            await page.locator('.answer .copy-button').click()
            check('copy has explicit visual feedback', await page.locator('.answer [role="status"]').inner_text() == '已复制')
            await shot('code-copy-feedback')
            await page.emulate_media(reduced_motion='reduce')
            await reset('waiting', 'dark')
            await shot('reduced-motion-waiting')
            check('reduced motion has no recurring rail animation', await page.locator('.rail-glyph.waiting').evaluate('(el) => getComputedStyle(el).animationIterationCount === "1"'))
        (OUT / f'{phase}-visual.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        await browser.close()

asyncio.run(main())
