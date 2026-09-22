"""按精确行坐标点同意"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.device import Device

dev = Device()
# 同意行 y≈703 (圆点中心), x 取左侧圆点
dev.d.click(66, 703)
time.sleep(1.5)
dev.screenshot("consent_check2.png")
print("done")
