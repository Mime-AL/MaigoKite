"""Local, ignored acceptance runner. Uses the real Gateway/Core and configured model."""
import asyncio
import json
import time
import sys
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "test-results" / "inkline-stage3a"
BASE = "http://127.0.0.1:5173"
API = BASE + "/api/v1/workspaces/personal"

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"backend": "REAL", "provider": "UNVERIFIED", "checks": [], "screenshots": [], "errors": []}
    remaining = "--remaining" in sys.argv
    short = "--short" in sys.argv
    created = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        context = await browser.new_context(viewport={"width": 1440, "height": 1000})
        page = await context.new_page()
        page.on("pageerror", lambda error: result["errors"].append(str(error)))
        async def api(method, path, data=None, key=None):
            response = await context.request.fetch(API + path, method=method, data=data,
                headers={"Idempotency-Key": key} if key else None)
            body = await response.json() if response.status != 204 else None
            if response.status >= 400:
                raise RuntimeError(f"{method} {path}: {response.status} {body}")
            return body
        async def screenshot(name):
            await page.screenshot(path=str(OUT / (name + ".png")), full_page=False)
            result["screenshots"].append(name + ".png")
        async def check(name, ok, detail=""):
            result["checks"].append({"name": name, "pass": bool(ok), "detail": detail})
            print(json.dumps(result["checks"][-1], ensure_ascii=False), flush=True)
        async def new_chat(title):
            conv = await api("POST", "/conversations", {"title": title, "permission_mode": "read_only"})
            created.append(conv["id"])
            await page.goto(BASE + "/chat/" + conv["id"])
            await page.locator(".composer textarea").wait_for()
            await page.wait_for_function("() => document.querySelector('.composer textarea') && !document.querySelector('.composer textarea').disabled")
            return conv["id"]
        async def task_of(conv):
            snapshot = await api("GET", f"/conversations/{conv}/snapshot")
            return snapshot["tasks"][-1] if snapshot.get("tasks") else None
        async def wait_task(conv, statuses, timeout=100):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                task = await task_of(conv)
                if task and task["status"] in statuses:
                    return task
                await asyncio.sleep(.3)
            raise RuntimeError("Task status timeout")
        try:
            models = await api("GET", "/models")
            result["provider"] = next((m["model"] for m in models["models"] if m.get("is_default")), "UNKNOWN")
            if not remaining:
                conv = await new_chat("3a · 引导与待发验收")
                textarea = page.locator(".composer textarea")
                prompt = "这是一次只读验收，不修改文件。请使用 write_todos 列出三步计划，再逐个使用 file_read 读取 README.md、docs/design/API.md 和 docs/design/AgentRuntime.md，每次读取后概括，再读取下一个。最后简短总结。不调用命令、浏览器或子 Agent。"
                if short:
                    prompt = "只读验收：只使用 file_read 一次读取 README.md，简短概括然后结束，不调用其他工具，不修改文件。"
                await textarea.fill(prompt)
                await textarea.press("Enter")
                task = await wait_task(conv, {"running"})
                await page.get_by_role("button", name="引导当前任务", exact=True).wait_for()
                await textarea.fill("补充：只读 README.md 即可，跳过其他文件。结尾加上：引导已收到。")
                await textarea.press("Enter")
                await page.locator(".supplement-message").wait_for(timeout=20000)
                await check("guide accepted", "等待纳入" in await page.locator(".supplement-message").inner_text())
                await screenshot("01-guide-queued")
                await textarea.fill("验收待发消息")
                await textarea.press("Alt+Enter")
                queue = page.locator('section[aria-label="稍后发送"]')
                await queue.wait_for()
                await queue.get_by_role("button", name="编辑", exact=True).click()
                await queue.get_by_role("textbox", name="编辑待发消息").fill("编辑后的待发消息")
                await queue.get_by_role("button", name="保存", exact=True).click()
                await check("later queue edited", "编辑后的待发消息" in await queue.inner_text())
                await screenshot("02-later-edited")
                await queue.get_by_role("button", name="移除", exact=True).click()
                await check("later queue removed", await queue.count() == 0)
                await screenshot("03-later-removed")
                terminal = await wait_task(conv, {"succeeded", "failed", "cancelled", "timed_out", "interrupted"}, 150)
                result["guide_task"] = {"status": terminal["status"], "last_error": terminal.get("last_error")}
                inputs = (await api("GET", f"/tasks/{task['id']}/inputs"))["inputs"]
                await check("guide consumed", bool(inputs) and inputs[0]["status"] == "consumed", terminal["status"])
                await page.wait_for_timeout(500)
                await screenshot("04-guide-final")
                snapshot = await api("GET", f"/conversations/{conv}/snapshot")
                await check("consumed message single ID", bool(inputs) and sum(m["id"] == inputs[0]["id"] for m in snapshot["messages"]) == 1)
                await check("consumed UI single ID", bool(inputs) and await page.locator(f'[data-input-id="{inputs[0]["id"]}"]').count() == 1)
                await page.reload()
                await page.locator(".supplement-message").wait_for(timeout=15000)
                await check("input survives refresh", "已纳入" in await page.locator(".supplement-message").inner_text())
                await screenshot("05-input-restored")
                inspection = await api("GET", f"/tasks/{task['id']}/inspection")
                result["plan"] = inspection["projection"].get("plan")

            conv2 = await new_chat("3a · 未采用与停止验收")
            textarea = page.locator(".composer textarea")
            late_input = None
            # A real final-answer stream has already entered its last model call.
            # Steering submitted here must be queried, never assumed consumed.
            await textarea.fill("不要使用工具，写一段约 300 字的中文，介绍如何整理个人工作区。保持纯文本，直接开始正文。")
            await textarea.press("Enter")
            task2 = await wait_task(conv2, {"running"})
            await page.wait_for_function("() => document.querySelector('.agent-message .markdown-content')?.textContent.length > 20", timeout=90000)
            await textarea.fill("补充：结尾加上本条补充。")
            await textarea.press("Enter")
            await page.locator(".supplement-message").wait_for(timeout=15000)
            await screenshot("06-late-input-queued")
            await wait_task(conv2, {"succeeded", "failed", "cancelled", "timed_out", "interrupted"}, 150)
            late_input = (await api("GET", f"/tasks/{task2['id']}/inputs"))["inputs"][0]
            await check("late input not_consumed", late_input["status"] == "not_consumed")
            await page.get_by_role("button", name="作为新回合发送", exact=True).wait_for(timeout=20000)
            await screenshot("07-not-consumed")
            async with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/messages')) as receipt:
                await page.get_by_role("button", name="作为新回合发送", exact=True).click()
            ack = await (await receipt.value).json()
            await check("explicit new turn", ack["task_id"] != task2["id"])
            await page.wait_for_timeout(300)
            await screenshot("08-resend-new-turn")
            await textarea.press("Escape")
            cancelled = await wait_task(conv2, {"cancelled", "succeeded", "failed", "timed_out"})
            await check("Esc stop", cancelled["status"] == "cancelled", cancelled["status"])
            await page.wait_for_timeout(300)
            await screenshot("09-esc-stop")
        except Exception as error:
            result["errors"].append(str(error))
            await screenshot("failure-state")
            print("LIVE BLOCKED: " + str(error), flush=True)
        finally:
            result["conversations"] = created
            report = "short-live-results.json" if short else "remaining-live-results.json" if remaining else "live-results.json"
            (OUT / report).write_text(json.dumps(result, ensure_ascii=False, indent=2))
            for conv in created:
                try:
                    task = await task_of(conv)
                    if task and task["status"] in {"created", "queued", "running", "waiting_approval", "retry_wait"}:
                        await api("POST", f"/tasks/{task['id']}/cancel")
                except Exception:
                    pass
            await browser.close()
    print(json.dumps({"checks": result["checks"], "errors": result["errors"]}, ensure_ascii=False), flush=True)

asyncio.run(main())
