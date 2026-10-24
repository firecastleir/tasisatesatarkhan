import os, asyncio, json, random, re, subprocess, sys, tempfile, datetime, html
from pathlib import Path

import requests
import edge_tts

# ======================= تنظیمات سایت =======================
SITE = os.environ.get("WP_SITE", "https://tasisatesatarkhan.ir").rstrip("/")
WP_USER = os.environ["WP_USER"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "")
# draft = پیش‌نویس (برای بازبینی) | publish = انتشار مستقیم
POST_STATUS = os.environ.get("POST_STATUS", "draft")

BRAND = "تاسیسات ستارخان"
SITE_SHORT = "tasisatesatarkhan.ir"
PHONE = "02144278518"
MOBILE = "09031413301"
OFFICE = "تهران، خیابان ستارخان، بازار سنتی ستارخان، چهارسوق دوم، قلمستان، پلاک ۴/۳۳۳"
LICENSE = "20692995"

BUSINESS = (
    "تاسیسات ستارخان در تهران خدمات فنی ساختمان ارائه می‌دهد: سرویس، تعمیر و نصب تاسیسات (پکیج، شوفاژ، رادیاتور، "
    "موتورخانه مرکزی، هواساز، اسپلیت، داکت اسپلیت، گرمایش از کف، چیلر)، نصب و تعمیر سرویس بهداشتی (والهنگ، توالت فرنگی، "
    "فلاش تانک توکار و معمولی، شیرآلات توکار، وان، جکوزی، جت شاور، اتاق دوش)، لوله‌کشی آب سرد و گرم (فلزی و لوله سفید)، "
    "لوله‌کشی فاضلاب و گاز، تامین و نگهداری موتورخانه مرکزی ساختمان‌ها، بازسازی توالت و حمام و ساختمان، اجرای خدمات فنی "
    "ساختمان، ساخت و تعمیر و نصب نرده استیل، آهنی و چوبی."
)

CAT_HEAT = "گرمایش و سرمایش"
CAT_PIPE = "لوله‌کشی ساختمان"
CAT_BATH = "سرویس بهداشتی و حمام"
CAT_ENGINE = "موتورخانه"
CAT_RENO = "بازسازی ساختمان"
CAT_RAIL = "نرده و سرپله"


def T(title, cat, kw):
    return {"title": title, "cat": cat, "kw": kw}


