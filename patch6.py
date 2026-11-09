# patch6.py: سرعت و پایداری: تلاش کمتر روی مدل شلوغ، ذخیره‌ی زودهنگام موضوع، و رد شدن از کارهای غیرضروری اگر دیر شد
import faulthandler, time as _t, requests as _rq

_START = _t.time()
_CUR = {}
faulthandler.cancel_dump_traceback_later()
faulthandler.dump_traceback_later(1560, exit=True)      # ۲۶ دقیقه


def gemini(prompt, retries=2):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.6, "maxOutputTokens": 30000, "responseMimeType": "application/json"}}
    deadline = _t.time() + 420           # هر درخواست حداکثر ۷ دقیقه (روی همه‌ی مدل‌ها)
    for model in candidate_models()[:4]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for i in range(retries):
            if _t.time() > deadline:
                raise RuntimeError("Gemini: time budget for this request exceeded")
            try:
                r = requests.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=(20, 200))
                if r.status_code in (404, 400):
                    print("model unavailable:", model, r.status_code)
                    break
                if r.status_code == 429:
                    print("quota/rate limit on", model, "- next model")
                    _t.sleep(10)
                    break
                if r.status_code >= 500:
                    print("gemini busy:", model, r.status_code)
                    _t.sleep(3)
                    if i == 0:
                        continue
                    break
                r.raise_for_status()
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
                print("using model:", model)
                return json.loads(text, strict=False)
            except _rq.exceptions.Timeout:
                print("gemini timeout:", model, "- next model")
                break
            except Exception as e:
                print("gemini retry", model, i, str(e)[:150])
                _t.sleep(3)
    raise RuntimeError("Gemini failed with all models")


_prev_pick_topic = pick_topic
_prev_set_rank_math = set_rank_math
_prev_create_web_story = create_web_story


def pick_topic(state):
    _CUR["state"] = state
    return _prev_pick_topic(state)


def set_rank_math(post_id, topic, art, image_url):
    _prev_set_rank_math(post_id, topic, art, image_url)
    # بلافاصله بعد از ساخت مقاله، موضوع را «انجام‌شده» ثبت می‌کند (حتی اگر ادامه‌ی کار قطع شود)
    try:
        st = _CUR.get("state")
        if st is not None and topic["title"] not in st["done"]:
            st["done"].append(topic["title"])
            save_state(st)
            print("state saved early")
    except Exception as e:
        print("early state save failed:", str(e)[:100])


def create_web_story(*a, **k):
    if _t.time() - _START > 1080:
        print("web story skipped: running late")
        return False
    return _prev_create_web_story(*a, **k)
