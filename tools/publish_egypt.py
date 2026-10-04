#!/usr/bin/env python3
"""Publish cleaned Egypt posts to https://rukn-eltatawer.com/eg via REST + WPVibe CLI."""

from __future__ import annotations

import base64
import json
import os
import re
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from egypt_data import city_info  # noqa: E402

DIST = ROOT / "dist" / "egypt-posts.json"
STATE = ROOT / "dist" / "publish-state.json"

BASE = "https://rukn-eltatawer.com/eg/index.php"
USER = os.environ.get("WP_EG_USER", "melsaad")
PASSWORD = os.environ.get("WP_EG_APP_PASSWORD", "")
WHATSAPP = "971586634710"

CTX = ssl.create_default_context()


def _auth() -> str:
    return base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()


def req(route: str, method: str = "GET", data=None, timeout: int = 90):
    url = f"{BASE}?rest_route={route}"
    body = None
    headers = {
        "Authorization": f"Basic {_auth()}",
        "Accept": "application/json",
        "User-Agent": "rukn-egypt-publisher/1.1",
    }
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, context=CTX, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw) if raw else None
        except Exception:
            parsed = raw.decode("utf-8", "replace")[:800]
        return exc.code, parsed


def cli(command: str, confirm_write: bool = False):
    return req("/wpvibe/v1/cli/run", "POST", {"command": command, "confirm_write": confirm_write})


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"posts": {}, "terms": {}, "pages": {}}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.U).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text[:70] or "term"


def ensure_term(taxonomy: str, name: str, slug: str, state: dict) -> int | None:
    key = f"{taxonomy}:{slug}"
    if key in state["terms"]:
        return state["terms"][key]
    route = {
        "cities": "/wp/v2/cities",
        "service_categories": "/wp/v2/service_categories",
        "post_tag": "/wp/v2/tags",
    }.get(taxonomy)
    if not route:
        return None
    st, data = req(route, "POST", {"name": name, "slug": slug})
    if st in (200, 201) and isinstance(data, dict) and data.get("id"):
        state["terms"][key] = data["id"]
        return data["id"]
    st2, found = req(f"{route}&slug={urllib.parse.quote(slug)}&per_page=20")
    if st2 == 200 and isinstance(found, list):
        for row in found:
            if row.get("slug") == slug:
                state["terms"][key] = row["id"]
                return row["id"]
    print(f"WARN term {taxonomy} {name} -> {st} {data}")
    return None


def upsert_post(item: dict, state: dict, city_id: int | None, tag_ids: list[int]) -> int | None:
    slug = item["post_name"]
    payload = {
        "title": item["post_title"],
        "content": item["post_content"],
        "status": "publish",
        "slug": slug,
        "comment_status": "closed",
        "ping_status": "closed",
    }
    if city_id:
        payload["cities"] = [city_id]
    if tag_ids:
        payload["tags"] = tag_ids

    if slug in state["posts"]:
        post_id = state["posts"][slug]
        st, data = req(f"/wp/v2/posts/{post_id}", "POST", payload)
        if st not in (200, 201):
            print(f"UPDATE FAIL {slug} {st} {data}")
            return post_id
        return post_id
    st, data = req("/wp/v2/posts", "POST", payload)
    if st not in (200, 201) or not isinstance(data, dict):
        print(f"CREATE FAIL {slug} {st} {data}")
        return None
    state["posts"][slug] = data["id"]
    return data["id"]


def configure_site() -> None:
    updates = {
        "blogdescription": "خدمات التشطيبات والصيانة والحرفيين في مصر | Finishing and home services in Egypt",
        "timezone_string": "Africa/Cairo",
        "default_comment_status": "closed",
        "posts_per_page": "12",
        "whatsapp_number": WHATSAPP,
        "date_format": "j F Y",
    }
    for key, value in updates.items():
        st, data = cli(f"wp option update {key} {json.dumps(value, ensure_ascii=False)}", True)
        print("option", key, (data or {}).get("exit_code") if isinstance(data, dict) else st)