TOPICS = [
    T("دلایل خاموش شدن پکیج دیواری و راه‌حل‌های آن", CAT_HEAT, "خاموش شدن پکیج"),
    T("ارورهای رایج پکیج و معنی آن‌ها", CAT_HEAT, "ارور پکیج"),
    T("افت فشار آب پکیج: علت‌ها و روش رفع", CAT_HEAT, "افت فشار پکیج"),
    T("سرویس سالانه پکیج شامل چه مراحلی است", CAT_HEAT, "سرویس پکیج"),
    T("راهنمای انتخاب پکیج مناسب برای آپارتمان", CAT_HEAT, "انتخاب پکیج"),
    T("پکیج کندانسینگ چیست و چه تفاوتی با پکیج معمولی دارد", CAT_HEAT, "پکیج کندانسینگ"),
    T("هواگیری رادیاتور به روش اصولی", CAT_HEAT, "هواگیری رادیاتور"),
    T("رادیاتور گرم نمی‌شود: علت‌ها و راه‌حل", CAT_HEAT, "رادیاتور گرم نمی‌شود"),
    T("شستشوی شوفاژ و رادیاتور: چه زمانی و چگونه", CAT_HEAT, "شستشوی رادیاتور"),
    T("محاسبه تعداد پره رادیاتور برای هر اتاق", CAT_HEAT, "محاسبه تعداد پره رادیاتور"),
    T("بالانس هیدرولیکی سیستم گرمایش چیست", CAT_HEAT, "بالانس سیستم گرمایش"),
    T("گرمایش از کف چیست؟ مزایا، معایب و محدودیت‌ها", CAT_HEAT, "گرمایش از کف"),
    T("مراحل اجرای گرمایش از کف در ساختمان", CAT_HEAT, "اجرای گرمایش از کف"),
    T("مشکلات رایج گرمایش از کف و تشخیص آن‌ها", CAT_HEAT, "مشکلات گرمایش از کف"),
    T("اصول نصب صحیح اسپلیت", CAT_HEAT, "نصب اسپلیت"),
    T("دلایل آب ریختن اسپلیت و روش رفع", CAT_HEAT, "آب ریختن اسپلیت"),
    T("سرویس و شستشوی اسپلیت: چه زمانی لازم است", CAT_HEAT, "سرویس اسپلیت"),
    T("داکت اسپلیت چیست و چه تفاوتی با اسپلیت دیواری دارد", CAT_HEAT, "داکت اسپلیت"),
    T("چیلر چیست؟ انواع چیلر تراکمی و جذبی", CAT_HEAT, "چیلر"),
    T("سرویس دوره‌ای چیلر و نکات نگهداری", CAT_HEAT, "سرویس چیلر"),
    T("هواساز چیست و در چه ساختمان‌هایی استفاده می‌شود", CAT_HEAT, "هواساز"),
    T("موتورخانه مرکزی ساختمان: اجزا و نحوه کار", CAT_ENGINE, "موتورخانه مرکزی"),
    T("نگهداری و بهره‌برداری صحیح از موتورخانه مرکزی", CAT_ENGINE, "نگهداری موتورخانه"),
    T("پمپ‌های موتورخانه و نشانه‌های خرابی آن‌ها", CAT_ENGINE, "پمپ موتورخانه"),
    T("دیگ آب گرم و مشعل: آشنایی و عیب‌یابی رایج", CAT_ENGINE, "دیگ و مشعل موتورخانه"),
    T("لوله‌کشی آب سرد و گرم: لوله فلزی یا لوله سفید؟", CAT_PIPE, "لوله‌کشی آب سرد و گرم"),
    T("اصول لوله‌کشی ساختمان با لوله سفید", CAT_PIPE, "لوله‌کشی با لوله سفید"),
    T("تشخیص و رفع نشتی لوله آب در ساختمان", CAT_PIPE, "نشتی لوله آب"),
    T("لوله‌کشی فاضلاب ساختمان: شیب، هواکش و اشتباهات رایج", CAT_PIPE, "لوله‌کشی فاضلاب"),
    T("لوله‌کشی گاز ساختمان: نکات ایمنی و الزامات", CAT_PIPE, "لوله‌کشی گاز ساختمان"),
    T("مراحل نصب توالت فرنگی به صورت اصولی", CAT_BATH, "نصب توالت فرنگی"),
    T("فلاش تانک توکار چیست؟ مزایا و نکات نصب", CAT_BATH, "فلاش تانک توکار"),
    T("تعمیر فلاش تانک: هرز رفتن آب و نشتی", CAT_BATH, "تعمیر فلاش تانک"),
    T("نصب و تعمیر شیرآلات توکار", CAT_BATH, "شیرآلات توکار"),
    T("نصب وان و جکوزی: نکات فنی مهم", CAT_BATH, "نصب وان و جکوزی"),
    T("اتاق دوش و جت شاور: انتخاب و نصب", CAT_BATH, "نصب اتاق دوش"),
    T("والهنگ چیست و نکات نصب آن", CAT_BATH, "والهنگ"),
    T("مراحل بازسازی حمام و توالت از ابتدا تا انتها", CAT_RENO, "بازسازی حمام و توالت"),
    T("چک‌لیست تاسیسات هنگام بازسازی ساختمان", CAT_RENO, "تاسیسات بازسازی ساختمان"),
    T("نرده استیل برای پله و بالکن: انواع و نکات انتخاب", CAT_RAIL, "نرده استیل"),
    T("نرده آهنی یا چوبی؟ مقایسه و راهنمای انتخاب", CAT_RAIL, "نرده آهنی و چوبی"),
    T("نگهداری از نرده استیل و جلوگیری از لکه و زنگ‌زدگی", CAT_RAIL, "نگهداری نرده استیل"),
]

# ============================================================

AUTH = (WP_USER, WP_APP_PASSWORD)
API = f"{SITE}/wp-json/wp/v2"
HERE = Path(__file__).parent
STATE_FILE = HERE / "state.json"
COPPER_ASS = "&H00B5701A"  # آبی تیره (BGR)


