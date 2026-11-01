# patch2.py: فقط یک ویدیوی افقی + پیدا کردن موضوع‌های پرتقاضا از طریق جستجوی گوگل
import json, re, shutil, tempfile, datetime
from pathlib import Path

_old_pick_topic = pick_topic


# ---------------------------------------------------------------- ویدیوی واقعی‌تر: چند نما از کتابخانه، بدون پوشاندن محصول
def match_library(topic, sentences, heads, library):
    """برای هر جمله ویدیو تا ۳ عکس/فیلم مرتبط، و برای هر بخش مقاله و وب‌استوری یک مورد پیدا می‌کند."""
    empty = {"video_scenes": [], "section_media": [], "story_media": [], "featured": None, "section_points": []}
    lib = [{"id": i["id"], "type": i["type"], "label": i["label"]} for i in library[:300]]
    prompt = f"""موضوع مقاله: «{topic['title']}»
جمله‌های روایت ویدیو (به ترتیب): {json.dumps(sentences, ensure_ascii=False)}
تیترهای مقاله (به ترتیب): {json.dumps(heads, ensure_ascii=False)}
کتابخانه رسانه سایت (id، type و label که توضیح خود صاحب سایت است): {json.dumps(lib, ensure_ascii=False)}

وظیفه:
۱) video_scenes: برای هر جمله ویدیو یک فهرست از حداکثر ۳ id مرتبط‌ترین عکس یا فیلم (به ترتیب نمایش). اگر مرتبط‌ای نیست فهرست خالی.
۲) section_media: برای هر تیتر مقاله دقیق‌ترین عکس (یا null). فیلم مجاز نیست.
۳) story_media: برای هر جمله (صفحه وب‌استوری) دقیق‌ترین عکس (یا null). فیلم مجاز نیست.
۴) featured: بهترین عکس شاخص مقاله (یا null).
۵) section_points: برای هر تیتر مقاله ۳ نکته خیلی کوتاه و دقیق فارسی (هرکدام حداکثر ۷ کلمه).
قوانین: فقط اگر label واقعاً همان محصول، موضوع یا کار را توصیف می‌کند انتخاب کن. اگر شک داری انتخاب نکن. حدس نزن و مورد بی‌ربط انتخاب نکن (مثلاً برای پکیج، عکس آبگرمکن ممنوع است). در video_scenes هر id فقط یک بار در کل ویدیو استفاده شود.
فقط JSON: {{"video_scenes": [{len(sentences)} فهرست], "section_media": [{len(heads)} عدد id یا null], "story_media": [{len(sentences)} عدد id یا null], "featured": id یا null, "section_points": [{len(heads)} فهرست ۳ تایی]}}"""
    try:
        r = gemini(prompt, retries=1)
    except Exception as e:
        print("library match skipped:", str(e)[:200])
        return empty
    by_id = {i["id"]: i for i in library}

    def to_id(v):
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    def single(lst, n):
        out, used = [], set()
        for k in range(n):
            v = to_id(lst[k]) if isinstance(lst, list) and k < len(lst) else None
            it = by_id.get(v)
            if it and v not in used and it["type"] == "image":
                used.add(v)
                out.append(v)
            else:
                out.append(None)
        return out

    scenes, used = [], set()
    raw = r.get("video_scenes") if isinstance(r.get("video_scenes"), list) else []
    for k in range(len(sentences)):
        ids = raw[k] if k < len(raw) else []
        if not isinstance(ids, list):
            ids = [ids]
        keep = []
        for v in ids:
            v = to_id(v)
            if v in by_id and v not in used and len(keep) < 3:
                used.add(v)
                keep.append(v)
        scenes.append(keep)
    feat = to_id(r.get("featured"))
    if feat not in by_id or by_id[feat]["type"] != "image":
        feat = None
    pts = r.get("section_points") if isinstance(r.get("section_points"), list) else []
    return {"video_scenes": scenes, "section_media": single(r.get("section_media"), len(heads)),
            "story_media": single(r.get("story_media"), len(sentences)), "featured": feat, "section_points": pts}


