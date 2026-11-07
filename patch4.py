# patch4.py: ۱) سایه‌ی نرم و بدون شیار پایین فیلم  ۲) کادر پیش‌نمایش ۵ ثانیه‌ای فیلم داخل مقاله با لینک به آپارات
import json, re, subprocess, shutil
from pathlib import Path

_old_make_explainer_ass = make_explainer_ass
_old_make_videos = make_videos
_old_build_content = build_content
_PREVIEW = {}


# ---------------------------------------------------------------- سایه‌ی نرم (بدون پله و شیار)
def make_shade(work, W, H):
    out = "shade.png"
    expr = "255*(0.06+0.52*pow(max(0,(Y/H-0.45)/0.55),1.6))"
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H},format=gbrap",
         "-vf", f"geq=r=0:g=0:b=0:a='{expr}',format=rgba", "-frames:v", "1", out], cwd=work)
    return out


def make_explainer_ass(segments, slides, W, H, path, title, intro, outro, kinds=None):
    _old_make_explainer_ass(segments, slides, W, H, path, title, intro, outro, kinds)
    t = Path(path).read_text(encoding="utf-8")
    # زیرنویس: به جای کادر نیمه‌شفاف (که بین خط‌ها شیار می‌اندازد) متن با حاشیه‌ی نرم
    t = t.replace(",&H78000000,&H96000000,1,0,0,0,100,100,0,0,3,3,0,2,", ",&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,3,1,2,")
    Path(path).write_text(t, encoding="utf-8")


