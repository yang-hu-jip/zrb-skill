import time
import uiautomator2 as u2
d = u2.connect()
d.xpath('//*[@text="Allow all cookies"]').click()
time.sleep(5)
print(d.app_current()["activity"])
for e in d.xpath("//*[@text]").all():
    if e.text and e.text.strip():
        print(repr(e.text[:80]))
d.screenshot("k2.png")
