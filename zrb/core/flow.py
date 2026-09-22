"""执行流程封装: apply / upload / submit"""
import time

from . import journal


def apply(dev):
    """报名当前详情页任务"""
    if dev.zrb_state() == "detail_applied":
        return {"ok": True, "reason": "已报名(幂等)"}
    btn = dev.d.xpath('//*[@text="立即报名"]')
    if not btn.exists:
        for _ in range(5):
            dev.d.swipe(0.5, 0.8, 0.5, 0.35)
            time.sleep(0.6)
            if btn.wait(0.5):
                break
    if not btn.exists:
        return {"ok": False, "reason": "未找到报名按钮"}
    btn.click()
    time.sleep(2)
    dev.dismiss_popups()
    if dev.wait_text("报名成功", timeout=6):
        dev.click_text("立即开始", timeout=3)
    return {"ok": dev.wait_text("重新报名", timeout=6) is not None,
            "reason": "报名流程结束"}


def upload(dev, local_img):
    """上传证据: 点[上传截图] -> 系统选择器选图(需人工兜底)"""
    dev.dismiss_popups()
    if not dev.click_text("上传截图", timeout=4):
        return {"ok": False, "reason": "未找到上传截图按钮"}
    time.sleep(3)
    # 选择器: 优先匹配最近图片(第一格)
    for kw in ["最近", "图片", "所有图片"]:
        dev.click_text(kw, timeout=1.5)
    dev.d.click(120, 420)   # 首图位(选择器网格第一格)
    time.sleep(2)
    for t in ["完成", "确定", "添加"]:
        if dev.click_text(t, timeout=2):
            break
    time.sleep(2)
    return {"ok": True, "reason": "已执行上传交互, 请核对截图是否挂上"}


def submit(dev, note=None, confirm=True):
    """填写反馈并提交。confirm=True 时由调用方(人)确认"""
    if note:
        f = dev.d.xpath('//*[contains(@text,"体验过程中自己的建议")]')
        if f.exists:
            f.click()
            time.sleep(0.8)
            dev.d.send_keys(note)
            time.sleep(1)
    if confirm:
        return {"ok": True, "reason": "待确认: 请人工点[提交]或在终端确认后重跑 --yes"}
    if dev.click_text("提交", timeout=4):
        time.sleep(2)
        return {"ok": True, "reason": "已提交"}
    return {"ok": False, "reason": "未找到提交按钮"}
