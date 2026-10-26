# patch.py: اصلاح‌های تلگرام، وب‌استوری و کادر ویدیو (روی main.py قبلی اعمال می‌شود)
import re, requests

PLACEHOLDER = (
    '<!-- wp:html -->\n<div style="border:2px dashed #e0a800;padding:16px;margin:0 0 22px;text-align:center;'
    'background:#fff8e1;color:#5c4400;font-weight:bold">📹 جای ویدیوهای آپارات و یوتیوب. بعد از آپلود، مرحله attach-video را در GitHub اجرا کنید تا این کادر خودکار با ویدیوها پر شود.</div>\n<!-- /wp:html -->\n')


def tg_pick_chat():
    """اگر شناسه چت اشتباه بود، آخرین گفتگوی خصوصی شما با ربات را پیدا می‌کند."""
    try:
        r = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates", timeout=60)
        for u in reversed(r.json().get("result", [])):
            msg = u.get("message") or u.get("edited_message") or {}
            ch = msg.get("chat") or {}
            if ch.get("type") == "private" and not (msg.get("from") or {}).get("is_bot"):
                return str(ch["id"])
    except Exception as e:
        print("telegram getUpdates failed:", type(e).__name__)
    return ""


def send_to_telegram(art, article_url, vv, vh, post_id=0):
    if not (TG_TOKEN and TG_CHAT):
        print("telegram not configured: videos saved only as backup artifact")
        return False
    tags = " ".join("#" + re.sub(r"\s+", "_", str(t).strip().lstrip("#")) for t in (art.get("hashtags") or [])[:8])
    msg = (f"📹 ویدیوی امروز {BRAND}\n\nعنوان ویدیو:\n{art.get('video_title') or art['title']}\n\n"
           f"توضیحات ویدیو:\n{art.get('video_description', '')}\n\n{tags}\n\nلینک مقاله برای گذاشتن زیر ویدیو: {article_url}\nشناسه مقاله (برای مرحله آخر): {post_id}")
    chat = TG_CHAT
    if not tg_call("sendMessage", {"chat_id": chat, "text": msg[:4000]}):
        alt = tg_pick_chat()
        if not alt:
            print("telegram: شناسه چت اشتباه است. در تلگرام به ربات خودتان یک پیام بدهید و دوباره اجرا کنید.")
            return False
        print(f"telegram: شناسه چت اشتباه بود. شناسه درست شما این عدد است: {alt} (آن را در TELEGRAM_CHAT_ID بگذارید)")
        chat = alt
        if not tg_call("sendMessage", {"chat_id": chat, "text": msg[:4000]}):
            return False
    ok = True
    for label, p in (("ویدیوی افقی: برای آپارات و داخل مقاله", vh), ("ویدیوی عمودی: برای یوتیوب Shorts", vv)):
        try:
            p = fit_for_telegram(p)
            with open(p, "rb") as f:
                ok = tg_call("sendVideo", {"chat_id": chat, "caption": label, "supports_streaming": "true"},
                             {"video": f}) and ok
        except Exception as e:
            print("telegram video failed:", type(e).__name__)
            ok = False
    return ok


def _uid():
    import uuid
    return str(uuid.uuid4())


def story_data_json(pages):
    """ساختار داده‌ی ویرایشگر Web Stories (افزونه هر دو را با هم می‌خواهد)."""
    white = {"color": {"r": 255, "g": 255, "b": 255}}
    out = []
    for url, alt, mid in pages:
        out.append({"id": _uid(), "type": "page", "backgroundColor": white, "elements": [
            {"id": _uid(), "type": "shape", "x": 1, "y": 1, "width": 1, "height": 1, "scale": 100, "focalX": 50, "focalY": 50,
             "mask": {"type": "rectangle"}, "flip": {"vertical": False, "horizontal": False},
             "isBackground": True, "isDefaultBackground": True, "backgroundColor": white},
            {"id": _uid(), "type": "image", "x": 0, "y": 0, "width": 412, "height": 732, "rotationAngle": 0,
             "scale": 100, "focalX": 50, "focalY": 50, "mask": {"type": "rectangle"},
             "flip": {"vertical": False, "horizontal": False},
             "resource": {"type": "image", "mimeType": "image/jpeg", "id": mid, "src": url, "width": 1080,
                          "height": 1920, "alt": alt, "isPlaceholder": False, "sizes": {}}}]})
    return {"version": 50, "pages": out, "autoAdvance": True, "defaultPageDuration": 6,
            "currentStoryStyles": {"colors": [], "textStyles": []}}


def create_web_story(work, art, slides, story_ids, lib_by_id, article_url, base="article"):
    """وب‌استوری را به صورت پیش‌نویس می‌سازد (نیاز به افزونه Web Stories)."""
    pages, n = [], min(len(slides), 6)
    for i in range(n):
        sl = slides[i]
        photo = None
        item = lib_by_id.get(story_ids[i]) if i < len(story_ids) and story_ids[i] else None
        if item and item["type"] == "image":
            try:
                photo = f"storybg_{i}.jpg"
                download(item["large"], work / photo)
            except Exception:
                photo = None
        name = f"{base}-story-{i + 1}.jpg"
        render_still(work, 1080, 1920, photo, sl.get("title", ""), sl.get("points", []), name, step=f"{fa(i + 1)} / {fa(n)}")
        mid, url = upload(work / name, "image/jpeg", f"{art['title']} - {i + 1}", sl.get("title", art["title"]))
        pages.append((url, sl.get("title", art["title"]), mid))
    render_still(work, 1080, 1920, None, BRAND, [f"تلفن: {PHONE}", f"موبایل: {MOBILE}", SITE_SHORT], f"{base}-story-contact.jpg")
    mid, url = upload(work / f"{base}-story-contact.jpg", "image/jpeg", f"{art['title']} - تماس", BRAND)
    pages.append((url, f"تماس با {BRAND}", mid))
    render_still(work, 960, 1280, None, art["title"], [], f"{base}-story-poster.jpg")
    pid, poster_url = upload(work / f"{base}-story-poster.jpg", "image/jpeg", art["title"], art["title"])
    logo_url = ""
    try:
        logo_url = requests.get(f"{SITE}/wp-json/", timeout=30).json().get("site_icon_url") or ""
    except Exception:
        pass
    if not logo_url:
        render_still(work, 512, 512, None, BRAND, [], f"{base}-logo.jpg")
        _, logo_url = upload(work / f"{base}-logo.jpg", "image/jpeg", BRAND, BRAND)
    content = story_html(art["title"], poster_url, logo_url, [(u, a) for u, a, _ in pages], article_url)
    payload = {"title": art["title"], "status": "draft", "content": content,
               "story_data": story_data_json(pages), "featured_media": pid}
    for ep in (f"{SITE}/wp-json/web-stories/v1/web-story", f"{API}/web-story"):
        r = requests.post(ep, auth=AUTH, json=payload, timeout=120)
        print("web story:", ep.split("/wp-json/")[1], r.status_code, "ok" if r.ok else r.text[:200])
        if r.ok:
            return True
    return False
