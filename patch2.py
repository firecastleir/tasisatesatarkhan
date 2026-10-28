# patch2.py: فقط یک ویدیوی افقی + پیدا کردن موضوع‌های پرتقاضا از طریق جستجوی گوگل
import json, re, shutil, tempfile, datetime
from pathlib import Path

_old_pick_topic = pick_topic


# ---------------------------------------------------------------- ویدیو: فقط افقی
def make_videos(art, sentences, scene_ids, lib_by_id, work):
    segments = synth_all(sentences, work)
    segments = [(t, w, max(round(d * 30) / 30, 0.5)) for t, w, d in segments]
    slides = art.get("slides") or []
    scenes = []
    for i in range(len(segments)):
        sid = scene_ids[i] if i < len(scene_ids) else None
        item = lib_by_id.get(sid) if sid else None
        sc = None
        if item:
            try:
                name = f"lib_{item['id']}" + (".mp4" if item["type"] == "video" else ".jpg")
                download(item["url"], work / name)
                sc = ("vid" if item["type"] == "video" else "img", name)
            except Exception as e:
                print("library download failed:", str(e)[:100])
        scenes.append(sc)
    print("video scenes:", [sc[0] if sc else "graphic" for sc in scenes])
    return build_explainer(work, segments, slides, scenes, 1920, 1080, "horizontal", art["title"])


def send_to_telegram(art, article_url, vh, post_id=0):
    if not (TG_TOKEN and TG_CHAT):
        print("telegram not configured: video saved only as backup artifact")
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
    try:
        p = fit_for_telegram(vh)
        with open(p, "rb") as f:
            return tg_call("sendVideo", {"chat_id": chat, "caption": "ویدیوی افقی: برای آپارات، یوتیوب و داخل مقاله",
                                         "supports_streaming": "true"}, {"video": f})
    except Exception as e:
        print("telegram video failed:", type(e).__name__)
        return False


# ---------------------------------------------------------------- پژوهش موضوع از گوگل
def gemini_grounded(prompt):
    """Gemini را با جستجوی زنده‌ی گوگل صدا می‌زند و متن جواب را برمی‌گرداند (یا رشته‌ی خالی)."""
    for tool in ({"google_search": {}}, {"google_search_retrieval": {}}):
        body = {"contents": [{"parts": [{"text": prompt}]}], "tools": [tool],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8000}}
        for model in candidate_models()[:4]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            try:
                r = requests.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=(20, 200))
                if r.status_code == 429:
                    time.sleep(20)
                    continue
                if r.status_code in (400, 404):
                    continue
                r.raise_for_status()
                parts = r.json()["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts)
                if text.strip():
                    print("research model:", model)
                    return text
            except Exception as e:
                print("research retry:", model, type(e).__name__)
    return ""


def research_topics(state):
    cats = [v for k, v in globals().items() if k.startswith("CAT_") and isinstance(v, str)]
    done = state.get("done", [])[-60:]
    prompt = f"""با جستجوی واقعی در گوگل (نتایج فارسی، بازار ایران) برای کسب‌وکار زیر ۱۰ موضوع مقاله پیدا کن.
کسب‌وکار: {BUSINESS}
شرط‌ها:
- موضوعی انتخاب کن که کاربران ایرانی واقعاً زیاد درباره‌اش جستجو می‌کنند (به پیشنهادهای جستجوی گوگل، بخش «سوالات مرتبط» و «جستجوهای مرتبط» توجه کن).
- صفحه اول گوگل برای آن موضوع پر از مقاله و صفحه‌های رقبا باشد (نشانه‌ی تقاضا).
- با خدمات یا محصولات همین کسب‌وکار مرتبط باشد و بتواند مشتری جذب کند.
- از پرتقاضاترین به کم‌تقاضا مرتب کن.
- با این عنوان‌های انجام‌شده تکراری نباشد: {json.dumps(done, ensure_ascii=False)}
حجم دقیق جستجو را نمی‌دانی؛ عدد نساز. فقط یک فهرست JSON بده (بدون هیچ متن دیگر) از اشیاء با این کلیدها:
title (عنوان مقاله به فارسی)، cat (یکی از: {', '.join(cats)})، kw (کلمه کلیدی اصلی؛ همان عبارتی که مردم جستجو می‌کنند)، kw2 (فهرست ۲ تا ۴ عبارت فرعی)، why (یک جمله: چرا پرتقاضاست)"""
    text = gemini_grounded(prompt)
    if not text:
        print("research: skipped (no answer)")
        return []
    s, e = text.find("["), text.rfind("]")
    try:
        items = json.loads(text[s:e + 1])
    except Exception:
        print("research: could not read the answer")
        return []
    out = []
    seen = set(state.get("done", [])) | {t["title"] for t in state.get("researched", [])}
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict) or not it.get("title") or not it.get("kw") or it["title"] in seen:
            continue
        cat = it.get("cat") if it.get("cat") in cats else (cats[0] if cats else "")
        out.append({"title": str(it["title"]).strip(), "cat": cat, "kw": str(it["kw"]).strip(),
                    "kw2": [str(x).strip() for x in (it.get("kw2") or []) if str(x).strip()][:4],
                    "why": str(it.get("why", ""))[:200]})
        seen.add(it["title"])
    print("research: found", len(out), "topics")
    for t in out[:10]:
        print("  -", t["kw"], "|", t.get("why", ""))
    return out


