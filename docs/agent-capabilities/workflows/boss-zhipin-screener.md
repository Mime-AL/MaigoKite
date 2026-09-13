# Boss 直聘职位筛选与自动投递工作流设计

> **版本**: v1.0  
> **日期**: 2026-07-15  
> **定位**: 具体业务工作流实现文档  
> **所属模块**: NanamiGopher Skill 体系

---

## 1. 概述

### 1.1 工作流目标

自动化筛选 Boss 直聘上的职位信息，使用 LLM 对职位进行评分，对高分职位自动发送沟通消息。全程模拟人类行为以避免反爬检测和封号。

### 1.2 核心价值

- **节省时间**: 一次性筛选数百个职位，无需手动浏览
- **智能匹配**: LLM 评分基于技能、薪资、地点等多维度综合评估
- **风险控制**: 人类行为模拟降低封号概率
- **透明可控**: 用户可随时暂停、审核、调整策略

---

## 2. SKILL.md 定义

```markdown
<!-- skills/boss-zhipin-screener/SKILL.md -->

---
name: boss-zhipin-screener
description: Boss直聘职位筛选与自动沟通工作流
version: 1.0
triggers:
  - "boss直聘"
  - "招聘筛选"
  - "job screener"
  - "自动沟通职位"
dependencies:
  - boss-browser
  - ocr-reader
  - llm-scoring
---

# Boss直聘职位筛选器

## 描述
浏览Boss直聘职位列表，使用LLM对职位进行评分，
对高分职位自动发送沟通消息。全程模拟人类行为避免反爬检测。

## 工作流步骤

### Phase 1: 配置解析
1. 从用户输入中提取: 职位关键词、地点、薪资范围、经验要求
2. 若参数缺失，通过对话引导用户补充

### Phase 2: 浏览器自动化抓取
1. 启动 Playwright 浏览器会话 (带 stealth 补丁)
2. 导航至 Boss直聘搜索页
3. 逐页抓取职位列表 (每页 30 个)
4. 人类行为模拟:
   - 随机延迟 3-8 秒 (正态分布，均值 5s)
   - 贝塞尔曲线鼠标轨迹
   - 自然滚动 (加速度曲线)
   - 模拟打字 (随机速度 + 偶尔停顿)
5. DOM 解析为主，OCR 为备用

### Phase 3: LLM 评分
1. 对每个职位调用评分工具
2. 评分维度:
   - 技能匹配度 (40%)
   - 薪资竞争力 (25%)
   - 地点匹配度 (15%)
   - 公司质量 (10%)
   - 发展前景 (10%)
3. 分级处理:
   - ≥85 分 → 自动沟通
   - 70-84 分 → 加入待确认清单
   - <70 分 → 跳过

### Phase 4: 人类审核
1. 展示高分职位清单
2. 用户可选择: 全部发送 / 部分发送 / 取消

### Phase 5: 自动沟通
1. 对选定职位发送预置消息
2. 每封消息间隔 15-45 秒
3. 记录发送结果

### Phase 6: 汇总报告
1. 输出统计: 浏览数、评分数、沟通数、成功率
2. 推荐 Top 5 职位

## 安全控制
- max_pages: 10 (可配置)
- daily_limit: 50 个职位/天
- rate_limit: 消息间隔 15-45 秒
- human_review_before_send: true
- abort_on_captcha: 遇到验证码立即停止并通知用户

## 状态持久化
- 中间结果保存到: {project_dir}/.skills/boss-zhipin/state/
- 支持断点续传: 中断后从上次页面继续

## 输出格式
工作流完成后返回结构化报告:
```json
{
  "total_screened": 50,
  "high_score": 12,
  "manually_reviewed": 8,
  "messages_sent": 5,
  "success_rate": 83,
  "top_recommendations": [...]
}
```
```

---

## 3. LangGraph 工作流图构建

### 3.1 状态定义

