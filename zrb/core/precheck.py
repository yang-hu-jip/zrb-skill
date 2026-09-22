"""报名前预检：探测目标页存活，避免浪费报名名额

两种模式：
- 快检 check_url():      HTTP 请求（秒级）。适合静态页；活动页是 JS 壳会假阳性
- 渲染检 check_url_rendered(): 设备端真实渲染后读文本（10~20s）。活动类链接必用
"""
import json
import time

import requests

MOBILE_UA = ("Mozilla/5.0 (Linux; Android 15; 2409BRN2CC) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36")

DEAD_KEYWORDS = ["活动太火爆", "活动已结束", "已结束", "活动已下线",
                 "页面不存在", "无法访问", "404 Not Found", "活动已抢光"]
LOGIN_KEYWORDS = ["请登录", "登录后", "立即登录"]


def check_url(url, timeout=10):
    """HTTP 快检。返回 dict(ok, reason, status)"""
    try:
        r = requests.get(url, headers={"User-Agent": MOBILE_UA},
                         timeout=timeout, allow_redirects=True)
    except requests.RequestException as e:
        return {"ok": False, "reason": f"请求失败: {type(e).__name__}", "status": None}
    text = r.text[:20000]
    for kw in DEAD_KEYWORDS:
        if kw in text:
            return {"ok": False, "reason": f"页面命中: {kw}", "status": r.status_code}
    if r.status_code >= 400:
        return {"ok": False, "reason": f"HTTP {r.status_code}", "status": r.status_code}
    if "<div id=\"app\"" in text or "<div id=app" in text:
        return {"ok": None, "reason": "JS壳页面，快检不可靠 → 请用 --render", "status": r.status_code}
    return {"ok": True, "reason": "存活", "status": r.status_code}


def _read_all_texts(dev):
    out = set()
    for e in dev.d.xpath("//*[@text]").all():
        if e.text and e.text.strip():
            out.add(e.text.strip())
    return out


def check_url_rendered(dev, url, pkg=None, wait=10):
    """设备端真实渲染预检。

    pkg: 指定用哪个 App 打开（如 com.jingdong.app.mall）；None=系统浏览器
    返回 dict(ok, reason, evidence)
    """
    from .device import adb
    args = ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url]
    if pkg:
        args = ["shell", "am", "start", "-a", "android.intent.action.VIEW",
                "-d", url, "-p", pkg]
    adb(*args)

    texts, deadline = set(), time.time() + wait
    while time.time() < deadline:
        time.sleep(1.5)
        texts |= _read_all_texts(dev)
        if any(k in " ".join(texts) for k in DEAD_KEYWORDS):
            break

    joined = " ".join(texts)
    result = {"ok": True, "reason": "存活", "evidence": list(texts)[:8]}

    for kw in DEAD_KEYWORDS:
        if kw in joined:
            result = {"ok": False, "reason": f"渲染命中死亡关键词: {kw}",
                      "evidence": list(texts)[:8]}
            break
    else:
        if any(k in joined for k in LOGIN_KEYWORDS):
            result = {"ok": None, "reason": "页面要求登录（活动可能存活，需登录验证）",
                      "evidence": list(texts)[:8]}

    # 回到众人帮
    dev.zrb_start()
    return result