# ---------------------------------------------------------------- helpers
def load_state():
    if not STATE_FILE.exists():
        return {"done": [], "used_images": []}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(s):
    STATE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2000:])
        raise RuntimeError("command failed: " + " ".join(map(str, cmd[:3])))
    return r.stdout


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "csv=p=0", str(path)]).strip())


_MODELS = None
_ALL = None


def list_models():
    global _ALL
    if _ALL is None:
        _ALL = []
        try:
            r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                             params={"key": GEMINI_API_KEY, "pageSize": 200}, timeout=60)
            r.raise_for_status()
            for m in r.json().get("models", []):
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    _ALL.append(m["name"].split("/")[-1])
        except Exception as e:
            print("model list failed:", e)
    return _ALL


def candidate_models():
    """مدل‌های فعال را از خود گوگل می‌پرسد تا به اسم مدل وابسته نباشیم."""
    global _MODELS
    if _MODELS is not None:
        return _MODELS
    names = [n for n in list_models() if "flash" in n and not any(
        x in n for x in ("image", "tts", "live", "audio", "thinking", "robotics", "computer", "embed", "native"))]

    def ver(n):
        m = re.search(r"(\d+(?:\.\d+)?)", n)
        return (float(m.group(1)) if m else 0, "lite" not in n, "preview" not in n)

    names.sort(key=ver, reverse=True)
    pref = [GEMINI_MODEL] if os.environ.get("GEMINI_MODEL") else []
    _MODELS = pref + [n for n in names if n not in pref] + (["gemini-flash-latest"] if "gemini-flash-latest" not in names else [])
    print("models to try:", _MODELS[:6])
    return _MODELS


def gemini(prompt, retries=2):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.6, "maxOutputTokens": 30000, "responseMimeType": "application/json"}}
    for model in candidate_models()[:6]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for i in range(retries):
            try:
                r = requests.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=240)
                if r.status_code in (404, 400):
                    print("model unavailable:", model, r.status_code)
                    break
                if r.status_code == 429:
                    print("quota/rate limit on", model, "- waiting")
                    time.sleep(30)
                    continue
                r.raise_for_status()
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
                print("using model:", model)
                return json.loads(text)
            except Exception as e:
                print("gemini retry", model, i, str(e)[:200])
                time.sleep(8)
    raise RuntimeError("Gemini failed with all models")


import time


# ---------------------------------------------------------------- topic
def pick_topic(state):
    topics = list(TOPICS) + state.get("extra_topics", [])
    left = [t for t in topics if t["title"] not in state["done"]]
    if not left:
        print("topic list exhausted -> asking Gemini for new topics")
        cats = [CAT_HEAT, CAT_PIPE, CAT_BATH, CAT_ENGINE, CAT_RENO, CAT_RAIL]
        new = gemini(f"""برای وبلاگ فنی سایت «{BRAND}» ({BUSINESS})
۱۰ موضوع جدید مقاله فنی و سئو شده بنویس که با این عناوین تکراری نباشد:
{json.dumps(state['done'][-80:], ensure_ascii=False)}
فقط JSON: لیستی از اشیاء با کلیدهای title, cat (یکی از: {', '.join(cats)}), kw (کلمه کلیدی اصلی فارسی)""")
        state.setdefault("extra_topics", []).extend(new)
        left = new
    return left[0]


# ---------------------------------------------------------------- article
def recent_posts():
    try:
        r = requests.get(f"{API}/posts", params={"per_page": 20, "status": "publish", "_fields": "title,link"}, timeout=60)
        return [{"title": p["title"]["rendered"], "url": p["link"]} for p in r.json()]
    except Exception:
        return []