```python
from typing import TypedDict, Literal, NotRequired
from langchain_core.messages import BaseMessage
from typing import Annotated
from langgraph.graph import add_messages

class BossZhipinState(TypedDict):
    # 对话消息
    messages: Annotated[list, add_messages]
    
    # 工作流状态
    status: Literal["init", "browsing", "scoring", "paused", "messaging", "complete", "error"]
    error: NotRequired[str]
    
    # 搜索参数
    search_query: str
    location: str
    salary_range: str
    experience_req: str
    criteria: dict  # LLM 评分标准
    
    # 浏览器会话
    browser_session_id: str
    
    # 数据流转
    page_results: list[dict]       # 当前页抓取结果
    scored_results: list[dict]     # 评分后的结果
    high_score_jobs: list[dict]    # ≥85 分的职位
    medium_score_jobs: list[dict]  # 70-84 分的职位
    messages_sent: list[dict]      # 已发送消息记录
    
    # 控制流
    current_page: int
    total_pages: int
    retry_count: int
    max_retries: int
    human_approved: bool
    daily_limit_reached: bool
```

### 3.2 图构建

```python
from langgraph.graph import StateGraph, START, END

def build_boss_zhipin_graph(mcp_tools: dict) -> StateGraph:
    workflow = StateGraph(BossZhipinState)
    
    # 注册节点
    workflow.add_node("init", node_init)
    workflow.add_node("scrape", node_scrape)
    workflow.add_node("score", node_score)
    workflow.add_node("pause_review", node_pause_review)
    workflow.add_node("message", node_message)
    workflow.add_node("report", node_report)
    
    # 定义边
    workflow.add_edge(START, "init")
    workflow.add_edge("init", "scrape")
    
    # 条件边：分页循环 + 人类审核
    workflow.add_conditional_edges(
        "scrape",
        route_after_scrape,
        {
            "score": "score",       # 一页完成，进入评分
            "scrape": "scrape",     # 还有下一页，继续抓取
            "pause": "pause_review", # 达到人类审核阈值
            "end": END             # 完成或出错
        }
    )
    
    workflow.add_edge("score", "pause_review")
    workflow.add_conditional_edges(
        "pause_review",
        route_after_review,
        {"message": "message", "end": END}
    )
    workflow.add_edge("message", "report")
    workflow.add_edge("report", END)
    
    return workflow

def route_after_scrape(state: BossZhipinState) -> str:
    """分页循环控制"""
    # 重试逻辑
    if state.get("error") and state["retry_count"] < state["max_retries"]:
        return "scrape"
    
    # 是否有结果
    if state.get("page_results"):
        # 还有下一页？
        if state["current_page"] < state.get("total_pages", 1):
            return "scrape"
        # 结果太多，需要人类审核
        if len(state["page_results"]) > 20:
            return "pause"
        return "score"
    
    # 无结果，结束
    return "end"

def route_after_review(state: BossZhipinState) -> str:
    """人类审核后继续"""
    return "message" if state.get("human_approved") else "end"
```

### 3.3 节点实现