def pick_topic(state):
    done = set(state.get("done", []))
    pending = [t for t in state.get("researched", []) if t["title"] not in done]
    if not pending:
        try:
            new = research_topics(state)
            if new:
                state.setdefault("researched", []).extend(new)
                state["research_date"] = datetime.date.today().isoformat()
                pending = [t for t in new if t["title"] not in done]
        except Exception as e:
            print("research failed:", str(e)[:150])
    if pending:
        print("topic source: google research")
        return pending[0]
    print("topic source: built-in list")
    return _old_pick_topic(state)


# ---------------------------------------------------------------- main (یک ویدیوی افقی)
def main():
    state = load_state()
    topic = pick_topic(state)
    print("topic:", topic["title"], "| keyword:", topic["kw"])
    art = write_article(topic)
    art["article_html"] = sanitize_html(art["article_html"])
    print("article:", art["title"])

    slug = re.sub(r"[^a-z0-9-]+", "-", str(art.get("slug", "")).lower()).strip("-")[:60] or "article"
    work = Path(tempfile.mkdtemp())
    sentences = split_sentences(art["narration"])
    heads_all = [strip_tags(x) for x in re.findall(r"(?is)<h2\b[^>]*>(.*?)</h2>", art["article_html"])]
    cand = [i for i, hd in enumerate(heads_all) if not re.search(r"سوالات متداول|نتیجه", hd)][:6]
    library = fetch_library()
    lib_by_id = {i["id"]: i for i in library}
    m = match_library(topic, sentences, [heads_all[i] for i in cand], library)

    vh = None
    try:
        vh = make_videos(art, sentences, m["video_scenes"], lib_by_id, work)
        outdir = HERE / "out"
        outdir.mkdir(exist_ok=True)
        shutil.copy(vh, outdir / "horizontal.mp4")
    except Exception as e:
        print("video creation failed, continuing with article only:", str(e)[:200])

    featured_id, featured_url = None, ""
    if m["featured"] and m["featured"] in lib_by_id:
        featured_id, featured_url = m["featured"], lib_by_id[m["featured"]]["url"]
    else:
        try:
            cover = render_still(work, 1280, 720, None, art["title"], [], f"{slug}-cover.jpg")
            featured_id, featured_url = upload(cover, "image/jpeg", art["title"], art.get("image_alt", art["title"]))
        except Exception as e:
            print("cover failed:", str(e)[:150])

    banner_url = ""
    try:
        bn = render_still(work, 1600, 500, None, art["title"], [], f"{slug}-banner.jpg")
        _, banner_url = upload(bn, "image/jpeg", art["title"], f"بنر {art['title']}")
    except Exception as e:
        print("banner failed:", str(e)[:150])

    figs, cards = {}, 0
    for pos, i in enumerate(cand):
        try:
            sid = m["section_media"][pos] if pos < len(m["section_media"]) else None
            item = lib_by_id.get(sid) if sid else None
            if item:
                figs[i] = figure_html(item["large"], item["alt"], item["label"][:120])
            elif cards < 4 and pos < len(m["section_points"]) and m["section_points"][pos]:
                jpg = render_still(work, 1280, 720, None, heads_all[i], m["section_points"][pos], f"{slug}-section-{pos + 1}.jpg")
                _, url = upload(jpg, "image/jpeg", heads_all[i], f"{heads_all[i]} - {art['title']}")
                figs[i] = figure_html(url, f"{heads_all[i]} - {art['title']}", heads_all[i], ' width="1280" height="720"')
                cards += 1
        except Exception as e:
            print("section image failed:", str(e)[:150])

    content = build_content(art, figs, with_placeholder=bool(vh and TG_TOKEN and TG_CHAT),
                            banner_url=banner_url, related=related_posts())
    cats = [c for c in [term("categories", topic["cat"])] if c]
    tags = [t for t in (term("tags", x) for x in art.get("tags", [])[:5]) if t]
    payload = {"title": art["title"], "content": content, "excerpt": art["meta_description"],
               "status": POST_STATUS, "categories": cats, "tags": tags, "slug": slug}
    if featured_id:
        payload["featured_media"] = featured_id
    r = requests.post(f"{API}/posts", auth=AUTH, timeout=120, json=payload)
    r.raise_for_status()
    post = r.json()
    article_url = f"{SITE}/?p={post['id']}"
    print("created:", article_url, POST_STATUS)
    set_rank_math(post["id"], topic, art, featured_url)

    if vh:
        send_to_telegram(art, article_url, vh, post["id"])
    try:
        create_web_story(work, art, art.get("slides") or [], m["story_media"], lib_by_id, article_url, slug)
    except Exception as e:
        print("web story failed:", str(e)[:200])

    state["done"].append(topic["title"])
    save_state(state)
