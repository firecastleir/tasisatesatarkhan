# patch3.py: ۱) تحمل خطای JSON و کلید گمشده در جواب مقاله  ۲) موضوع‌های پرتقاضا از پیشنهادهای واقعی جستجوی گوگل
import json, re, time

_old_write_article = write_article
_old_research_topics = research_topics


def gemini(prompt, retries=2):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.6, "maxOutputTokens": 30000, "responseMimeType": "application/json"}}
    for model in candidate_models()[:6]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for i in range(retries):
            try:
                r = requests.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=(20, 240))
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
                return json.loads(text, strict=False)
            except Exception as e:
                print("gemini retry", model, i, str(e)[:200])
                time.sleep(8)
    raise RuntimeError("Gemini failed with all models")


def _fallback_narration(art):
    pts = [str(p).strip().rstrip(".،؛ ") + "." for p in (art.get("summary_points") or []) if str(p).strip()]
    text = " ".join(pts)
    if len(text) < 120:
        plain = strip_tags(art.get("article_html", ""))[:900]
        cut = plain.rfind(".")
        text = plain[:cut + 1] if cut > 200 else plain
    return text.strip()


def write_article(topic):
    art = None
    for attempt in range(2):
        art = _old_write_article(topic)
        if art.get("article_html"):
            break
        print("article has no html, retrying", attempt + 1)
    if not art.get("article_html"):
        raise RuntimeError("Gemini returned no article_html")
    need = [k for k in ("narration", "slides", "faq", "tags", "meta_description", "title", "slug") if not art.get(k)]
    if need:
        print("article is missing keys:", need)
        plain = strip_tags(art["article_html"])[:7000]
        try:
            extra = gemini(f"""این متن مقاله‌ی «{topic['title']}» است:
{plain}

فقط کلیدهای زیر را در یک JSON بده (بقیه را ننویس):
{', '.join(need)}
- title: عنوان حداکثر ۶۰ کاراکتر شامل «{topic['kw']}»
- slug: انگلیسی کوچک با خط تیره
- meta_description: ۱۲۰ تا ۱۵۵ کاراکتر شامل کلمه کلیدی
- tags: ۳ تا ۵ برچسب فارسی
- faq: ۶ شیء با q و a
- narration: روایت ویدیو ۱۳۰ تا ۱۶۰ کلمه، حداکثر ۷ جمله، فارسی ساده، اعداد با حروف، بدون کلمه انگلیسی، بدون آدرس و شماره، پایان با دعوت به مشاوره با {BRAND}
- slides: به تعداد جمله‌های narration، هر کدام {{"title": عنوان کوتاه حداکثر ۵ کلمه, "points": ۲ تا ۳ نکته کوتاه حداکثر ۷ کلمه}}""", retries=1)
            for k in need:
                if extra.get(k):
                    art[k] = extra[k]
        except Exception as e:
            print("could not fill missing keys:", str(e)[:150])
    if not art.get("narration"):
        art["narration"] = _fallback_narration(art)
        print("narration built from the article summary")
    if not art.get("slides"):
        sents = split_sentences(art["narration"])
        art["slides"] = [{"title": " ".join(s.split()[:4]), "points": []} for s in sents]
    art.setdefault("title", topic["title"])
    if not art.get("tags"):
        art["tags"] = [topic["kw"]]
    if not art.get("meta_description"):
        art["meta_description"] = strip_tags(art["article_html"])[:150]
    art.setdefault("faq", [])
    art.setdefault("slug", "")
    return art


# ---------------------------------------------------------------- پیشنهادهای واقعی جستجوی گوگل
def google_suggest(q):
    try:
        r = requests.get("https://suggestqueries.google.com/complete/search",
                         params={"client": "firefox", "hl": "fa", "gl": "ir", "q": q},
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.encoding = "utf-8"
        return [str(x) for x in r.json()[1]][:10]
    except Exception as e:
        print("suggest failed:", type(e).__name__)
        return []


def research_topics(state):
    found = _old_research_topics(state)
    if found:
        return found
    cats = [v for k, v in globals().items() if k.startswith("CAT_") and isinstance(v, str)]
    done = set(state.get("done", []))
    seeds = []
    for t in TOPICS:
        if t["title"] not in done and t["kw"] not in seeds:
            seeds.append(t["kw"])
    sugg = {}
    for sd in seeds[:14]:
        lst = google_suggest(sd)
        if lst:
            sugg[sd] = lst
        time.sleep(0.5)
    if not sugg:
        print("research: google suggestions unavailable")
        return []
    allowed = {x for lst in sugg.values() for x in lst} | set(sugg)
    prompt = f"""این‌ها پیشنهادهای واقعی جستجوی گوگل (فارسی، ایران) است؛ هر پیشنهاد نشانه‌ی عبارتی است که مردم واقعاً جستجو می‌کنند (پیشنهادهای بالاتر معمولاً پرجستجوترند):
{json.dumps(sugg, ensure_ascii=False)}

کسب‌وکار: {BUSINESS}
از میان همین عبارت‌ها ۱۰ موضوع مقاله انتخاب کن که با خدمات این کسب‌وکار مرتبط است و برای جذب مشتری ارزش دارد. اول عبارت‌هایی که هم پرجستجو به نظر می‌رسند هم قصد خرید یا سفارش دارند. kw باید دقیقاً یکی از همین عبارت‌ها باشد (چیزی از خودت نساز).
با این عنوان‌های انجام‌شده تکراری نباشد: {json.dumps(list(done)[-40:], ensure_ascii=False)}
فقط یک فهرست JSON با کلیدهای title (عنوان مقاله فارسی)، cat (یکی از: {', '.join(cats)})، kw، kw2 (۲ تا ۴ عبارت فرعی از همین پیشنهادها)، why (یک جمله)"""
    try:
        items = gemini(prompt, retries=1)
    except Exception as e:
        print("research (suggestions) failed:", str(e)[:150])
        return []
    if isinstance(items, dict):
        items = items.get("topics") or items.get("items") or []
    out = []
    seen = done | {t["title"] for t in state.get("researched", [])}
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict) or not it.get("title") or not it.get("kw") or it["title"] in seen:
            continue
        if str(it["kw"]).strip() not in allowed:
            continue
        cat = it.get("cat") if it.get("cat") in cats else (cats[0] if cats else "")
        out.append({"title": str(it["title"]).strip(), "cat": cat, "kw": str(it["kw"]).strip(),
                    "kw2": [str(x).strip() for x in (it.get("kw2") or []) if str(x).strip()][:4],
                    "why": str(it.get("why", ""))[:200]})
        seen.add(it["title"])
    print("research (google suggestions): found", len(out), "topics")
    for t in out[:10]:
        print("  -", t["kw"], "|", t.get("why", ""))
    return out