```python
async def node_init(state: BossZhipinState) -> dict:
    """初始化工作流"""
    session_id = f"bz_{int(asyncio.get_event_loop().time() * 1000)}"
    return {
        "status": "browsing",
        "current_page": 1,
        "retry_count": 0,
        "browser_session_id": session_id,
        "messages": [HumanMessage(content=f"开始筛选 Boss 直聘职位: {state['search_query']} @ {state['location']}")],
    }

async def node_scrape(state: BossZhipinState) -> dict:
    """抓取一页职位数据"""
    try:
        # 导航并搜索
        await call_mcp_tool(
            mcp_tools,
            "boss_navigate_and_search",
            {
                "query": state["search_query"],
                "location": state["location"],
                "salary": state.get("salary_range", ""),
                "page": state["current_page"],
                "session_id": state["browser_session_id"],
            }
        )
        
        # 人类行为模拟
        await call_mcp_tool(mcp_tools, "human_beat", {
            "behavior": "browse",
            "session_id": state["browser_session_id"]
        })
        
        # 提取职位列表
        result = await call_mcp_tool(
            mcp_tools,
            "boss_extract_listings",
            {
                "session_id": state["browser_session_id"],
                "max_items": 30,
            }
        )
        
        # OCR 备用
        if not result.get("jobs"):
            ocr_result = await call_mcp_tool(
                mcp_tools,
                "ocr_extract_text",
                {
                    "image_base64": result.get("screenshot", ""),
                    "mode": "structured",
                }
            )
            result["jobs"] = parse_ocr_output(ocr_result["text"])
        
        return {
            "page_results": result.get("jobs", []),
            "total_pages": result.get("total_pages", 1),
            "status": "browsing",
            "messages": [AIMessage(content=f"抓取第 {state['current_page']} 页，共 {len(result.get('jobs', []))} 个职位")],
        }
    except Exception as e:
        return {
            "error": str(e),
            "retry_count": state["retry_count"] + 1,
            "status": "error",
            "messages": [HumanMessage(content=f"抓取失败: {e}")],
        }

async def node_score(state: BossZhipinState) -> dict:
    """评分所有抓取的职位"""
    scored = []
    high_score = []
    medium_score = []
    
    for job in state["page_results"]:
        score_result = await call_mcp_tool(
            mcp_tools,
            "llm_score_job",
            {
                "job_data": job,
                "criteria": state["criteria"],
                "score_threshold": 70,
            }
        )
        job_with_score = {**job, **score_result}
        scored.append(job_with_score)
        
        if score_result.get("overall_score", 0) >= 85:
            high_score.append(job_with_score)
        elif score_result.get("overall_score", 0) >= 70:
            medium_score.append(job_with_score)
    
    return {
        "scored_results": scored,
        "high_score_jobs": high_score,
        "medium_score_jobs": medium_score,
        "status": "scoring",
        "messages": [AIMessage(content=f"评分完成: {len(scored)} 个职位，高分 {len(high_score)} 个，待确认 {len(medium_score)} 个")],
    }

async def node_pause_review(state: BossZhipinState) -> dict:
    """暂停等待人类审核"""
    top_jobs = state["high_score_jobs"][:12]
    review_text = f"""Boss 直聘筛选结果:
- 共浏览 {sum(len(state.get('page_results', [[]])[0] for _ in range(state['current_page'])))} 个职位
- 高分职位 (≥85): {len(state['high_score_jobs'])} 个
- 待确认职位 (70-84): {len(state['medium_score_jobs'])} 个

Top 推荐职位:
{chr(10).join(f"{i+1}. [{j.get('title','?')}] {j.get('company','?')} - {j.get('salary','?')} - 评分: {j.get('overall_score','?')}" for i, j in enumerate(top_jobs))}

是否自动发送沟通消息？(回复 approve/reject)"""
    
    return {
        "status": "paused",
        "human_approved": False,
        "messages": [HumanMessage(content=review_text)],
    }

async def node_message(state: BossZhipinState) -> dict:
    """自动发送沟通消息"""
    sent = []
    
    for job in state["high_score_jobs"]:
        # 生成个性化消息
        msg_content = await call_mcp_tool(
            mcp_tools,
            "llm_generate_message",
            {
                "job": job,
                "candidate_profile": state.get("candidate_profile", {}),
            }
        )
        
        # 发送消息
        await call_mcp_tool(
            mcp_tools,
            "boss_send_message",
            {
                "session_id": state["browser_session_id"],
                "job_url": job.get("url", ""),
                "message": msg_content,
            }
        )
        
        # 人类行为间隔
        await asyncio.sleep(random.uniform(15, 45))
        
        sent.append({"job": job.get("title"), "status": "sent"})
    
    return {
        "messages_sent": sent,
        "status": "complete",
        "messages": [AIMessage(content=f"已发送 {len(sent)} 条沟通消息")],
    }

async def node_report(state: BossZhipinState) -> dict:
    """生成最终报告"""
    report = f"""
Boss 直聘筛选报告
==================
搜索: {state['search_query']} @ {state['location']}
浏览页数: {state['current_page']}/{state['total_pages']}
总职位数: {len(state['scored_results'])}
高分职位: {len(state['high_score_jobs'])}
已发送消息: {len(state['messages_sent'])}
成功率: {len(state['messages_sent'])/max(len(state['high_score_jobs']),1)*100:.0f}%

Top 推荐:
{chr(10).join(f"- [{j.get('title','?')}] {j.get('company','?')} - {j.get('salary','?')}" for j in state['high_score_jobs'][:5])}
"""
    return {
        "status": "complete",
        "messages": [AIMessage(content=report.strip())],
    }
```

