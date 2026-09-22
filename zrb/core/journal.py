"""本地台账 journal.jsonl（状态机持久化）

状态机: 未报名 -> 已报名待执行 -> 已执行待提交 -> 已提交待审核
        -> (通过 | 驳回重做 | 放弃 | 预检失败跳过)
"""
import json
import os
import time

JOURNAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "journal.jsonl")


def append(task, status, **extra):
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "task": task, "status": status}
    rec.update(extra)
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def read_all():
    if not os.path.exists(JOURNAL):
        return []
    with open(JOURNAL, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def latest_status(task):
    for r in reversed(read_all()):
        if r["task"] == task:
            return r
    return None


def today_summary():
    today = time.strftime("%Y-%m-%d")
    recs = [r for r in read_all() if r["ts"].startswith(today)]
    stats = {}
    for r in recs:
        stats[r["status"]] = stats.get(r["status"], 0) + 1
    return stats


def pending():
    """返回每个任务的最新状态，筛选出待处理项"""
    seen = {}
    for r in read_all():
        seen[r["task"]] = r
    return [r for r in seen.values()
            if r["status"] in ("已报名待执行", "已执行待提交", "驳回重做")]