def make_explainer_ass(segments, slides, W, H, path, title, intro, outro, kinds=None):
    vertical = H > W
    head_sz = 90 if vertical else 68
    body_sz = 60 if vertical else 46
    sub_sz = 48 if vertical else 38
    sub_mv = 250 if vertical else 60
    low_sz = 70 if vertical else 54
    cx = W // 2
    head_y = 330 if vertical else 140
    body_y0 = 610 if vertical else 320
    gap = 200 if vertical else 110
    low_y = H - (420 if vertical else 215)
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
Style: Low,Vazirmatn,{low_sz},{ACCENT_ASS},&H00FFFFFF,&H8C000000,&H00000000,1,0,0,0,100,100,0,0,3,12,0,2,120,120,40,1
Style: Mark,Vazirmatn,{int(body_sz*0.6)},{ACCENT_ASS},&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,8,40,40,{60 if vertical else 30},1
Style: Card,Vazirmatn,{head_sz},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,0,5,100,100,40,1
Style: Step,Vazirmatn,{int(body_sz*0.7)},{ACCENT_ASS},&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,9,40,40,40,1
Style: Bar,Vazirmatn,20,{ACCENT_BAR},&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,9,0,0,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Encoding_unused,Text
""".replace("Encoding_unused", "Effect")
    ev = []
    ev.append(f"Dialogue: 1,{ass_time(0)},{ass_time(total)},Mark,,0,0,0,,{{\\an8\\pos({cx},{60 if vertical else 28})}}{esc(BRAND)}  |  {SITE_SHORT}")
    ev.append(f"Dialogue: 2,{ass_time(0.2)},{ass_time(intro)},Card,,0,0,0,,{{\\fad(450,350)}}{esc(title)}")
    bar_h = 14
    ev.append(f"Dialogue: 1,{ass_time(intro)},{ass_time(intro + narr)},Bar,,0,0,0,,"
              f"{{\\an9\\pos({W},0)\\p1\\fscx1\\t(0,{int(narr * 1000)},\\fscx100)}}m 0 0 l {W} 0 l {W} {bar_h} l 0 {bar_h}{{\\p0}}")
    t = intro
    n = len(segments)
    for i, (text, _, d) in enumerate(segments):
        end = t + d
        sl = slides[i] if i < len(slides) else {}
        ttl = esc(sl.get("title") or " ".join(text.split()[:5]))
        media = bool(kinds and i < len(kinds) and kinds[i] == "media")
        if media:
            # روی عکس یا فیلم واقعی فقط یک عنوان کوچک پایین صفحه می‌آید تا محصول دیده شود
            ev.append(f"Dialogue: 2,{ass_time(t)},{ass_time(min(end, t + 3.5))},Low,,0,0,0,,{{\\an2\\pos({cx},{low_y})\\fad(300,200)}}{ttl}")
        else:
            ev.append(f"Dialogue: 2,{ass_time(t)},{ass_time(end)},Head,,0,0,0,,{{\\an8\\pos({cx},{head_y})\\fad(250,150)}}{ttl}")
            for k, p in enumerate((sl.get("points") or [])[:3]):
                bs = min(t + 0.7 + 0.9 * k, end - 0.4)
                ev.append(f"Dialogue: 2,{ass_time(bs)},{ass_time(end)},Body,,0,0,0,,"
                          f"{{\\an8\\pos({cx},{body_y0 + k * gap})\\fad(300,100)}}\u200f• {esc(p)}")
        ev.append(f"Dialogue: 2,{ass_time(t)},{ass_time(end)},Step,,0,0,0,,{{\\pos({W - 50},{110 if vertical else 80})}}گام {fa(i + 1)} از {fa(n)}")
        ev.append(f"Dialogue: 3,{ass_time(t)},{ass_time(end)},Sub,,0,0,0,,{esc(text)}")
        t = end
    ev.append(f"Dialogue: 2,{ass_time(intro + narr)},{ass_time(total)},Card,,0,0,0,,"
              f"{{\\fad(400,0)}}{esc(BRAND)}\\Nتماس: {PHONE}\\N{MOBILE}\\N{SITE_SHORT}")
    Path(path).write_text(head + "\n".join(ev), encoding="utf-8")


def build_explainer(work, segments, slides, scenes, W, H, name, title, intro=3.2, outro=4.5):
    bg = make_bg(work, W, H, name)
    narr = sum(d for _, _, d in segments)
    total = intro + narr + outro
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", "30", "-pix_fmt", "yuv420p"]
    # سایه‌ی ملایم: کل تصویر کمی، و پایین تصویر بیشتر تا نوشته خوانا باشد ولی محصول پیدا بماند
    soft = ("drawbox=x=0:y=0:w=iw:h=ih:color=black@0.08:t=fill,"
            "drawbox=x=0:y=ih*0.52:w=iw:h=ih*0.48:color=black@0.10:t=fill,"
            "drawbox=x=0:y=ih*0.64:w=iw:h=ih*0.36:color=black@0.14:t=fill,"
            "drawbox=x=0:y=ih*0.76:w=iw:h=ih*0.24:color=black@0.18:t=fill,"
            "drawbox=x=0:y=ih*0.88:w=iw:h=ih*0.12:color=black@0.18:t=fill")

    def graphic(d, tag):
        out = f"g_{name}_{tag}.mp4"
        frames = int(round(d * 30)) + 2
        vf = f"zoompan=z='min(1+0.0004*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=30"
        run(["ffmpeg", "-y", "-i", bg, "-vf", vf, "-t", f"{d:.3f}"] + enc + [out], cwd=work)
        return out

    def shot(kind, src, d, tag, k):
        out = f"s_{name}_{tag}.mp4"
        if kind == "vid":
            vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,{soft}"
            run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", src, "-t", f"{d:.3f}", "-vf", vf, "-an"] + enc + [out], cwd=work)
        else:
            frames = int(round(d * 30)) + 2
            sw, sh = int(W * 1.5) // 2 * 2, int(H * 1.5) // 2 * 2
            z = "min(zoom+0.0009,1.15)" if k % 2 == 0 else "if(eq(on,1),1.15,max(zoom-0.0009,1.0))"
            vf = (f"scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh},"
                  f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=30,{soft}")
            run(["ffmpeg", "-y", "-i", src, "-vf", vf, "-t", f"{d:.3f}"] + enc + [out], cwd=work)
        return out

    clips, kinds = [graphic(intro, "intro")], []
    for i, (text, _, d) in enumerate(segments):
        shots = scenes[i] if i < len(scenes) else []
        if isinstance(shots, tuple):
            shots = [shots]
        shots = [s for s in (shots or []) if s][:3]
        k = len(shots)
        while k > 1 and d / k < 1.8:
            k -= 1
        shots = shots[:k]
        made = []
        try:
            for j, (kind, src) in enumerate(shots):
                dj = d / k if j < k - 1 else d - (d / k) * (k - 1)
                dj = max(round(dj * 30) / 30, 0.4)
                made.append(shot(kind, src, dj, f"{i}_{j}", i + j))
        except Exception as e:
            print("scene failed, using graphic:", i, str(e)[:100])
            made = []
        if made:
            clips += made
            kinds.append("media")
        else:
            clips.append(graphic(d, f"seg{i}"))
            kinds.append("graphic")
    clips.append(graphic(outro, "outro"))
    print("scene kinds:", kinds)
    (work / f"list_{name}.txt").write_text("".join(f"file '{c}'\n" for c in clips))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"list_{name}.txt", "-c", "copy", f"base_{name}.mp4"], cwd=work)
    make_explainer_ass(segments, slides, W, H, work / f"sub_{name}.ass", title, intro, outro, kinds)
    ms = int(intro * 1000)
    fc = (f"[1:a]adelay={ms}:all=1,apad=whole_dur={total:.2f}[a];[0:v]ass=sub_{name}.ass,format=yuv420p[v]")
    out = f"{name}.mp4"
    run(["ffmpeg", "-y", "-i", f"base_{name}.mp4", "-i", "audio.wav", "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], cwd=work)
    return work / out


def make_videos(art, sentences, scene_ids, lib_by_id, work):
    segments = synth_all(sentences, work)
    segments = [(t, w, max(round(d * 30) / 30, 0.5)) for t, w, d in segments]
    slides = art.get("slides") or []
    scenes = []
    for i in range(len(segments)):
        ids = scene_ids[i] if i < len(scene_ids) else []
        if not isinstance(ids, list):
            ids = [ids] if ids else []
        shots = []
        for sid in ids[:3]:
            item = lib_by_id.get(sid)
            if not item:
                continue
            try:
                name = f"lib_{item['id']}" + (".mp4" if item["type"] == "video" else ".jpg")
                if not (work / name).exists():
                    download(item["url"], work / name)
                shots.append(("vid" if item["type"] == "video" else "img", name))
            except Exception as e:
                print("library download failed:", str(e)[:100])
        scenes.append(shots)
    print("shots per sentence:", [len(s) for s in scenes])
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