---

## 4. MCP 原子工具实现

### 4.1 Boss Browser MCP Server

```python
# skills/boss-zhipin-screener/tools/boss-browser/main.py
"""
Boss 直聘浏览器自动化 MCP Server
使用 Playwright + stealth 补丁
"""
import asyncio
import random
from fastmcp import FastMCP

mcp = FastMCP("boss-browser")

# === 人类行为模拟 ===

async def bezier_curve_move(page, start_x, start_y, end_x, end_y, steps=20):
    """贝塞尔曲线鼠标移动"""
    cp1x = start_x + (end_x - start_x) * 0.3 + random.uniform(-30, 30)
    cp1y = start_y + (end_y - start_y) * 0.3 + random.uniform(-20, 20)
    cp2x = start_x + (end_x - start_x) * 0.7 + random.uniform(-30, 30)
    cp2y = start_y + (end_y - start_y) * 0.7 + random.uniform(-20, 20)
    
    for t in [i / steps for i in range(steps + 1)]:
        x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1x + 3*(1-t)*t**2 * cp2x + t**3 * end_x
        y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1y + 3*(1-t)*t**2 * cp2y + t**3 * end_y
        await page.mouse.move(x + random.uniform(-2, 2), y + random.uniform(-2, 2), steps=2)
        await asyncio.sleep(random.uniform(0.01, 0.03))

async def human_typing(page, selector, text, delay_range=(50, 150)):
    """模拟人类打字"""
    element = page.locator(selector)
    for char in text:
        delay = random.randint(*delay_range)
        await asyncio.sleep(delay / 1000)
        await element.press(char)
        if random.random() < 0.1:
            await asyncio.sleep(random.uniform(0.3, 0.8))

async def natural_scroll(page, direction="down", distance=500):
    """自然滚动"""
    speed_multiplier = 1.0
    total_distance = distance * (1 if direction == "down" else -1)
    steps = 15
    
    for i in range(steps):
        progress = i / steps
        ease = 4 * progress * (1 - progress)
        scroll_amount = int(total_distance / steps * (ease + 0.3))
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(0.05 * (1/ease+0.1), 0.2))

async def human_delay(min_sec=3, max_sec=8):
    """随机等待"""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)

# === MCP 工具定义 ===

_browser_sessions = {}

async def get_or_create_browser(session_id: str):
    """获取或创建浏览器会话"""
    if session_id not in _browser_sessions:
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        context = await browser.new_context(
            user_agent=random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            ]),
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        # 覆盖 navigator.webdriver
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        _browser_sessions[session_id] = {"browser": browser, "context": context}
    return _browser_sessions[session_id]

@mcp.tool()
async def boss_navigate_and_search(query: str, location: str = "", 
                                    salary: str = "", page: int = 1,
                                    session_id: str = "") -> dict:
    """导航到 Boss 直聘搜索页"""
    session = await get_or_create_browser(session_id)
    page_obj = session["context"].new_page()
    
    url = f"https://www.zhipin.com/wapi/zpgeek/search/job/search.json?query={query}&city={location}&page={page}"
    await page_obj.goto("https://www.zhipin.com")
    await human_delay(2, 4)
    
    # 模拟输入
    await human_typing(page_obj, 'input[name="query"]', query)
    await human_delay(1, 3)
    
    if location:
        await page_obj.click('.city-selector')
        await human_delay(0.5, 1.5)
    
    await page_obj.click('button[type="submit"]')
    await page_obj.wait_for_load_state("networkidle")
    await human_delay(3, 6)
    
    return {"status": "navigated", "session_id": session_id, "page": page}

@mcp.tool()
async def boss_extract_listings(session_id: str, max_items: int = 30) -> dict:
    """提取职位列表"""
    session = _browser_sessions.get(session_id)
    if not session:
        return {"jobs": [], "error": "Browser session not found"}
    
    page_obj = session["context"].new_page()
    
    # DOM 解析
    jobs = await page_obj.evaluate(f"""
        () => {{
            const cards = document.querySelectorAll('.job-card-wrapper');
            return Array.from(cards).slice(0, {max_items}).map(card => ({{
                title: card.querySelector('.job-name')?.textContent?.trim(),
                salary: card.querySelector('.salary')?.textContent?.trim(),
                company: card.querySelector('.company-name')?.textContent?.trim(),
                experience: card.querySelector('.experience')?.textContent?.trim(),
                tags: Array.from(card.querySelectorAll('.tag span')).map(s => s.textContent.trim()),
                url: card.querySelector('.job-name a')?.href,
            }}));
        }}
    """)
    
    # 截图备用
    screenshot = await page_obj.screenshot()
    
    return {
        "jobs": jobs,
        "total_pages": extract_total_pages(page_obj),
        "has_next_page": has_next_page(page_obj),
        "screenshot": screenshot,
    }

@mcp.tool()
async def boss_send_message(session_id: str, job_url: str, message: str) -> dict:
    """发送沟通消息"""
    session = _browser_sessions.get(session_id)
    if not session:
        return {"status": "error", "error": "Browser session not found"}
    
    page_obj = session["context"].new_page()
    
    # 导航到职位详情
    await page_obj.goto(job_url)
    await human_delay(3, 6)
    await natural_scroll(page_obj, "down", 300)
    
    # 点击"立即沟通"
    await bezier_curve_move(page_obj, 100, 100, 500, 400)
    await page_obj.click('.btn-talk')
    await human_delay(1, 3)
    
    # 输入消息
    await human_typing(page_obj, 'textarea', message)
    await human_delay(1, 2)
    
    # 发送
    await page_obj.mouse.move(random.randint(200, 600), random.randint(200, 500))
    await human_delay(0.5, 2)
    await page_obj.click('.send-btn')
    await human_delay(2, 4)
    
    return {"status": "sent", "job_url": job_url}

@mcp.tool()
async def human_beat(behavior_type: str = "browse", session_id: str = "") -> dict:
    """人类行为模拟"""
    session = _browser_sessions.get(session_id)
    if not session:
        return {"status": "error"}
    
    page_obj = session["context"].new_page()
    
    if behavior_type == "browse":
        for _ in range(random.randint(3, 8)):
            x = random.randint(100, 900)
            y = random.randint(100, 700)
            await bezier_curve_move(page_obj, 0, 0, x, y)
            await human_delay(0.5, 2)
    elif behavior_type == "scroll":
        await natural_scroll(page_obj, "down", random.randint(200, 800))
    elif behavior_type == "rest":
        await human_delay(5, 15)
    
    return {"status": "behavior_applied", "type": behavior_type}
```