def write_article(topic):
    internal = recent_posts()
    prompt = f"""تو سردبیر فنی و متخصص سئوی فارسی هستی و برای سایت «{BRAND}» ({SITE}) مقاله می‌نویسی.
درباره کسب‌وکار: {BUSINESS}
موضوع مقاله: «{topic['title']}»
کلمه کلیدی اصلی: «{topic['kw']}»

هدف: مقاله‌ای جامع، فوق‌العاده فنی، کاربردی و روان که از رقبای صفحه اول گوگل کامل‌تر و مفیدتر باشد، برای کاربر ایرانی (مالک ساختمان، مدیر ساختمان، مستأجر) و تا حدی برای تکنسین‌ها.

قوانین محتوا:
- فارسی روان و استاندارد ایران، لحن حرفه‌ای، دقیق و قابل فهم. حدود ۲۲۰۰ تا ۲۸۰۰ کلمه.
- دقت فنی در اولویت است. هیچ عدد، قیمت، مشخصات، استاندارد یا ادعای ساختگی ننویس. اگر از عددی مطمئن نیستی، توصیف کلی یا بازه‌ی منطقی بدون ادعای دقیق بنویس. فقط اگر کاملاً مطمئنی به مقررات ملی ساختمان (مثلاً مبحث ۱۴ تاسیسات مکانیکی، مبحث ۱۶ تاسیسات بهداشتی، مبحث ۱۷ لوله‌کشی گاز طبیعی) اشاره کن.
- ساختار پیشنهادی: مقدمه کوتاه با کلمه کلیدی، پاسخ سریع به سوال اصلی، توضیح فنی اصول کار، انواع و مقایسه (حتماً حداقل یک جدول HTML با table)، مراحل گام‌به‌گام، علائم خرابی و عیب‌یابی، اشتباهات رایج، نکات ایمنی، هزینه و عوامل موثر بر آن (بدون قیمت دقیق)، چه زمانی باید تکنسین مجاز خبر کرد، نتیجه‌گیری.
- از h2 و h3، لیست‌های ul و ol، جدول، و در صورت نیاز تگ strong استفاده کن. تگ h1 نگذار.
- ایمنی (گاز، برق، آب داغ، فشار، ارتفاع) را شفاف و محتاطانه بنویس. کارهای حساس گازی و موتورخانه را به متخصص مجاز ارجاع بده، نه آموزش خودسرانه.
- کلمه کلیدی در عنوان، پاراگراف اول، حداقل دو تیتر h2 و نتیجه‌گیری بیاید (طبیعی، بدون پرکردن).
- ادعای تجربه یا آمار جعلی نیاور (مثلاً «ما ۲۰ سال سابقه داریم»)، فقط از «تیم فنی {BRAND}» به صورت کلی استفاده کن.
- در انتها دعوت به مشاوره با {BRAND} بیاور (بدون شماره تلفن؛ شماره را سیستم اضافه می‌کند).
- ۲ تا ۳ لینک داخلی فقط از این فهرست و فقط اگر مرتبط‌اند، با تگ a: {json.dumps(internal, ensure_ascii=False)}
- متن روایت ویدیو (narration): ۱۳۰ تا ۱۶۰ کلمه، حداکثر ۷ جمله، گفتاری، طبیعی و فنی ولی ساده برای گوینده، هر جمله حداکثر ۲۰ کلمه و با نقطه تمام‌شونده. برای خوانده‌شدن درست توسط موتور تبدیل متن به گفتار: همه عددها را با حروف بنویس، هیچ کلمه انگلیسی، مخفف، علامت و ایموجی نیاور، از کلمه‌های ساده و رایج فارسی معیار و املای استاندارد با نیم‌فاصله درست استفاده کن. بدون آدرس سایت و شماره. شروع جذاب و پایان با دعوت به مشاوره با {BRAND}.
- scene_queries: به تعداد جمله‌های narration (به ترتیب)، هر کدام یک عبارت کوتاه انگلیسی (۲ تا ۴ کلمه) برای جستجوی فیلم استوک مرتبط با همان جمله، مثل: plumber repairing pipe, boiler maintenance, radiator heating, air conditioner installation. بدون نام برند.

فقط JSON با این کلیدها:
title (حداکثر ۶۰ کاراکتر، شامل کلمه کلیدی), slug (انگلیسی کوچک با خط تیره), meta_description (۱۲۰ تا ۱۵۵ کاراکتر شامل کلمه کلیدی),
tags (۳ تا ۵ برچسب فارسی), article_html, faq (لیست ۶ شیء با q و a، پاسخ‌های دقیق و کامل در ۲ تا ۴ جمله), narration, scene_queries, image_keywords (۳ عبارت انگلیسی برای جستجوی عکس), image_alt (متن جایگزین فارسی عکس شاخص)"""
    art = gemini(prompt)
    return review_article(art, topic)


