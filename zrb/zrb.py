"""zrb — 众人帮 skill CLI 入口

用法:
  python zrb.py status                  查看设备/页面状态
  python zrb.py popups                  清理已知弹窗
  python zrb.py scan [--pages 3] [--min 0.5] [--out tasks.json]
  python zrb.py qr                      二维码极速通道(触发落盘→解码→输出URL)
  python zrb.py precheck <url>          目标页存活预检
  python zrb.py open <url>              投递URL打开(浏览器优先)
  python zrb.py push <file>             推图到相册+媒体扫描(上传证据)
  python zrb.py journal [--pending]     查看台账/待处理项

铁律: 一切操作经此CLI, 禁止 python -c 传中文
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import journal
from core.device import Device, adb
from core.flow import apply, submit, upload
from core.precheck import check_url, check_url_rendered
from core.qr import fastpath
from core.scanner import scan


def cmd_status(args):
    dev = Device(args.serial)
    cur = dev.current()
    state = dev.zrb_state()
    gate = dev.human_gate()
    print(json.dumps({
        "serial": dev.serial,
        "screen": list(dev.d.window_size()),
        "package": cur["package"],
        "activity": cur["activity"],
        "zrb_state": state,
        "human_gate": gate,
    }, ensure_ascii=False, indent=1))
    if gate:
        print(f"⚠️ 检测到人工闸门关键词[{gate}] → 按铁律暂停，确认后继续")


def cmd_popups(args):
    dev = Device(args.serial)
    print("已处理弹窗:", dev.dismiss_popups())


def cmd_scan(args):
    dev = Device(args.serial)
    tasks = scan(dev, pages=args.pages, min_amount=args.min_amount)
    print(f"扫描到 {len(tasks)} 个任务:")
    for t in tasks:
        print(f"  {t['amount']:>6.2f} 元 | {t['title']}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=1)
        print("已保存:", args.out)


def cmd_qr(args):
    dev = Device(args.serial)
    url, remote = fastpath(dev)
    print(json.dumps({"url": url, "remote_file": remote}, ensure_ascii=False))
    if url:
        journal.append("QR解码", "已执行待提交", url=url, evidence=remote)


def cmd_precheck(args):
    if args.render:
        dev = Device(args.serial)
        res = check_url_rendered(dev, args.url, pkg=args.pkg, wait=args.wait)
    else:
        res = check_url(args.url)
    print(json.dumps(res, ensure_ascii=False))
    if res["ok"] is False:
        print("❌ 预检不通过 → 建议放弃该任务，不浪费报名名额")
        journal.append(f"预检:{args.url[:60]}", "预检失败跳过", reason=res["reason"])
    elif res["ok"] is None:
        print("⚠️ 无法确定（需人工/登录验证）")
    else:
        print("✅ 预检通过，可以报名")


def cmd_open(args):
    adb("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", args.url)
    print("已投递:", args.url)


def cmd_push(args):
    """把本地图片推送到手机相册并触发媒体扫描（用于提交证据）"""
    local = os.path.abspath(args.file)
    remote = f"/sdcard/Pictures/{os.path.basename(local)}"
    print(adb("push", local, remote).strip())
    print(adb("shell", "am", "broadcast", "-a",
              "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
              "-d", f"file://{remote}").strip()[:120])
    time.sleep(1)
    out = adb("shell", "content", "query", "--uri",
              "content://media/external/images/media",
              "--projection", "_display_name:_data")
    hit = [l for l in out.splitlines() if os.path.basename(local) in l]
    print("入库:", hit[0] if hit else "未确认(可能延迟)")


def cmd_journal(args):
    if args.pending:
        items = journal.pending()
        print(f"待处理 {len(items)} 项:")
        for r in items:
            print(" ", r["ts"], r["task"], r["status"])
    else:
        print("今日统计:", journal.today_summary())
        for r in journal.read_all()[-args.tail:]:
            print(" ", r["ts"], r["task"], r["status"])


def cmd_cancel(args):
    """善后：待提交页取消报名（任务无法完成时使用）"""
    from core.cancel import cancel_task
    dev = Device(args.serial)
    res = cancel_task(dev, args.keyword)
    print(json.dumps(res, ensure_ascii=False))
    if res["ok"]:
        journal.append(res["title"] or args.keyword, "已取消报名", reason=args.reason)
        print("✅ 已取消并记入台账")
    else:
        print("⚠️ 未完成:", res["reason"])


def cmd_clip(args):
    """读取剪贴板（需 AdbKeyboard，已随 u2 init 安装）"""
    dev = Device(args.serial)
    try:
        dev.d.set_input_ime(True)
        txt = dev.d.clipboard
    except Exception as e:
        print(json.dumps({"ok": False, "err": str(e)}, ensure_ascii=False))
        return
    print(txt)


def cmd_apply(args):
    dev = Device(args.serial)
    print(json.dumps(apply(dev), ensure_ascii=False))


def cmd_upload(args):
    dev = Device(args.serial)
    res = upload(dev, args.img)
    print(json.dumps(res, ensure_ascii=False))
    journal.append("上传证据", "已执行待确认", img=args.img)


def cmd_submit(args):
    dev = Device(args.serial)
    res = submit(dev, note=args.note, confirm=not args.yes)
    print(json.dumps(res, ensure_ascii=False))
    if res["ok"] and args.yes:
        journal.append(args.note or "提交", "已提交待审核")


def cmd_cleanup(args):
    """任务完成后的后台清理"""
    from core.cleanup import cleanup
    dev = Device(args.serial)
    pkgs = args.apps.split(",") if args.apps else None
    res = cleanup(dev, pkgs=pkgs, recents=not args.no_recents)
    print(json.dumps(res, ensure_ascii=False, indent=1))


def cmd_ensure(args):
    """依赖 App 预装检查：任务文本里命中的 App 是否已装"""
    from core.apps import ensure_apps
    res = ensure_apps(args.text)
    if res["present"]:
        print("✅ 已安装:", [f"{k}({p})" for k, p in res["present"]])
    if res["missing"]:
        print("❌ 未安装:", [f"{k}({p})" for k, p in res["missing"]])
        print("→ 先装好再报名（小米商店搜索关键词安装）")
    else:
        print("依赖齐全，可继续")


def main():
    p = argparse.ArgumentParser(description="众人帮 skill CLI")
    p.add_argument("--serial", default=None, help="设备序列号(默认自动)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="查看状态").set_defaults(func=cmd_status)
    sub.add_parser("popups", help="清理弹窗").set_defaults(func=cmd_popups)

    s = sub.add_parser("scan", help="扫描大厅")
    s.add_argument("--pages", type=int, default=3)
    s.add_argument("--min", dest="min_amount", type=float, default=0.0)
    s.add_argument("--out", default="tasks.json")
    s.set_defaults(func=cmd_scan)

    sub.add_parser("qr", help="二维码极速通道").set_defaults(func=cmd_qr)

    s = sub.add_parser("precheck", help="目标页存活预检")
    s.add_argument("url")
    s.add_argument("--render", action="store_true", help="设备端真实渲染预检(活动页必用)")
    s.add_argument("--pkg", default=None, help="用指定App打开(如 com.jingdong.app.mall)")
    s.add_argument("--wait", type=int, default=10)
    s.set_defaults(func=cmd_precheck)

    s = sub.add_parser("open", help="投递URL打开")
    s.add_argument("url")
    s.set_defaults(func=cmd_open)

    s = sub.add_parser("push", help="推图到相册(证据上传用)")
    s.add_argument("file")
    s.set_defaults(func=cmd_push)

    s = sub.add_parser("journal", help="查看台账")
    s.add_argument("--pending", action="store_true")
    s.add_argument("--tail", type=int, default=10)
    s.set_defaults(func=cmd_journal)

    s = sub.add_parser("ensure", help="依赖App预装检查")
    s.add_argument("text", help="任务标题/要求文本")
    s.set_defaults(func=cmd_ensure)

    s = sub.add_parser("cancel", help="善后: 待提交页取消报名")
    s.add_argument("--keyword", required=True, help="任务标题关键词, 如 京东")
    s.add_argument("--reason", default="", help="取消原因(记入台账)")
    s.set_defaults(func=cmd_cancel)

    s = sub.add_parser("clip", help="读取手机剪贴板")
    s.set_defaults(func=cmd_clip)

    s = sub.add_parser("apply", help="报名当前任务")
    s.set_defaults(func=cmd_apply)

    s = sub.add_parser("upload", help="上传证据截图")
    s.add_argument("--img", default="")
    s.set_defaults(func=cmd_upload)

    s = sub.add_parser("submit", help="填写反馈并提交")
    s.add_argument("--note", default=None)
    s.add_argument("--yes", action="store_true", help="跳过人工确认直接提交")
    s.set_defaults(func=cmd_submit)

    s = sub.add_parser("cleanup", help="任务完成后清理后台")
    s.add_argument("--apps", default=None, help="指定包名, 逗号分隔(默认自动)")
    s.add_argument("--no-recents", action="store_true", help="跳过多任务界面清理")
    s.set_defaults(func=cmd_cleanup)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
