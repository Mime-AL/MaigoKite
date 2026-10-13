"""Read-only, real-backend acceptance of plan recovery and drawer projections."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "test-results" / "inkline-stage3a"
BASE = "http://127.0.0.1:5173"
API = BASE + "/api/v1/workspaces/personal"

async def main():
    report = {"backend": "REAL", "checks": [], "screenshots": [], "errors": []}
    initial = json.loads((OUT / "live-results.json").read_text())
    short = json.loads((OUT / "short-live-results.json").read_text())
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        context = await browser.new_context(viewport={"width": 1440, "height": 1000})
        page = await context.new_page()
        page.on("pageerror", lambda error: report["errors"].append(str(error)))
        async def screenshot(name):
            await page.screenshot(path=str(OUT / (name + ".png")))
            report["screenshots"].append(name + ".png")
        def check(name, ok):
            report["checks"].append({"name": name, "pass": bool(ok)})
            print(json.dumps(report["checks"][-1]), flush=True)
        async def drawer(tab):
            if not await page.locator("#work-drawer").is_visible():
                await page.locator(".drawer-toggle").click()
            await page.get_by_role("tab", name=tab, exact=True).click()
        try:
            conv = initial["conversations"][0]
            snapshot = await (await context.request.get(API + f"/conversations/{conv}/snapshot")).json()
            task = snapshot["tasks"][-1]
            inspection = await (await context.request.get(API + f"/tasks/{task['id']}/inspection")).json()
            expected = inspection["projection"]["plan"]
            await page.goto(BASE + "/chat/" + conv)
            await page.locator(".composer textarea").wait_for()
            await drawer("计划")
            await page.locator(".plan-tab li").first.wait_for()
            plan_text = await page.locator(".plan-tab").inner_text()
            check("real plan matches inspection", await page.locator(".plan-tab li").count() == len(expected) and all(item["content"] in plan_text for item in expected))
            await screenshot("10-plan-restored-light")
            await page.reload()
            await page.locator(".composer textarea").wait_for()
            await drawer("计划")
            await page.locator(".plan-tab li").first.wait_for()
            check("plan survives browser refresh", await page.locator(".plan-tab li").count() == len(expected))
            await page.get_by_role("button", name="切换到松烟", exact=True).click()
            await screenshot("11-plan-restored-dark")
            await drawer("运行")
            await page.locator(".jobs-tab details").first.wait_for(timeout=20000)
            check("history collapsed", await page.locator(".jobs-tab details").count() > 0 and await page.locator(".jobs-tab details[open]").count() == 0)
            await screenshot("12-runtime-history-dark")
            await page.goto(BASE + "/chat/" + short["conversations"][0])
            await page.locator(".composer textarea").wait_for()
            await drawer("计划")
            await page.locator(".plan-empty").wait_for()
            check("real plan empty state", await page.locator(".plan-tab li").count() == 0)
            await screenshot("13-plan-empty-dark")
            # Responsive smoke only: no state injection or fabricated task activity.
            for width in [1100, 719]:
                await page.set_viewport_size({"width": width, "height": 1000})
                await page.wait_for_timeout(300)
                check(f"drawer usable at {width}", await page.get_by_role("tab", name="运行", exact=True).is_visible())
                await screenshot(f"14-plan-empty-{width}-dark")
        except Exception as error:
            report["errors"].append(str(error))
            print("DETAIL BLOCKED: " + str(error), flush=True)
        finally:
            (OUT / "details-live-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
            await browser.close()

asyncio.run(main())