def review_article(art, topic):
    """یک دور بازبینی فنی: اشتباهات، اعداد مشکوک و توصیه‌های ناایمن را اصلاح می‌کند."""
    if os.environ.get("REVIEW_PASS", "1") == "0":
        return art
    old = art.get("article_html", "")
    prompt = f"""تو بازبین فنی ارشد تاسیسات و ساختمان هستی. مقاله HTML زیر درباره «{topic['title']}» است.
آن را با دقت بخوان و هر ادعای فنی نادرست یا مشکوک، عدد یا استاندارد بی‌پشتوانه، توصیه ناایمن (به‌ویژه گاز و برق) و اغراق را اصلاح یا حذف کن.
جزئیات مفید را کم نکن. ساختار HTML، تیترها و جدول‌ها را حفظ کن و طول را کم‌تر از ۹۰ درصد نکن.
فقط JSON با کلیدهای article_html (متن اصلاح‌شده کامل) و changes (فهرست کوتاه تغییرات).

{old}"""
    try:
        r = gemini(prompt, retries=1)
        new = r.get("article_html", "")
        if len(new) >= 0.7 * len(old):
            art["article_html"] = new
            print("review changes:", r.get("changes", [])[:8])
    except Exception as e:
        print("review pass skipped:", str(e)[:200])
    return art


# ---------------------------------------------------------------- images
def wp_images():
    out = []
    try:
        r = requests.get(f"{API}/media", params={"per_page": 100, "media_type": "image",
                                                 "_fields": "id,source_url,media_details"}, auth=AUTH, timeout=60)
        for m in r.json():
            d = m.get("media_details") or {}
            if d.get("width", 0) >= 800:
                out.append({"id": m["id"], "url": m["source_url"]})
    except Exception as e:
        print("media list failed", e)
    return out


def pixabay_photos(query, n=2):
    if not PIXABAY_API_KEY:
        return []
    try:
        r = requests.get("https://pixabay.com/api/", params={
            "key": PIXABAY_API_KEY, "q": query[:100], "image_type": "photo", "orientation": "horizontal",
            "min_width": 1280, "safesearch": "true", "per_page": 12}, timeout=60)
        hits = r.json().get("hits", [])
        random.shuffle(hits)
        return [{"id": None, "url": h["largeImageURL"]} for h in hits[:n]]
    except Exception as e:
        print("pixabay photo failed:", str(e)[:150])
        return []


def pick_images(n, keywords, state):
    lib = wp_images()
    used = set(state.get("used_images", []))
    fresh = [i for i in lib if i["id"] not in used]
    random.shuffle(fresh)
    random.shuffle(lib)
    chosen = (fresh + [i for i in lib if i not in fresh])[:n]
    if len(chosen) < n:
        for k in keywords:
            chosen += pixabay_photos(k)
    if not chosen:
        raise RuntimeError("no images available (upload photos to the media library or set PIXABAY_API_KEY)")
    while len(chosen) < n:
        chosen.append(chosen[len(chosen) % len(chosen)])
    return chosen[:n]


def download(url, path):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    Path(path).write_bytes(r.content)


# ---------------------------------------------------------------- video
def split_sentences(text, max_parts=7):
    parts = [p.strip() for p in re.split(r"(?<=[.!؟?…])\s+", text.strip()) if p.strip()]
    merged = []
    for p in parts:
        if merged and len(merged[-1]) < 40:
            merged[-1] += " " + p
        else:
            merged.append(p)
    while len(merged) > max_parts:
        i = min(range(len(merged) - 1), key=lambda k: len(merged[k]) + len(merged[k + 1]))
        merged[i:i + 2] = [merged[i] + " " + merged[i + 1]]
    return merged


EDGE_VOICE = os.environ.get("EDGE_VOICE", "fa-IR-DilaraNeural")  # صدای زن
EDGE_RATE = os.environ.get("EDGE_RATE", "-8%")
GEMINI_TTS_VOICE = os.environ.get("GEMINI_TTS_VOICE", "Aoede")  # صدای زن طبیعی‌تر


async def tts(text, path):
    await edge_tts.Communicate(text, EDGE_VOICE, rate=EDGE_RATE).save(str(path))


