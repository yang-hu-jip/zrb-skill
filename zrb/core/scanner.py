"""大厅扫描：纯控件树文本解析（零截图零 VLM，秒级）

导航策略：无论当前在哪个 Tab，先点底部「悬赏」Tab 回大厅，再滚扫。
"""
import re
import time

SKIP = re.compile(r"元$|分钟|人赚到|推荐|热门|快速|大厅|悬赏|发现|消息|我的|待提交|公告|点一下|帮个忙|得赏金|抢红包|打卡|积分|兼职|筛选|全部|更多")

AMOUNT = re.compile(r"([\d.]+)\s*元")
DURATION = re.compile(r"人均用(.+?)分钟")

HALL_MARKERS = ["为你推荐", "热门", "快速审"]


def _bottom_tab(dev):
    """返回底部导航「悬赏」Tab 的 bounds，找不到则 None"""
    for e in dev.d.xpath('//*[@text="悬赏"]').all():
        b = e.bounds
        if b[1] > 1400:
            return b
    return None


def navigate_to_hall(dev):
    """回到悬赏大厅（幂等）：详情页先返回 → 点底部「悬赏」Tab"""
    dev.zrb_start()
    dev.dismiss_popups()

    for _ in range(4):
        cur = set(dev.texts())
        if any(m in cur for m in HALL_MARKERS):
            return True
        tab = _bottom_tab(dev)
        if tab:
            dev.click_by_bounds(tab)
            time.sleep(1.5)
            dev.dismiss_popups()
            cur = set(dev.texts())
            if any(m in cur for m in HALL_MARKERS):
                return True
            # 首页 -> 再点「悬赏大厅」
            if dev.click_text("悬赏大厅", timeout=1):
                time.sleep(1.5)
                if any(m in set(dev.texts()) for m in HALL_MARKERS):
                    return True
        else:
            # 二级页（详情/WebView）→ 返回
            dev.d.press("back")
            time.sleep(1.2)
            dev.dismiss_popups()

    return any(m in set(dev.texts()) for m in HALL_MARKERS)


def parse_screen(texts):
    """从当前屏文本解析任务卡片: 标题 + 金额"""
    tasks, cur = [], None
    for t in texts:
        m = AMOUNT.fullmatch(t.strip())
        if m and cur:
            tasks.append({"title": cur, "amount": float(m.group(1))})
            cur = None
            continue
        if DURATION.search(t) or "人赚到" in t:
            continue
        if t.startswith("【") and not SKIP.search(t):
            cur = t
    return tasks


def scan(dev, pages=3, min_amount=0.0):
    """滚动扫描大厅，返回去重后的任务列表"""
    if not navigate_to_hall(dev):
        print("⚠️ 未能确认进入悬赏大厅，请人工确认页面后重试")
        return []

    seen, out = set(), []
    for i in range(pages):
        dev.dismiss_popups()
        for t in parse_screen(dev.texts()):
            if t["title"] in seen or t["amount"] < min_amount:
                continue
            seen.add(t["title"])
            out.append(t)
        dev.d.swipe(0.5, 0.75, 0.5, 0.3)
        time.sleep(0.8)

    out.sort(key=lambda x: -x["amount"])
    return out
