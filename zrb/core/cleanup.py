"""任务完成后的后台清理

两步：
1) force-stop: 结束任务用过的第三方 App 进程（保留众人帮/微信/支付宝等日常 App）
2) 多任务界面一键清理: MIUI 的「清理全部任务」按钮
3) 回到众人帮，保持任务状态可见
"""
import time

from .apps import load_app_map, installed_packages
from .device import adb

# 日常 App 不清理（避免打扰用户）
KEEP_ALWAYS = {"com.tencent.mm", "com.eg.android.AlipayGphone",
               "com.jianzhiku.zhongrenbang"}

BROWSERS = ["com.android.browser", "mark.via", "com.microsoft.emmx",
            "com.android.chrome"]


def default_targets():
    """默认清理目标：app_map 里已安装的第三方 App（排除日常）+ 浏览器"""
    installed = installed_packages()
    targets = [pkg for pkg in load_app_map().values()
               if pkg in installed and pkg not in KEEP_ALWAYS]
    targets += [b for b in BROWSERS if b in installed]
    return sorted(set(targets))


def force_stop(pkgs):
    done = []
    for p in pkgs:
        adb("shell", "am", "force-stop", p)
        done.append(p)
    return done


def clear_recents(dev):
    """打开多任务界面并点「清理全部任务」"""
    dev.d.press("recent")
    time.sleep(1.5)
    for desc in ["清理全部任务", "清除全部", "关闭全部"]:
        el = dev.d.xpath(f'//*[@content-desc="{desc}"]')
        if el.exists:
            el.click()
            time.sleep(1.2)
            dev.d.press("back")
            time.sleep(1)
            return desc
    # 兜底：文本按钮
    for t in ["清除全部", "清理全部", "关闭全部", "一键清理"]:
        if dev.click_text(t, timeout=1):
            time.sleep(1)
            dev.d.press("back")
            return t
    dev.d.press("back")
    return None


def cleanup(dev, pkgs=None, recents=True):
    targets = pkgs if pkgs is not None else default_targets()
    result = {"force_stopped": force_stop(targets), "recents": None}

    if recents:
        result["recents"] = clear_recents(dev)

    time.sleep(1)
    dev.zrb_start()
    result["back_to"] = dev.zrb_state()
    return result