def gemini_tts(text, pcm_path, wav_path):
    """صدای طبیعی‌تر با Gemini TTS. اگر خطا داد، برنامه خودش به edge-tts برمی‌گردد."""
    import base64
    models = [n for n in list_models() if "tts" in n]
    if not models:
        raise RuntimeError("no gemini tts model available")
    prompt = ("Read aloud in Persian (Iran, standard Tehran accent), in a warm, natural, friendly "
              "female narrator voice, at a calm medium pace, with natural pauses. Text:\n" + text)
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": GEMINI_TTS_VOICE}}}}}
    last = None
    for model in models[:3]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(3):
            try:
                r = requests.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=240)
                if r.status_code == 429:
                    print("tts rate limit, waiting")
                    time.sleep(45)
                    continue
                r.raise_for_status()
                part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
                rate = 24000
                m = re.search(r"rate=(\d+)", part.get("mimeType", ""))
                if m:
                    rate = int(m.group(1))
                Path(pcm_path).write_bytes(base64.b64decode(part["data"]))
                run(["ffmpeg", "-y", "-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", str(pcm_path),
                     "-ar", "44100", "-ac", "1", "-af", "apad=pad_dur=0.35", str(wav_path)])
                return
            except Exception as e:
                last = e
                print("gemini tts retry", model, attempt, str(e)[:200])
                time.sleep(6)
    raise RuntimeError(f"gemini tts failed: {last}")


def synth_all(sentences, work):
    segments = []
    if os.environ.get("USE_GEMINI_TTS", "1") != "0":
        try:
            for i, s in enumerate(sentences):
                wav = work / f"a{i}.wav"
                gemini_tts(s, work / f"a{i}.pcm", wav)
                segments.append((s, wav.name, duration(wav)))
                time.sleep(3)
            print("voice: gemini tts")
            return segments
        except Exception as e:
            print("gemini tts failed, falling back to edge-tts:", str(e)[:300])
            segments = []
    for i, s in enumerate(sentences):
        mp3, wav = work / f"a{i}.mp3", work / f"a{i}.wav"
        asyncio.run(tts(s, mp3))
        run(["ffmpeg", "-y", "-i", str(mp3), "-ar", "44100", "-ac", "1", "-af", "apad=pad_dur=0.35", str(wav)])
        segments.append((s, wav.name, duration(wav)))
    print("voice: edge-tts", EDGE_VOICE)
    return segments


