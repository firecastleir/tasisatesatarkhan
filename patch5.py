# patch5.py: دانلود امن فایل‌های کتابخانه (حجم زیاد یا سرور کند دیگر کل اجرا را گیر نمی‌اندازد)
import time as _time

_old_make_videos5 = make_videos
_DL = {"spent": 0.0}
_VIDEO_EXT = (".mp4", ".mov", ".webm", ".mkv", ".m4v")


def download(url, path, *_a, **_k):
    path = Path(path)
    limit = (80 if str(path).lower().endswith(_VIDEO_EXT) else 20) * 1024 * 1024
    if _DL["spent"] > 360:
        raise RuntimeError("download budget exceeded")
    start = _time.time()
    try:
        with requests.get(url, stream=True, timeout=(15, 30)) as r:
            r.raise_for_status()
            cl = r.headers.get("Content-Length")
            if cl and cl.isdigit() and int(cl) > limit:
                raise RuntimeError(f"file too large ({int(cl) // 1048576} MB)")
            n = 0
            with open(path, "wb") as f:
                for chunk in r.iter_content(262144):
                    f.write(chunk)
                    n += len(chunk)
                    el = _time.time() - start
                    if n > limit:
                        raise RuntimeError("file too large")
                    if el > 150 or (el > 20 and n / el < 100 * 1024):
                        raise RuntimeError("download too slow")
    except Exception:
        try:
            path.unlink()
        except Exception:
            pass
        raise
    finally:
        _DL["spent"] += _time.time() - start


def make_videos(art, sentences, scene_ids, lib_by_id, work):
    _DL["spent"] = 0.0
    return _old_make_videos5(art, sentences, scene_ids, lib_by_id, work)
