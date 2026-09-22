import uiautomator2 as u2

d = u2.connect()
# 切到 AdbKeyboard 输入法后读取剪贴板
try:
    d.set_input_ime(True)
    print("clipboard:", repr(d.clipboard))
except Exception as e:
    print("err:", e)
try:
    print("broadcast:", d.shell("am broadcast -a ADB_GET_CLIPBOARD"))
except Exception as e:
    print("err2:", e)
