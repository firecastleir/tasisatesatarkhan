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

# رنگ‌های ویدیو (BGR برای زیرنویس) و پس‌زمینه (RGB)
ACCENT_ASS = "&H0045C4F5"      # زرد کهربایی
ACCENT_BAR = "&H0045C4F5"
BG_TOP = (9, 30, 58)           # بالای پس‌زمینه
BG_BOTTOM = (26, 76, 135)      # پایین پس‌زمینه

# ============================================================

AUTH = (WP_USER, WP_APP_PASSWORD)
API = f"{SITE}/wp-json/wp/v2"
HERE = Path(__file__).parent
STATE_FILE = HERE / "state.json"


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
- slides: به تعداد جمله‌های narration (به ترتیب)، برای هر جمله یک شیء با کلیدهای title (عنوان کوتاه فارسی حداکثر ۵ کلمه) و points (۲ تا ۳ نکته بسیار کوتاه فارسی، هرکدام حداکثر ۷ کلمه، دقیقاً مطابق همان جمله). این‌ها روی صفحه ویدیو نمایش داده می‌شوند، پس باید دقیق، فنی و بدون غلط باشند.

فقط JSON با این کلیدها:
title (حداکثر ۶۰ کاراکتر، شامل کلمه کلیدی), slug (انگلیسی کوچک با خط تیره), meta_description (۱۲۰ تا ۱۵۵ کاراکتر شامل کلمه کلیدی),
tags (۳ تا ۵ برچسب فارسی), article_html, faq (لیست ۶ شیء با q و a، پاسخ‌های دقیق و کامل در ۲ تا ۴ جمله), narration, slides, image_keywords (۳ عبارت انگلیسی برای جستجوی عکس), image_alt (متن جایگزین فارسی عکس شاخص)"""
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
    prompt = ("Language: Persian (Farsi, fa-IR), standard Tehran accent. You are a professional Iranian female "
              "narrator recording an explainer video. Read the text below exactly as written, fluently and naturally, "
              "with correct Persian pronunciation, a warm calm tone, a steady medium pace and short natural pauses "
              "between sentences. Do not add or skip any words and do not read these instructions.\n\nText:\n" + text)
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": GEMINI_TTS_VOICE}}}}}
    last = None
    for model in models[:3]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(3):
            try:
                r = requests.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=300)
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
                     "-ar", "44100", "-ac", "1", "-af", "apad=pad_dur=0.5", str(wav_path)])
                return
            except Exception as e:
                last = e
                print("gemini tts retry", model, attempt, str(e)[:200])
                time.sleep(6)
    raise RuntimeError(f"gemini tts failed: {last}")


def find_pauses(path):
    r = subprocess.run(["ffmpeg", "-i", str(path), "-af", "silencedetect=noise=-32dB:d=0.18", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return [(a + b) / 2 for a, b in zip(starts, ends)]


def segment_durations(sentences, wav_path, total):
    """زمان هر جمله را از روی طول متن حدس می‌زند و به نزدیک‌ترین مکث واقعی صدا می‌چسباند."""
    if len(sentences) == 1:
        return [total]
    weights = [max(len(x), 1) for x in sentences]
    pauses = find_pauses(wav_path)
    avg = total / len(sentences)
    bounds, cum = [0.0], 0
    for w in weights[:-1]:
        cum += w
        target = total * cum / sum(weights)
        cands = [p for p in pauses if abs(p - target) <= 0.35 * avg and p > bounds[-1] + 0.8]
        b = min(cands, key=lambda p: abs(p - target)) if cands else max(target, bounds[-1] + 0.8)
        bounds.append(min(b, total - 0.5))
    bounds.append(total)
    return [max(bounds[i + 1] - bounds[i], 0.5) for i in range(len(sentences))]


def synth_all(sentences, work):
    """کل متن را یک‌جا می‌خواند (صدا و لحن یکدست) و زمان جمله‌ها را برای زیرنویس حساب می‌کند."""
    text = " ".join(sentences)
    wav = work / "audio.wav"
    ok = False
    if os.environ.get("USE_GEMINI_TTS", "1") != "0":
        try:
            gemini_tts(text, work / "full.pcm", wav)
            ok = True
            print("voice: gemini tts", GEMINI_TTS_VOICE)
        except Exception as e:
            print("gemini tts failed, falling back to edge-tts:", str(e)[:300])
    if not ok:
        mp3 = work / "full.mp3"
        asyncio.run(tts(text, mp3))
        run(["ffmpeg", "-y", "-i", str(mp3), "-ar", "44100", "-ac", "1", "-af", "apad=pad_dur=0.5", str(wav)])
        print("voice: edge-tts", EDGE_VOICE)
    total = duration(wav)
    durs = segment_durations(sentences, wav, total)
    return [(sent, "", d) for sent, d in zip(sentences, durs)]


def ass_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def esc(t):
    """متن را برای زیرنویس تمیز می‌کند و جهت راست‌به‌چپ را مشخص می‌کند."""
    t = re.sub(r"[{}\\]", "", str(t or "")).replace("\n", " ").strip()
    return ("\u200f" + t + "\u200f") if t else t


def make_bg(work, W, H, name):
    (r0, g0, b0), (r1, g1, b1) = BG_TOP, BG_BOTTOM
    vf = (f"format=gbrp,geq=r='{r0}+({r1}-{r0})*Y/{H}':g='{g0}+({g1}-{g0})*Y/{H}':b='{b0}+({b1}-{b0})*Y/{H}',"
          f"format=rgb24")
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:d=1", "-vf", vf, "-frames:v", "1",
         f"bg_{name}.png"], cwd=work)
    return f"bg_{name}.png"


def make_explainer_ass(segments, slides, W, H, path, title, intro, outro):
    vertical = H > W
    head_sz = 90 if vertical else 68
    body_sz = 60 if vertical else 46
    sub_sz = 48 if vertical else 38
    sub_mv = 250 if vertical else 60
    cx = W // 2
    head_y = 330 if vertical else 140
    body_y0 = 610 if vertical else 320
    gap = 200 if vertical else 110
    narr = sum(d for _, _, d in segments)
    total = intro + narr + outro
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Head,Vazirmatn,{head_sz},{ACCENT_ASS},&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,0,8,90,90,40,1
Style: Body,Vazirmatn,{body_sz},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,8,100,100,40,1
Style: Sub,Vazirmatn,{sub_sz},&H00FFFFFF,&H00FFFFFF,&H78000000,&H96000000,1,0,0,0,100,100,0,0,3,3,0,2,90,90,{sub_mv},1
Style: Mark,Vazirmatn,{int(body_sz*0.6)},{ACCENT_ASS},&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,8,40,40,{60 if vertical else 30},1
Style: Card,Vazirmatn,{head_sz},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,0,5,100,100,40,1
Style: Step,Vazirmatn,{int(body_sz*0.7)},{ACCENT_ASS},&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,9,40,40,40,1
Style: Bar,Vazirmatn,20,{ACCENT_BAR},&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,9,0,0,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    ev = []
    # برند بالای صفحه در تمام مدت
    ev.append(f"Dialogue: 1,{ass_time(0)},{ass_time(total)},Mark,,0,0,0,,{{\\an8\\pos({cx},{60 if vertical else 28})}}{esc(BRAND)}  |  {SITE_SHORT}")
    # کارت عنوان (ابتدا)
    ev.append(f"Dialogue: 2,{ass_time(0.2)},{ass_time(intro)},Card,,0,0,0,,{{\\fad(450,350)}}{esc(title)}")
    # نوار پیشرفت
    bar_h = 14
    ev.append(f"Dialogue: 1,{ass_time(intro)},{ass_time(intro + narr)},Bar,,0,0,0,,"
              f"{{\\an9\\pos({W},0)\\p1\\fscx1\\t(0,{int(narr * 1000)},\\fscx100)}}m 0 0 l {W} 0 l {W} {bar_h} l 0 {bar_h}{{\\p0}}")
    t = intro
    n = len(segments)
    for i, (text, _, d) in enumerate(segments):
        end = t + d
        sl = slides[i] if i < len(slides) else {}
        ttl = esc(sl.get("title") or " ".join(text.split()[:5]))
        ev.append(f"Dialogue: 2,{ass_time(t)},{ass_time(end)},Head,,0,0,0,,{{\\an8\\pos({cx},{head_y})\\fad(250,150)}}{ttl}")
        for k, p in enumerate((sl.get("points") or [])[:3]):
            bs = min(t + 0.7 + 0.9 * k, end - 0.4)
            ev.append(f"Dialogue: 2,{ass_time(bs)},{ass_time(end)},Body,,0,0,0,,"
                      f"{{\\an8\\pos({cx},{body_y0 + k * gap})\\fad(300,100)}}\u200f• {esc(p)}")
        ev.append(f"Dialogue: 2,{ass_time(t)},{ass_time(end)},Step,,0,0,0,,{{\\pos({W - 50},{110 if vertical else 80})}}گام {fa(i + 1)} از {fa(n)}")
        ev.append(f"Dialogue: 3,{ass_time(t)},{ass_time(end)},Sub,,0,0,0,,{esc(text)}")
        t = end
    # کارت پایانی
    ev.append(f"Dialogue: 2,{ass_time(intro + narr)},{ass_time(total)},Card,,0,0,0,,"
              f"{{\\fad(400,0)}}{esc(BRAND)}\\Nتماس: {PHONE}\\N{MOBILE}\\N{SITE_SHORT}")
    Path(path).write_text(head + "\n".join(ev), encoding="utf-8")


def build_explainer(work, segments, slides, W, H, name, title, intro=3.2, outro=4.5):
    bg = make_bg(work, W, H, name)
    narr = sum(d for _, _, d in segments)
    total = intro + narr + outro
    make_explainer_ass(segments, slides, W, H, work / f"sub_{name}.ass", title, intro, outro)
    ms = int(intro * 1000)
    fc = (f"[1:a]adelay={ms}:all=1,apad=whole_dur={total:.2f}[a];"
          f"[0:v]zoompan=z='min(1+0.00035*on,1.14)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps=30,"
          f"ass=sub_{name}.ass,format=yuv420p[v]")
    out = f"{name}.mp4"
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", bg, "-i", "audio.wav", "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], cwd=work)
    return work / out


def make_videos(art, work):
    sentences = split_sentences(art["narration"])
    segments = synth_all(sentences, work)
    slides = art.get("slides") or []
    vv = build_explainer(work, segments, slides, 1080, 1920, "vertical", art["title"])
    vh = build_explainer(work, segments, slides, 1920, 1080, "horizontal", art["title"])
    cover = work / "cover.jpg"
    run(["ffmpeg", "-y", "-ss", "1.6", "-i", str(vh), "-frames:v", "1", "-q:v", "2", str(cover)])
    return vv, vh, cover


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


def sanitize_html(h):
    """متن مقاله را تمیز و برای موبایل مناسب می‌کند."""
    h = (h or "").strip()
    h = re.sub(r"^```(?:html)?\s*|\s*```$", "", h, flags=re.I).strip()
    if h.count("&lt;") > 5 and "<h2" not in h:
        h = html.unescape(h)
    h = re.sub(r"(?is)<(script|style|iframe)\b.*?</\1>", "", h)
    h = re.sub(r"(?is)<!doctype[^>]*>", "", h)
    h = re.sub(r"(?is)</?(html|head|body|h1)\b[^>]*>", "", h)
    h = re.sub(r"(?is)<table\b[^>]*>", '<table style="width:100%;border-collapse:collapse;font-size:15px">', h)
    h = re.sub(r"(?is)<th\b[^>]*>", '<th style="border:1px solid #9fb3c8;background:#dbe8f5;color:#10263b;padding:8px;text-align:right">', h)
    h = re.sub(r"(?is)<td\b[^>]*>", '<td style="border:1px solid #9fb3c8;background:#ffffff;color:#1b2a3a;padding:8px;text-align:right;vertical-align:top">', h)
    h = re.sub(r"(?is)(<table\b.*?</table>)",
               r'<div style="overflow-x:auto;-webkit-overflow-scrolling:touch;margin:16px 0">\1</div>', h)
    return h


def build_content(art, topic, videos, poster, internal_video_title):
    h = '<div dir="rtl">\n'
    main_video = next((v for v in videos if v and v[0] == "افقی"), None)
    if main_video:
        h += (f'<div style="max-width:100%;margin:0 0 22px"><video controls preload="none" playsinline '
              f'poster="{poster}" style="width:100%;max-width:100%;height:auto;border-radius:10px;background:#000" '
              f'src="{main_video[1]}"></video></div>\n')
    h += sanitize_html(art["article_html"])
    if art.get("faq"):
        h += "\n<h2>سوالات متداول</h2>\n"
        for f in art["faq"]:
            h += f"<h3>{html.escape(f['q'])}</h3>\n<p>{html.escape(f['a'])}</p>\n"
    h += f"""
