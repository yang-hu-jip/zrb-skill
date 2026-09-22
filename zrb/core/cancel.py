"""善后流程：任务无法完成时 → 待提交页 → 取消报名

页面: ActivityUnsubmitAndWanted  (待提交悬赏)
   Tab: 已报名 / 想报名
   卡片按钮: [取消报名] [继续做悬赏]
"""
import time


def goto_pending(dev):
    """从任意页面进入待提交页（幂等）"""
    dev.zrb_start()
    dev.dismiss_popups()

    for _ in range(4):
        el = dev.d.xpath('//*[contains(@text,"待提交")]')
        if el.exists:
            dev.click_by_bounds(el.get().bounds)
            time.sleep(2.5)
            dev.dismiss_popups()
            if "Unsubmit" in dev.current().get("activity", ""):
                return True
        # 不在首页则先回首页
        tab = None
        for e in dev.d.xpath('//*[@text="悬赏"]').all():
            b = e.bounds
            if b[1] > 1400:
                tab = b
                break
        if tab:
            dev.click_by_bounds(tab)
        else:
            dev.d.press("back")
        time.sleep(1.5)
        dev.dismiss_popups()
    return "Unsubmit" in dev.current().get("activity", "")


def cancel_task(dev, keyword):
    """在待提交页找到含 keyword 的任务，点其[取消报名]并确认。
    返回 dict(ok, reason, title)
    """
    if not goto_pending(dev):
        return {"ok": False, "reason": "未能进入待提交页", "title": None}

    title_el = dev.d.xpath(f'//*[contains(@text,"{keyword}")]')
    if not title_el.exists:
        return {"ok": False, "reason": f"待提交页未找到含[{keyword}]的任务", "title": None}
    title = title_el.get().text
    tb = title_el.get().bounds

    # 在同一张卡片内找[取消报名]（y 在标题下方 0~260px 内，x 在左半屏）
    target = None
    for e in dev.d.xpath('//*[@text="取消报名"]').all():
        b = e.bounds
        if tb[1] - 60 <= b[1] <= tb[3] + 260 and b[0] < 400:
            target = b
            break
    if target is None:
        return {"ok": False, "reason": "该卡片未找到[取消报名]按钮", "title": title}

    dev.click_by_bounds(target)
    time.sleep(2)

    # 确认弹窗: "您确定要取消报名此悬赏的名额么？" [不取消报名] [取消报名]
    # 注意: 必须精确匹配 @text="取消报名"，否则会命中"不取消报名"
    confirmed = False
    if dev.wait_text("确定要取消报名", timeout=4):
        btn = dev.d.xpath('//*[@text="取消报名"]')
        if btn.exists:
            btn.click()
            confirmed = True
    if not confirmed:  # 兜底: 无弹窗时的其他确认按钮
        for t in ["确定", "确认", "确定取消"]:
            if dev.click_text(t, timeout=1.5):
                confirmed = True
                break
    time.sleep(2.5)

    # 校验: 弹窗已关 且 该卡片区域内不再有[取消报名]按钮(已变为"重新报名")
    dialog_gone = not dev.d.xpath('//*[contains(@text,"确定要取消报名")]').exists
    if not dialog_gone:
        return {"ok": False, "reason": "确认弹窗未关闭(可能需要人工确认)", "title": title}

    still = False
    tb2 = dev.d.xpath(f'//*[contains(@text,"{keyword}")]')
    if tb2.exists:
        t2 = tb2.get().bounds
        for e in dev.d.xpath('//*[@text="取消报名"]').all():
            b = e.bounds
            if t2[1] - 60 <= b[1] <= t2[3] + 260 and b[0] < 400:
                still = True
                break
    if still:
        return {"ok": False, "reason": "卡片上仍存在[取消报名]按钮", "title": title}
    return {"ok": True, "reason": "已取消(卡片按钮已变为'重新报名')", "title": title}