def ass_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def make_ass(segments, W, H, path, title=""):
    vertical = H > W
    size = 62 if vertical else 50
    marginv = 420 if vertical else 70
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Sub,Vazirmatn,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,3,3,0,2,90,90,{marginv},1
Style: Mark,Vazirmatn,{int(size*0.55)},{COPPER_ASS},&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,8,40,40,{80 if vertical else 40},1
Style: Card,Vazirmatn,{int(size*1.1)},&H00FFFFFF,&H00FFFFFF,{COPPER_ASS},&H00000000,1,0,0,0,100,100,0,0,3,10,0,5,100,100,40,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Encoding_unused,Text
"""
    head = head.replace("Encoding_unused", "Effect")
    total = sum(d for _, _, d in segments)
    lines = [f"Dialogue: 1,{ass_time(0)},{ass_time(total)},Mark,,0,0,0,,{BRAND}  |  {SITE_SHORT}"]
    t = 0.0
    for text, _, d in segments:
        lines.append(f"Dialogue: 0,{ass_time(t)},{ass_time(t + d)},Sub,,0,0,0,,{text}")
        t += d
    clean = re.sub(r"[{}\\]", "", title)
    if clean:
        lines.append(f"Dialogue: 2,{ass_time(0.2)},{ass_time(min(3.6, total))},Card,,0,0,0,,{clean}")
    if total > 8:
        lines.append(f"Dialogue: 2,{ass_time(total - 4.2)},{ass_time(total)},Card,,0,0,0,,{BRAND}\\Nتماس: {PHONE}")
    Path(path).write_text(head + "\n".join(lines), encoding="utf-8")


def stock_video(query, W, H, work, name, used):
    """یک فیلم استوک مرتبط از Pixabay می‌گیرد. اگر نشد None برمی‌گرداند."""
    if not PIXABAY_API_KEY or not query:
        return None
    short = " ".join(query.split()[:2])
    for q in dict.fromkeys([query, short]):
        try:
            r = requests.get("https://pixabay.com/api/videos/", params={
                "key": PIXABAY_API_KEY, "q": q[:100], "video_type": "film", "safesearch": "true",
                "min_width": 1280, "per_page": 12}, timeout=60)
            hits = [h for h in r.json().get("hits", []) if h["id"] not in used]
            random.shuffle(hits)
            for h in hits[:3]:
                vs = h.get("videos", {})
                for size in ("large", "medium"):
                    v = vs.get(size) or {}
                    if v.get("url") and (v.get("width") or 0) >= 1280:
                        path = work / f"{name}.mp4"
                        download(v["url"], path)
                        used.add(h["id"])
                        return path.name
        except Exception as e:
            print("pixabay video failed:", q, str(e)[:150])
    return None


def build_video(work, segments, sources, W, H, out_name, title=""):
    clips = []
    for i, ((text, wav, d), (kind, src)) in enumerate(zip(segments, sources)):
        out = f"seg_{out_name}_{i}.mp4"
        if kind == "vid":
            vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,format=yuv420p"
            run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", src, "-t", f"{d:.2f}", "-vf", vf, "-an",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", out], cwd=work)
        else:
            frames = int(d * 30) + 2
            sw, sh = int(W * 1.5) // 2 * 2, int(H * 1.5) // 2 * 2
            direction = "min(zoom+0.0007,1.12)" if i % 2 == 0 else "if(eq(on,1),1.12,max(zoom-0.0007,1.0))"
            vf = (f"scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh},"
                  f"zoompan=z='{direction}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=30,format=yuv420p")
            run(["ffmpeg", "-y", "-i", src, "-vf", vf, "-t", f"{d:.2f}", "-r", "30", "-c:v", "libx264",
                 "-preset", "veryfast", "-crf", "24", out], cwd=work)
        clips.append(out)
    (work / f"list_{out_name}.txt").write_text("".join(f"file '{c}'\n" for c in clips))
    make_ass(segments, W, H, work / f"sub_{out_name}.ass", title)
    final = f"{out_name}.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"list_{out_name}.txt", "-i", "audio.wav",
         "-vf", f"ass=sub_{out_name}.ass", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", final], cwd=work)
    return work / final


def make_videos(art, image_infos, work):
    narration = art["narration"]
    sentences = split_sentences(narration)
    segments = synth_all(sentences, work)
    (work / "alist.txt").write_text("".join(f"file '{w}'\n" for _, w, _ in segments))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "alist.txt", "-c", "copy", "audio.wav"], cwd=work)
    imgs = []
    for i, info in enumerate(image_infos[:len(segments)]):
        p = f"img{i}.jpg"
        download(info["url"], work / p)
        imgs.append(p)
    queries = list(art.get("scene_queries") or []) + list(art.get("image_keywords") or [])
    results = []
    for name, W, H in (("vertical", 1080, 1920), ("horizontal", 1920, 1080)):
        used, sources = set(), []
        for i in range(len(segments)):
            q = queries[i] if i < len(queries) else (queries[i % len(queries)] if queries else "")
            clip = stock_video(q, W, H, work, f"clip_{name}_{i}", used)
            sources.append(("vid", clip) if clip else ("img", imgs[i % len(imgs)]))
        print(name, "scenes:", [k for k, _ in sources])
        results.append(build_video(work, segments, sources, W, H, name, art["title"]))
    return tuple(results)


# ---------------------------------------------------------------- wordpress
def upload(path, mime, title, alt=""):
    path = Path(path)
    r = requests.post(f"{API}/media", auth=AUTH, timeout=900,
                      headers={"Content-Disposition": f'attachment; filename="{path.name}"', "Content-Type": mime},
                      data=path.read_bytes())
    r.raise_for_status()
    j = r.json()
    requests.post(f"{API}/media/{j['id']}", auth=AUTH, json={"title": title, "alt_text": alt}, timeout=60)
    return j["id"], j["source_url"]


def term(kind, name):
    r = requests.get(f"{API}/{kind}", params={"search": name, "per_page": 50}, auth=AUTH, timeout=60).json()
    for t in r:
        if t["name"] == name:
            return t["id"]
    r = requests.post(f"{API}/{kind}", json={"name": name}, auth=AUTH, timeout=60)
    return r.json()["id"] if r.ok else None


def build_content(art, topic, videos, poster, internal_video_title):
    h = ""
    vids = [v for v in videos if v]
    if vids:
        h += "<h2>ویدیوی کوتاه این مقاله</h2>\n"
        for label, url in vids:
            h += (f'<figure class="wp-block-video"><video controls preload="metadata" playsinline '
                  f'poster="{poster}" src="{url}"></video></figure>\n')
    h += art["article_html"]
    if art.get("faq"):
        h += "<h2>سوالات متداول</h2>\n"
        for f in art["faq"]:
            h += f"<h3>{html.escape(f['q'])}</h3>\n<p>{html.escape(f['a'])}</p>\n"
    h += f"""