### 4.2 OCR Reader MCP Server

```python
# skills/boss-zhipin-screener/tools/ocr-reader/main.py
"""
OCR 内容识别 MCP Server
使用 PaddleOCR + VLM 增强
"""
from fastmcp import FastMCP
import base64
from PIL import Image
import io

mcp = FastMCP("ocr-reader")

@mcp.tool()
async def ocr_extract_text(image_base64: str, mode: str = "fast", 
                           lang: str = "zh") -> dict:
    """从截图提取文字"""
    img_data = base64.b64decode(image_base64)
    img = Image.open(io.BytesIO(img_data))
    
    if mode == "fast":
        # PaddleOCR 快速模式
        from paddlex import OCR
        ocr_model = OCR(model_name="PP-OCRv6_medium")
        result = ocr_model.predict(str(img))
        text_blocks = []
        for res in result:
            text_blocks.append({
                "text": res["text"],
                "confidence": res["confidence"],
                "bbox": res["bbox"],
            })
        return {"text": "\n".join(b["text"] for b in text_blocks), "blocks": text_blocks}
    
    elif mode == "accurate":
        # PaddleOCR + VLM 增强
        from paddlex import OCR
        ocr_model = OCR(model_name="PP-OCRv6_medium")
        result = ocr_model.predict(str(img))
        # 如果置信度低，使用 VLM
        avg_conf = sum(r["confidence"] for r in result) / len(result) if result else 0
        if avg_conf < 0.7:
            # 调用 VLM (Qwen2.5-VL 或 PaddleOCR-VL)
            return await vl_enhanced_extract(img)
        return {"text": "\n".join(r["text"] for r in result), "blocks": result}
    
    return {"text": "", "blocks": []}

async def vl_enhanced_extract(img: Image.Image) -> dict:
    """VLM 增强提取"""
    # 这里可以集成 Qwen2.5-VL 或 PaddleOCR-VL
    # 简化示例
    return {"text": "VLM 提取结果", "blocks": [], "mode": "vl_enhanced"}
```