def create_pages(state: dict, posts: list[dict]) -> None:
    home = "https://rukn-eltatawer.com/eg"
    html_map = [
        f'<li lang="{item.get("lang","ar")}"><a href="{home}/?name={item["post_name"]}">{item["post_title"]}</a></li>'
        for item in posts
    ]
    pages = {
        "contact-us": {
            "title": "تواصل معنا — ركن التطور مصر / Contact Egypt",
            "content": f"""<h1>تواصل مع ركن التطور في مصر</h1>
<p>المعاينة والمقايسات بالجنيه المصري. أرسل المحافظة والحي ونوع الوحدة عبر واتساب.</p>
<p><a href="https://wa.me/{WHATSAPP}?text=%D9%85%D8%B1%D8%AD%D8%A8%D8%A7%D9%8B%20%D8%B1%D9%83%D9%86%20%D8%A7%D9%84%D8%AA%D8%B7%D9%88%D8%B1%20%D9%85%D8%B5%D8%B1">واتساب ركن التطور مصر</a></p>
<h2>English</h2>
<p>Inspection and written estimates in EGP. WhatsApp the Egypt desk with your city, compound, and job.</p>
""",
        },
        "about-egypt": {
            "title": "عن ركن التطور في مصر / About",
            "content": """<h1>ركن التطور في مصر</h1>
<p>التشطيبات والديكور والحرفيون والصيانة داخل محافظات مصر، بعقود وخامات بالجنيه المصري ومحتوى محلي وليس نسخة خليجية.</p>
<p>Rukn El Tatawer Egypt delivers finishing, trades and maintenance for Egyptian homes, priced in EGP.</p>
""",
        },
        "privacy-egypt": {
            "title": "سياسة الخصوصية / Privacy",
            "content": """<h1>سياسة الخصوصية</h1>
<p>بيانات التواصل تُستخدم للرد على طلب الخدمة داخل مصر فقط.</p>
<p>Contact details are used only to fulfil Egypt service requests.</p>
""",
        },
        "html-sitemap": {
            "title": "خريطة الموقع — مصر / HTML Sitemap",
            "content": "<h1>صفحات ركن التطور مصر</h1><ul>" + "".join(html_map) + "</ul>",
        },
    }
    for slug, page in pages.items():
        payload = {
            "title": page["title"],
            "content": page["content"],
            "status": "publish",
            "slug": slug,
            "comment_status": "closed",
        }
        if slug in state["pages"]:
            req(f"/wp/v2/pages/{state['pages'][slug]}", "POST", payload)
            continue
        st, data = req("/wp/v2/pages", "POST", payload)
        if st in (200, 201) and isinstance(data, dict):
            state["pages"][slug] = data["id"]
            save_state(state)
            print("page", slug, data["id"])
        else:
            print("PAGE FAIL", slug, st, data)


def delete_noise() -> None:
    for pid in (1, 31):
        st, data = req(f"/wp/v2/posts/{pid}&force=true", "DELETE")
        print("delete", pid, st, data.get("deleted") if isinstance(data, dict) else data)


def build_menu(state: dict) -> None:
    cli("wp menu create Egypt --porcelain", True)
    home = "https://rukn-eltatawer.com/eg/"
    cli(f"wp menu item add-custom Egypt الرئيسية {home}", True)
    for slug in ("contact-us", "about-egypt", "html-sitemap"):
        if slug in state["pages"]:
            cli(f"wp menu item add-post Egypt {state['pages'][slug]}", True)
    cli("wp menu location assign Egypt main-menu", True)


def preload_terms(items: list[dict], state: dict) -> tuple[dict, dict]:
    city_ids = {}
    seen_tags: dict[str, int] = {}
    for item in items:
        city_ar = item.get("city_ar") or (item.get("city") if item.get("lang") == "ar" else None)
        city_label = item.get("city") or ""
        if item.get("lang") == "en":
            info = city_info(item.get("city_ar") or "")
            slug = (info.get("slug") or slugify(city_label)) + "-en"
            tid = ensure_term("cities", city_label, slug, state)
            if tid and city_label:
                city_ids[city_label] = tid
            if item.get("city_ar"):
                # English posts still map via city_ar below using EN label
                city_ids[item["city_ar"] + "|en"] = tid
        else:
            info = city_info(city_label)
            tid = ensure_term("cities", city_label, info.get("slug") or slugify(city_label), state)
            if tid:
                city_ids[city_label] = tid
        cat = item.get("categories") or ""
        cslug = item.get("category_slug") or slugify(cat)
        if cat:
            ensure_term("service_categories", cat, cslug, state)
        for tag in [t.strip() for t in (item.get("tags") or "").split(",") if t.strip()][:6]:
            tslug = slugify(tag)
            if tslug not in seen_tags:
                tid = ensure_term("post_tag", tag, tslug, state)
                if tid:
                    seen_tags[tslug] = tid
    save_state(state)
    return city_ids, seen_tags


def tags_for(item: dict, seen_tags: dict) -> list[int]:
    ids = []
    for tag in [t.strip() for t in (item.get("tags") or "").split(",") if t.strip()][:6]:
        tid = seen_tags.get(slugify(tag))
        if tid:
            ids.append(tid)
    return ids


def main() -> None:
    if not PASSWORD:
        raise SystemExit("Set WP_EG_APP_PASSWORD to the WordPress application password.")
    payload = json.loads(DIST.read_text(encoding="utf-8"))
    state = load_state()
    print("configure site…")
    configure_site()
    items = payload["arabic"] + payload["english"]
    print("preload terms…")
    city_ids, seen_tags = preload_terms(items, state)
    print(f"cities={len(city_ids)} tags={len(seen_tags)} publishing {len(items)}")
    ok = 0
    for i, item in enumerate(items, 1):
        if item.get("lang") == "en" and item.get("city_ar"):
            city_id = city_ids.get(item["city_ar"] + "|en")
        else:
            city_id = city_ids.get(item.get("city") or "")
        pid = upsert_post(item, state, city_id, tags_for(item, seen_tags))
        if pid:
            ok += 1
        if i % 20 == 0:
            print(f"  {i}/{len(items)} ok={ok}")
            save_state(state)
    save_state(state)
    print("pages…")
    create_pages(state, items)
    build_menu(state)
    delete_noise()
    cli("wp cache flush", True)
    cli("wp litespeed-purge all", True)
    print(f"DONE ok={ok}/{len(items)} state={STATE}")


if __name__ == "__main__":
    main()