<div style="border:2px solid #1a6fb5;border-radius:12px;padding:18px;margin-top:30px;background:#f2f8ff">
<h3>مشاوره و سفارش از {BRAND}</h3>
<p>تلفن: <a href="tel:{PHONE}">{PHONE}</a> | موبایل: <a href="tel:{MOBILE}">{MOBILE}</a></p>
<p>آدرس دفتر: {OFFICE}</p>
<p>شماره جواز کسب: {LICENSE}</p>
</div>"""
    ld = []
    if art.get("faq"):
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in art["faq"]]})
    for label, url in vids[:1]:
        ld.append({"@context": "https://schema.org", "@type": "VideoObject", "name": art["title"],
                   "description": art["meta_description"], "thumbnailUrl": poster, "contentUrl": url,
                   "uploadDate": datetime.datetime.now().astimezone().isoformat()})
    for o in ld:
        h += f'\n<script type="application/ld+json">{json.dumps(o, ensure_ascii=False)}</script>'
    return h


def main():
    state = load_state()
    topic = pick_topic(state)
    print("topic:", topic["title"])
    art = write_article(topic)
    print("article:", art["title"])

    work = Path(tempfile.mkdtemp())
    n_img = max(len(split_sentences(art["narration"])), 4)
    images = pick_images(n_img, art.get("image_keywords", []), state)

    video_urls = []
    featured_id = images[0]["id"]
    featured_url = images[0]["url"]
    try:
        vv, vh = make_videos(art, images, work)
        for label, p in (("عمودی", vv), ("افقی", vh)):
            try:
                _, url = upload(p, "video/mp4", f"{art['title']} ({label})")
                video_urls.append((label, url))
            except Exception as e:
                print("video upload failed:", e)
    except Exception as e:
        print("video creation failed, continuing with article only:", e)

    if featured_id is None:
        p = work / "featured.jpg"
        download(featured_url, p)
        featured_id, featured_url = upload(p, "image/jpeg", art["title"], art.get("image_alt", art["title"]))
    else:
        requests.post(f"{API}/media/{featured_id}", auth=AUTH, json={"alt_text": art.get("image_alt", art["title"])}, timeout=60)

    content = build_content(art, topic, video_urls, featured_url, art["title"])
    cats = [c for c in [term("categories", topic["cat"])] if c]
    tags = [t for t in (term("tags", x) for x in art.get("tags", [])[:5]) if t]
    r = requests.post(f"{API}/posts", auth=AUTH, timeout=120, json={
        "title": art["title"], "slug": art["slug"], "content": content, "excerpt": art["meta_description"],
        "status": POST_STATUS, "categories": cats, "tags": tags, "featured_media": featured_id})
    r.raise_for_status()
    post = r.json()
    print("created:", post["link"], POST_STATUS)

    # Rank Math SEO fields (best effort)
    try:
        rm = requests.post(f"{SITE}/wp-json/rankmath/v1/updateMeta", auth=AUTH, timeout=60, json={
            "objectID": post["id"], "objectType": "post", "meta": {
                "rank_math_focus_keyword": topic["kw"], "rank_math_description": art["meta_description"],
                "rank_math_title": f"%title% %sep% {BRAND}"}})
        print("rankmath:", rm.status_code)
    except Exception as e:
        print("rankmath update failed:", e)

    state["done"].append(topic["title"])
    state["used_images"] = (state.get("used_images", []) + [i["id"] for i in images if i["id"]])[-60:]
    save_state(state)


if __name__ == "__main__":
    main()
