import faulthandler, glob, os, sys

print("attach.py started", flush=True)
# اگر بیش از ۲.۵ دقیقه طول کشید، متوقف می‌شود (اتصال لینک‌ها چند ثانیه بیشتر طول نمی‌کشد)
faulthandler.dump_traceback_later(150, exit=True)

import main as m

for _p in sorted(glob.glob("patch*.py")):
    exec(compile(open(_p, encoding="utf-8").read(), _p, "exec"), m.__dict__)

m.attach()