<div style="border:2px solid #1a6fb5;border-radius:12px;padding:18px;margin-top:30px;background:#f2f8ff;color:#12263a">
<h3 style="color:#0b3a66;margin-top:0">مشاوره و سفارش از {BRAND}</h3>
<p style="color:#12263a">تلفن: <a href="tel:{PHONE}" style="color:#0b5cab">{PHONE}</a> | موبایل: <a href="tel:{MOBILE}" style="color:#0b5cab">{MOBILE}</a></p>
<p style="color:#12263a">آدرس دفتر: {OFFICE}</p>
<p style="color:#12263a">شماره جواز کسب: {LICENSE}</p>
</div>
</div>"""
    return h


def main():
    state = load_state()
    topic = pick_topic(state)
    print("topic:", topic["title"])
    art = write_article(topic)
    print("article:", art["title"])

    work = Path(tempfile.mkdtemp())
    video_urls = []
    featured_id, featured_url = None, ""
    try:
        vv, vh, cover = make_videos(art, work)
        featured_id, featured_url = upload(cover, "image/jpeg", art["title"], art.get("image_alt", art["title"]))
        for label, p in (("عمودی", vv), ("افقی", vh)):
            try:
                _, url = upload(p, "video/mp4", f"{art['title']} ({label})")
                video_urls.append((label, url))
            except Exception as e:
                print("video upload failed:", e)
    except Exception as e:
        print("video creation failed, continuing with article only:", e)

    if featured_id is None:
        for k in art.get("image_keywords", [])[:2]:
            ph = pixabay_photos(k, 1)
            if ph:
                try:
                    p = work / "featured.jpg"
                    download(ph[0]["url"], p)
                    featured_id, featured_url = upload(p, "image/jpeg", art["title"], art.get("image_alt", art["title"]))
                    break
                except Exception as e:
                    print("featured image failed:", str(e)[:150])

    content = build_content(art, topic, video_urls, featured_url, art["title"])
    cats = [c for c in [term("categories", topic["cat"])] if c]
    tags = [t for t in (term("tags", x) for x in art.get("tags", [])[:5]) if t]
    r = requests.post(f"{API}/posts", auth=AUTH, timeout=120, json={
        "title": art["title"], "slug": art["slug"], "content": content, "excerpt": art["meta_description"],
        "status": POST_STATUS, "categories": cats, "tags": tags, "featured_media": featured_id or 0})
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
    save_state(state)


VOICE_SAMPLE = ("سلام. من گوینده تاسیسات ستارخان هستم. امروز درباره دلایل خاموش شدن پکیج و روش‌های رفع آن صحبت می‌کنیم. "
                "اگر پکیج شما مشکل دارد، با کارشناسان ما تماس بگیرید.")


def voicetest():
    """چند صدا را امتحان می‌کند و نمونه‌ها را در کتابخانه رسانه وردپرس می‌گذارد."""
    global GEMINI_TTS_VOICE
    work = Path(tempfile.mkdtemp())
    for v in ["Aoede", "Kore", "Leda", "Zephyr", "Despina", "Sulafat"]:
        GEMINI_TTS_VOICE = v
        try:
            wav = work / f"{v}.wav"
            gemini_tts(VOICE_SAMPLE, work / f"{v}.pcm", wav)
            mp3 = work / f"voice-test-{v}.mp3"
            run(["ffmpeg", "-y", "-i", str(wav), "-b:a", "128k", str(mp3)])
            upload(mp3, "audio/mpeg", f"voice-test-{v}")
            print("uploaded sample:", v)
        except Exception as e:
            print("voice failed:", v, str(e)[:200])
        time.sleep(20)
    try:
        mp3 = work / "voice-test-edge-Dilara.mp3"
        asyncio.run(tts(VOICE_SAMPLE, mp3))
        upload(mp3, "audio/mpeg", "voice-test-edge-Dilara")
        print("uploaded sample: edge Dilara")
    except Exception as e:
        print("edge sample failed:", str(e)[:200])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "voicetest":
        voicetest()
    else:
        main()
