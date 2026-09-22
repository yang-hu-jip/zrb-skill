"""依赖 App 预装检查（执行前 ensure，避免任务中断）

- 关键词 -> 包名 映射来自 ui_map.yaml: app_map
- 缺失时给出待装清单（自动装机走小米商店流程，见 SOP）
"""
import os

import yaml

from .device import adb

MAP_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui_map.yaml")


def load_app_map():
    with open(MAP_FILE, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("app_map", {})


def installed_packages():
    out = adb("shell", "pm", "list", "packages")
    return {l.split("package:")[-1].strip() for l in out.splitlines() if l.startswith("package:")}


def ensure_apps(text, packages=None):
    """检查 text 中命中的 App 是否已安装。
    返回 dict(missing=[(关键词, 包名)], present=[(关键词, 包名)])
    """
    app_map = load_app_map()
    pkgs = packages if packages is not None else installed_packages()
    missing, present = [], []
    for kw, pkg in app_map.items():
        if kw in text:
            (present if pkg in pkgs else missing).append((kw, pkg))
    return {"missing": missing, "present": present}
