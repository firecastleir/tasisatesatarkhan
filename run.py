import faulthandler, os

# اگر بیش از ۲۳ دقیقه طول کشید، محل گیر کردن را در لاگ چاپ می‌کند و متوقف می‌شود
faulthandler.dump_traceback_later(1380, exit=True)

import main as m

for _p in ("patch.py", "patch2.py"):
    if os.path.exists(_p):
        exec(compile(open(_p, encoding="utf-8").read(), _p, "exec"), m.__dict__)

requests = m.requests
Path = m.Path

_post = requests.post


def _limited_post(url, **kw):
    t = kw.get("timeout")
    if isinstance(t, (int, float)) and t > 200:
        kw["timeout"] = (20, 200)
    return _post(url, **kw)


requests.post = _limited_post


def upload(path, mime, title, alt=""):
    path = Path(path)
    data = path.read_bytes()
    last = None
    for _ in range(2):
        try:
            r = requests.post(f"{m.API}/media", auth=m.AUTH, timeout=(20, 150), data=data,
                              headers={"Content-Disposition": f'attachment; filename="{path.name}"', "Content-Type": mime})
            r.raise_for_status()
            j = r.json()
            requests.post(f"{m.API}/media/{j['id']}", auth=m.AUTH, timeout=(20, 60),
                          json={"title": title, "alt_text": alt, "caption": alt, "description": "AUTO"})
            return j["id"], j["source_url"]
        except Exception as e:
            last = e
            print("upload retry:", path.name, type(e).__name__, flush=True)
    raise last


def tg_call(method, data, files=None):
    try:
        r = requests.post(f"https://api.telegram.org/bot{m.TG_TOKEN}/{method}", data=data, files=files, timeout=(20, 180))
        if not r.ok:
            print("telegram error:", r.status_code, r.text[:200], flush=True)
        return r.ok
    except Exception as e:
        print("telegram failed:", type(e).__name__, flush=True)
        return False


m.upload = upload
m.tg_call = tg_call
m.main()
