"""设备控制与通用 UI 工具

铁律：
- 所有 adb 调用使用 subprocess 列表参数（禁止 shell 字符串传中文）
- 所有等待使用条件轮询（禁止盲等）
"""
import subprocess
import time

import uiautomator2 as u2

PKG_ZRB = "com.jianzhiku.zhongrenbang"

# 常见弹窗按钮：自动点掉（保守白名单，只点明确安全的）
POPUP_TEXTS = [
    "同意并继续", "始终允许", "仅在使用中允许", "允许",
    "知道了", "我知道了", "暂不更新", "以后再说",
    "不再提示", "跳过", "确认", "继续",
]

# 遇到以下关键词 → 暂停交还用户（铁律 2）
# 注意：用"精确短语"而非宽泛词，避免普通页面误报（如任务要求里提到"验证码"）
HUMAN_GATE_KEYWORDS = [
    "请输入短信验证码", "验证码已发送", "获取验证码后登录",
    "滑块验证", "拖动滑块", "安全验证", "京东验证",
    "本机号码一键登录", "人脸识别", "实名认证",
    "输入支付密码", "请输入支付密码", "确认付款", "立即支付", "收银台",
    "请登录后重试",
]


def adb(*args, timeout=30):
    """统一 adb 调用（列表参数，避免 Windows 转义）"""
    r = subprocess.run(["adb"] + list(args), capture_output=True, text=True, timeout=timeout)
    return r.stdout + r.stderr


class Device:
    def __init__(self, serial=None):
        self.d = u2.connect(serial) if serial else u2.connect()
        self.serial = self.d.serial

    # ---------- 基础 ----------
    def screenshot(self, path):
        self.d.screenshot(path)
        return path

    def current(self):
        return self.d.app_current()

    def texts(self):
        return [e.text for e in self.d.xpath("//*[@text]").all() if e.text and e.text.strip()]

    def click_text(self, text, contains=True, timeout=3):
        xp = f'//*[contains(@text,"{text}")]' if contains else f'//*[@text="{text}"]'
        el = self.d.xpath(xp)
        if el.wait(timeout):
            el.click()
            return True
        return False

    # ---------- 等待（条件轮询，禁止盲等）----------
    def wait_text(self, text, timeout=8, contains=True):
        xp = f'//*[contains(@text,"{text}")]' if contains else f'//*[@text="{text}"]'
        el = self.d.xpath(xp)
        return el if el.wait(timeout) else None

    def wait_any(self, texts, timeout=8):
        """等待任一文本出现，返回命中的文本"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            cur = set(self.texts())
            for t in texts:
                if any(t in c for c in cur):
                    return t
            time.sleep(0.3)
        return None

    def wait_activity(self, keyword, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if keyword in self.current().get("activity", ""):
                return True
            time.sleep(0.3)
        return False

    # ---------- 弹窗处理 ----------
    def dismiss_popups(self, max_rounds=3):
        clicked = []
        for _ in range(max_rounds):
            hit = False
            for t in POPUP_TEXTS:
                el = self.d.xpath(f'//*[@text="{t}"]')
                if el.exists:
                    try:
                        el.click()
                        clicked.append(t)
                        hit = True
                        time.sleep(0.5)
                    except Exception:
                        pass
            if not hit:
                break
        return clicked

    def click_by_bounds(self, bounds, offset_y=0):
        x = (bounds[0] + bounds[2]) // 2
        y = (bounds[1] + bounds[3]) // 2 + offset_y
        self.d.click(x, y)

    # ---------- 状态识别 ----------
    def human_gate(self):
        """检测是否需要人工接管（铁律 2）。返回命中关键词或 None"""
        cur = self.texts()
        joined = " ".join(cur)
        for kw in HUMAN_GATE_KEYWORDS:
            if kw in joined:
                return kw
        return None

    def zrb_state(self):
        """众人帮页面状态: home/hall/detail_not_applied/detail_applied/other"""
        act = self.current()
        if act["package"] != PKG_ZRB:
            return f"other:{act['package']}"
        cur = self.texts()
        if "立即报名" in cur:
            return "detail_not_applied"
        if "重新报名" in cur:
            return "detail_applied"
        if any(t in cur for t in ["悬赏大厅", "为你推荐", "快速审"]):
            return "hall"
        if any(t in cur for t in ["点一下", "帮个忙", "得赏金"]):
            return "home"
        return "unknown"

    def zrb_start(self):
        self.d.app_start(PKG_ZRB, stop=False)
        time.sleep(1.5)
        self.dismiss_popups()
        return self.zrb_state()