### 4.3 LLM Scoring MCP Server

```python
# skills/boss-zhipin-screener/tools/llm-scoring/scorer.py
"""
LLM 评分 MCP Server
"""
from fastmcp import FastMCP
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json

mcp = FastMCP("llm-scoring")

@mcp.tool()
async def llm_score_job(job_data: dict, criteria: dict, 
                        score_threshold: int = 70) -> dict:
    """评分职位"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位职业顾问，负责评估职位匹配度。
        评分维度:
        - 技能匹配度 (40%): 职位要求与候选人技能的契合程度
        - 薪资竞争力 (25%): 薪资是否在期望范围内
        - 地点匹配度 (15%): 工作地点是否可接受
        - 公司质量 (10%): 公司规模、行业地位
        - 发展前景 (10%): 技术栈先进性、团队规模增长
        
        只返回 JSON:
        {
          "overall_score": 0-100,
          "dimensions": {
            "skill_match": 0-100,
            "salary": 0-100,
            "location": 0-100,
            "company": 0-100,
            "growth": 0-100
          },
          "reasoning": "简短说明",
          "recommended_action": "message|save|skip"
        }"""),
        ("human", """职位信息:
        标题: {title}
        薪资: {salary}
        公司: {company}
        经验要求: {experience}
        标签: {tags}
        
        筛选标准:
        {criteria}"""),
    ])
    
    chain = prompt | llm
    response = await chain.ainvoke({
        "title": job_data.get("title", ""),
        "salary": job_data.get("salary", ""),
        "company": job_data.get("company", ""),
        "experience": job_data.get("experience", ""),
        "tags": ", ".join(job_data.get("tags", [])),
        "criteria": json.dumps(criteria, ensure_ascii=False),
    })
    
    result = json.loads(response.content)
    result["meets_threshold"] = result["overall_score"] >= score_threshold
    return result

@mcp.tool()
async def llm_generate_message(job_data: dict, candidate_profile: dict) -> str:
    """生成个性化沟通消息"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的求职者，正在与招聘方沟通。
        生成一段简短、专业、个性化的沟通消息。
        长度控制在 100 字以内。
        提及职位亮点和自身匹配优势。"""),
        ("human", """职位: {title}
        公司: {company}
        薪资: {salary}
        
        候选人背景:
        技能: {skills}
        经验: {experience}
        期望: {expectations}"""),
    ])
    
    chain = prompt | llm
    response = await chain.ainvoke({
        "title": job_data.get("title", ""),
        "company": job_data.get("company", ""),
        "salary": job_data.get("salary", ""),
        "skills": ", ".join(candidate_profile.get("skills", [])),
        "experience": candidate_profile.get("experience", ""),
        "expectations": candidate_profile.get("expectations", ""),
    })
    
    return response.content.strip()
```

---

## 5. 端到端执行示例