def build_explainer(work, segments, slides, scenes, W, H, name, title, intro=3.2, outro=4.5):
    bg = make_bg(work, W, H, name)
    shade = make_shade(work, W, H)
    narr = sum(d for _, _, d in segments)
    total = intro + narr + outro
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30", "-pix_fmt", "yuv420p"]

    def graphic(d, tag):
        out = f"g_{name}_{tag}.mp4"
        frames = int(round(d * 30)) + 2
        vf = f"zoompan=z='min(1+0.0004*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=30"
        run(["ffmpeg", "-y", "-i", bg, "-vf", vf, "-t", f"{d:.3f}"] + enc + [out], cwd=work)
        return out

    def shot(kind, src, d, tag, k):
        out = f"s_{name}_{tag}.mp4"
        if kind == "vid":
            chain = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30[b]"
            pre = ["-stream_loop", "-1", "-i", src]
        else:
            frames = int(round(d * 30)) + 2
            sw, sh = int(W * 1.5) // 2 * 2, int(H * 1.5) // 2 * 2
            z = "min(zoom+0.0009,1.15)" if k % 2 == 0 else "if(eq(on,1),1.15,max(zoom-0.0009,1.0))"
            chain = (f"[0:v]scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh},"
                     f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=30[b]")
            pre = ["-i", src]
        fc = chain + ";[b][1:v]overlay=0:0:shortest=1,format=yuv420p[v]"
        run(["ffmpeg", "-y"] + pre + ["-loop", "1", "-framerate", "30", "-i", shade, "-filter_complex", fc,
                                      "-map", "[v]", "-t", f"{d:.3f}", "-an"] + enc + [out], cwd=work)
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
         "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], cwd=work)
    return work / out


# ---------------------------------------------------------------- کادر پیش‌نمایش فیلم داخل مقاله
def _brand_hex():
    r, g, b = BG_BOTTOM
    return "#%02x%02x%02x" % (r, g, b)


def video_card(preview, poster, link, label, links_html=""):
    href = link or "#"
    return (
        '<!-- wp:html -->\n<!--VCARD-START-->\n'
        f'<div data-preview="{preview}" data-poster="{poster}" style="max-width:100%;margin:0 0 22px;'
        f'border:2px solid {_brand_hex()};border-radius:14px;overflow:hidden;background:#101820">'
        f'<a href="{href}" target="_blank" rel="noopener" style="display:block;position:relative;text-decoration:none">'
        f'<video autoplay muted loop playsinline preload="metadata" poster="{poster}" src="{preview}" '
        'style="display:block;width:100%;height:auto"></video>'
        '<span style="position:absolute;left:50%;top:50%;width:76px;height:76px;margin:-38px 0 0 -38px;border-radius:50%;'
        'background:rgba(0,0,0,.55);border:3px solid #fff"></span>'
        '<span style="position:absolute;left:50%;top:50%;margin:-16px 0 0 -10px;border-left:28px solid #fff;'
        'border-top:17px solid transparent;border-bottom:17px solid transparent"></span></a>'
        f'<div style="padding:12px 14px;background:#ffffff;color:#1b1b1b;text-align:center;font-weight:bold;line-height:1.9">'
        f'<a href="{href}" target="_blank" rel="noopener" style="color:#0b5cab;text-decoration:none">▶ {label}</a>'
        f'{("<div style=font-weight:normal;font-size:15px>" + links_html + "</div>") if links_html else ""}</div></div>\n'
        '<!--VCARD-END-->\n<!-- /wp:html -->\n')


def make_videos(art, sentences, scene_ids, lib_by_id, work):
    _PREVIEW.clear()
    vh = _old_make_videos(art, sentences, scene_ids, lib_by_id, work)
    try:
        slug = re.sub(r"[^a-z0-9-]+", "-", str(art.get("slug", "")).lower()).strip("-")[:50] or "article"
        pv = work / f"{slug}-video-preview.mp4"
        run(["ffmpeg", "-y", "-ss", "3.4", "-t", "5", "-i", str(vh), "-vf", "scale=854:-2", "-an", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(pv)])
        pj = work / f"{slug}-video-poster.jpg"
        run(["ffmpeg", "-y", "-ss", "4.2", "-i", str(vh), "-frames:v", "1", "-vf", "scale=854:-2", "-q:v", "4", str(pj)])
        _, purl = upload(pv, "video/mp4", f"{art['title']} - پیش‌نمایش ویدیو", f"پیش‌نمایش ویدیوی {art['title']}")
        _, jurl = upload(pj, "image/jpeg", f"{art['title']} - ویدیو", f"ویدیوی {art['title']}")
        _PREVIEW.update({"preview": purl, "poster": jurl})
        print("video preview uploaded")
    except Exception as e:
        print("video preview failed:", str(e)[:150])
    return vh


def build_content(art, figs, with_placeholder, banner_url="", related=None):
    body = _old_build_content(art, figs, False, banner_url, related)
    if with_placeholder and _PREVIEW:
        return video_card(_PREVIEW["preview"], _PREVIEW["poster"], "", "ویدیوی کامل به‌زودی در آپارات و یوتیوب") + body
    if with_placeholder:
        return PLACEHOLDER + body
    return body


# ---------------------------------------------------------------- مرحله‌ی آخر: وصل کردن لینک آپارات و یوتیوب
def attach():
    pid = os.environ.get("POST_ID", "").strip()
    aparat = os.environ.get("APARAT_URL", "").strip()
    embed = os.environ.get("APARAT_EMBED", "").strip()
    yt = os.environ.get("YOUTUBE_URL", "").strip()
    shorts = os.environ.get("SHORTS_URL", "").strip()
    publish = os.environ.get("PUBLISH", "no").strip().lower() == "yes"
    if not pid:
        raise SystemExit("POST_ID is empty")
    r = requests.get(f"{API}/posts/{pid}", params={"context": "edit"}, auth=AUTH, timeout=60)
    r.raise_for_status()
    raw = r.json()["content"]["raw"]
    link = aparat or yt or shorts
    label = "مشاهده‌ی ویدیوی کامل در آپارات" if aparat else ("مشاهده‌ی ویدیوی کامل در یوتیوب" if yt else "مشاهده‌ی ویدیوی کامل")
    links = []
    if aparat:
        links.append(f'<a href="{aparat}" target="_blank" rel="noopener" style="color:#0b5cab">آپارات</a>')
    if yt:
        links.append(f'<a href="{yt}" target="_blank" rel="noopener" style="color:#0b5cab">یوتیوب</a>')
    if shorts:
        links.append(f'<a href="{shorts}" target="_blank" rel="noopener" style="color:#0b5cab">نسخه کوتاه (Shorts)</a>')
    links_html = " | ".join(links)
    card_pat = r"<!-- wp:html -->\s*<!--VCARD-START-->.*?<!--VCARD-END-->\s*<!-- /wp:html -->"
    old_pat = r"<!-- wp:html -->\s*<div[^>]*dashed[^>]*>.*?</div>\s*<!-- /wp:html -->"
    mc = re.search(card_pat, raw, flags=re.S)
    if embed:
        block = (f"<!-- wp:html -->\n<div style=\"max-width:100%;margin:0 0 18px\">{embed}</div>\n"
                 + (f"<p style=\"margin:0 0 18px\">🎬 {links_html}</p>\n" if links_html else "") + "<!-- /wp:html -->\n")
    elif mc:
        pv = re.search(r'data-preview="([^"]+)"', mc.group(0))
        pj = re.search(r'data-poster="([^"]+)"', mc.group(0))
        block = video_card(pv.group(1) if pv else "", pj.group(1) if pj else "", link, label, links_html)
    else:
        block = ("<!-- wp:html -->\n" + (f"<p style=\"margin:0 0 18px\">🎬 {links_html}</p>\n" if links_html else "") + "<!-- /wp:html -->\n")
    if mc:
        new = re.sub(card_pat, lambda _m: block, raw, count=1, flags=re.S)
    elif re.search(old_pat, raw, flags=re.S):
        new = re.sub(old_pat, lambda _m: block, raw, count=1, flags=re.S)
    else:
        new = block + raw
    payload = {"content": new}
    if publish:
        payload["status"] = "publish"
    r = requests.post(f"{API}/posts/{pid}", auth=AUTH, json=payload, timeout=120)
    r.raise_for_status()
    print("updated post", pid, "| published:", publish, "|", r.json().get("link"))
