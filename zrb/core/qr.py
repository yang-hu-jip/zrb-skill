"""QR 极速通道（已实测）

流程：
  长按二维码 → 微信扫一扫 → "知道了"（触发 App 把原图落盘）
  → MediaStore 找最新 /sdcard/Pictures/zrbdownload_*.png
  → adb pull → 本地多引擎解码 → URL

禁止走微信界面取 URL（诱导页拦截 + 控件树不可读）。
"""
import os
import subprocess
import time

import cv2
from PIL import Image
from pyzbar.pyzbar import decode as zbar_decode

from .device import adb

PICTURES = "/sdcard/Pictures"
QR_PREFIXES = ("zrbdownload", "qr_task")


def newest_qr_file(after_ts=None):
    """通过 MediaStore 查询最新的二维码原图文件路径"""
    out = adb("shell", "content", "query", "--uri",
              "content://media/external/images/media",
              "--projection", "_display_name:_data:date_added")
    best = None
    for line in out.splitlines():
        if not line.startswith("Row:"):
            continue
        try:
            parts = dict(p.split("=", 1) for p in line.split(", ")[1:])
            name = parts["_display_name"]
            added = int(parts["date_added"])
        except Exception:
            continue
        if not name.startswith(QR_PREFIXES):
            continue
        if after_ts and added < after_ts:
            continue
        if best is None or added > best[0]:
            best = (added, parts["_data"])
    return best[1] if best else None


def trigger_save(dev, timeout=15):
    """在众人帮详情页触发原图落盘: 长按二维码 → 微信扫一扫 → 知道了"""
    before = time.time()
    label = dev.wait_text("长按识别图中二维码", timeout=6)
    if label is None:
        return None
    b = label.bounds
    dev.d.long_click((b[0] + b[2]) // 2, b[3] + 150)
    time.sleep(1.5)
    if dev.click_text("微信扫一扫", timeout=3):
        dev.wait_text("知道了", timeout=8)
        dev.click_text("知道了", timeout=3)
    # 等落盘
    deadline = time.time() + timeout
    while time.time() < deadline:
        path = newest_qr_file(after_ts=before - 5)
        if path:
            return path
        time.sleep(1)
    return None


def decode_file(local_path):
    """多引擎解码本地图片，返回 URL 或 None"""
    img = cv2.imread(local_path)
    if img is None:
        return None
    results = set()
    try:
        for r in zbar_decode(Image.open(local_path)):
            results.add(r.data.decode(errors="ignore"))
    except Exception:
        pass
    try:
        data, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
        if data:
            results.add(data)
    except Exception:
        pass
    try:
        det = cv2.wechat_qrcode_WeChatQRCode()
        r2, _ = det.detectAndDecode(img)
        results.update(r2)
    except Exception:
        pass
    for r in results:
        if r and r.startswith("http"):
            return r
    return results.pop() if results else None


def pull_and_decode(remote_path, local_path="qr_original.png"):
    adb("pull", remote_path, local_path)
    url = decode_file(local_path)
    return url


def fastpath(dev):
    """一键：触发落盘 + 拉取 + 解码。返回 (url, remote_path)"""
    remote = trigger_save(dev)
    if not remote:
        return None, None
    url = pull_and_decode(remote)
    return url, remote