```
用户: "帮我筛 Boss 上北京的 Python 岗位，薪资 20K+，至少 3 年经验"

Agent 执行流程:

[init]
  → 解析参数: query="Python", location="北京", salary="20K+", exp="3+"
  → 创建浏览器会话 session_bz_1784045621
  → 状态: status="running", current_page=1

[scrape] page=1
  → navigate("boss直聘搜索页", query="Python", location="北京")
  → human_delay(3s, 6s)
  → extract_listings(page=1) → 30 个职位
  → human_delay(5s, 8s)
  → 状态: page_results=30条, current_page=2

[scrape] page=2
  → extract_listings(page=2) → 30 个职位
  → 状态: page_results=30条, current_page=3

[scrape] page=3
  → extract_listings(page=3) → 0 个职位 (无更多结果)
  → route_after_scrape → "score"

[score]
  → 对 60 个职位逐一调用 llm-scoring.score_job
  → 结果: ≥85分(12个), 70-84分(8个), <70分(40个)
  → 状态: scored_results=60条, high_score_jobs=12条

[pause_review]
  → 向用户展示: "找到 60 个职位，12 个高分，8 个待确认"
  → 展示 Top 12 高分职位清单
  → 等待用户确认

[message] (用户确认)
  → 对 12 个高分职位逐一:
    - generate_message(job, profile) → 个性化消息
    - click("立即沟通") → 贝塞尔曲线鼠标轨迹
    - fill(textarea, message) → 模拟打字
    - click("发送") → 悬停后点击
    - human_delay(15s, 45s) → 消息间隔
  → 状态: messages_sent=12条

[report]
  → 输出: "完成! 浏览 60 个职位，已沟通 12 个，成功率 100%"
  → 保存报告到 state/reports/
  → 状态: status="complete"
```

---

## 6. 安全控制与风险评估

### 6.1 反封号策略

| 策略 | 实现 | 效果 |
|------|------|------|
| 浏览器指纹伪装 | navigator.webdriver = undefined | 绕过基础检测 |
| 人类行为模拟 | 贝塞尔曲线鼠标、随机延迟 | 降低行为分析风险 |
| 独立浏览器 Profile | Cookie 隔离 | 不影响主账号 |
| 每日限额 | 默认 50 个职位/天 | 避免高频操作 |
| 异常检测 | 连续验证码 → 暂停 | 及时止损 |

### 6.2 风险控制

```
风险等级评估:

低:
  ✅ 使用独立浏览器 Profile
  ✅ 人类行为模拟
  ✅ 每日限额控制

中:
  ⚠️ Boss 直聘可能更新反爬策略
  ⚠️ 长时间运行可能被检测到

高:
  ❌ 不建议用于企业账号
  ❌ 不建议高频次使用

缓解措施:
  • 首次使用默认低强度模式
  • 用户确认后逐步提高频率
  • 提供手动覆盖开关
  • 所有操作记录到审计日志
```

### 6.3 用户保护

```
用户操作流程:
1. 启动工作流 → 解析参数
2. 抓取职位 → 展示进度
3. LLM 评分 → 展示结果
4. 人类审核 → 用户确认/调整
5. 发送消息 → 展示状态
6. 汇总报告 → 保存记录

用户可随时:
  • 点击 [停止] 终止工作流
  • 调整评分阈值
  • 选择部分职位沟通
  • 查看审计日志
```

---

## 7. 配置参考

```yaml
# skills/boss-zhipin-screener/config.yaml
workflow:
  max_pages: 10
  daily_limit: 50
  score_threshold:
    auto_communicate: 85
    manual_confirm: 70
  
  human_behavior:
    min_delay_ms: 2000
    max_delay_ms: 8000
    scroll_min_pages: 3
    scroll_max_pages: 8
    break_interval_positions: 5
    break_duration_min_sec: 30
    break_duration_max_sec: 60
  
  browser:
    profile_name: "boss-autopilot"
    headless: false
    viewport: {"width": 1920, "height": 1080}
  
  scoring:
    dimensions:
      skill_match: 0.4
      salary: 0.25
      location: 0.15
      company: 0.1
      growth: 0.1

anti_detect:
  stealth_enabled: true
  rotate_user_agent: true
  custom_cookies: false

ocr:
  engine: "paddleocr"
  model_tier: "medium"
  vlm:
    enabled: false
    provider: "paddleocr-vl"
```

---

*本文档为具体业务工作流设计，不属于核心 PRD 范畴。*
