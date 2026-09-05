#!/usr/bin/env python3
"""Publish cleaned Egypt posts to https://rukn-eltatawer.com/eg via REST + WPVibe CLI."""

from __future__ import annotations

import base64
import json
import os
import ssl
import sys
import time
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
AUTH = base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()


def req(route: str, method: str = "GET", data=None, timeout: int = 90):
    url = f"{BASE}?rest_route={route}"
    body = None
    headers = {
        "Authorization": f"Basic {AUTH}",
        "Accept": "application/json",
        "User-Agent": "rukn-egypt-publisher/1.0",
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


def ensure_term(taxonomy: str, name: str, slug: str, state: dict) -> int | None:
    key = f"{taxonomy}:{slug}"
    if key in state["terms"]:
        return state["terms"][key]
    route = {
        "category": "/wp/v2/categories",
        "cities": "/wp/v2/cities",
        "service_categories": "/wp/v2/service_categories",
        "post_tag": "/wp/v2/tags",
    }.get(taxonomy)
    if route:
        st, data = req(route, "POST", {"name": name, "slug": slug})
        if st in (200, 201) and isinstance(data, dict) and data.get("id"):
            state["terms"][key] = data["id"]
            save_state(state)
            return data["id"]
        if st == 400 and isinstance(data, dict):
            # already exists
            search = req(f"{route}&{urllib.parse.urlencode({'slug': slug, 'per_page': 1})}")
            if search[0] == 200 and isinstance(search[1], list) and search[1]:
                state["terms"][key] = search[1][0]["id"]
                save_state(state)
                return state["terms"][key]
    # CLI fallback
    st, data = cli(
        f"wp term create {taxonomy} {json.dumps(name, ensure_ascii=False)} --slug={slug} --porcelain",
        True,
    )
    if isinstance(data, dict) and data.get("exit_code") == 0 and data.get("stdout"):
        try:
            tid = int(str(data["stdout"]).strip().split()[0])
            state["terms"][key] = tid
            save_state(state)
            return tid
        except Exception:
            pass
    st, data = cli(f"wp term list {taxonomy} --search={json.dumps(name, ensure_ascii=False)} --format=json")
    if isinstance(data, dict) and data.get("stdout"):
        try:
            rows = json.loads(data["stdout"])
            if rows:
                state["terms"][key] = int(rows[0]["term_id"])
                save_state(state)
                return state["terms"][key]
        except Exception:
            pass
    print(f"WARN term failed {taxonomy} {name} {st} {data}")
    return None


def upsert_post(item: dict, state: dict) -> int | None:
    slug = item["post_name"]
    if slug in state["posts"]:
        post_id = state["posts"][slug]
        st, data = req(
            f"/wp/v2/posts/{post_id}",
            "POST",
            {
                "title": item["post_title"],
                "content": item["post_content"],
                "status": "publish",
                "slug": slug,
                "comment_status": "closed",
                "ping_status": "closed",
            },
        )
        if st not in (200, 201):
            print(f"UPDATE FAIL {slug} {st} {data}")
            return post_id
    else:
        payload = {
            "title": item["post_title"],
            "content": item["post_content"],
            "status": "publish",
            "slug": slug,
            "comment_status": "closed",
            "ping_status": "closed",
        }
        st, data = req("/wp/v2/posts", "POST", payload)
        if st not in (200, 201) or not isinstance(data, dict):
            print(f"CREATE FAIL {slug} {st} {data}")
            return None
        post_id = data["id"]
        state["posts"][slug] = post_id
        save_state(state)

    # Rank Math + contact meta
    metas = {
        "rank_math_title": item.get("rank_math_title") or "",
        "rank_math_description": item.get("rank_math_description") or "",
        "rank_math_focus_keyword": item.get("rank_math_focus_keyword") or "",
        "rank_math_robots": "index,follow",
        "whatsapp_number": WHATSAPP,
        "country": item.get("country") or "مصر",
    }
    for key, value in metas.items():
        cli(
            f"wp post meta update {post_id} {key} {json.dumps(value, ensure_ascii=False)} --force",
            True,
        )

    city_tax = "cities"
    city_name = item.get("city") or ""
    if city_name:
        info = city_info(item.get("city_ar") or city_name)
        slug_city = info.get("slug") or slug
        tid = ensure_term(city_tax, city_name, slug_city, state)
        if tid:
            cli(f"wp post term set {post_id} cities {tid} --by=id", True)

    cat_name = item.get("categories") or ""
    cat_slug = item.get("category_slug") or "egypt-services"
    if cat_name:
        cid = ensure_term("category", cat_name, cat_slug, state)
        if cid:
            cli(f"wp post term set {post_id} category {cid} --by=id", True)
        sid = ensure_term("service_categories", cat_name, cat_slug, state)
        if sid:
            cli(f"wp post term set {post_id} service_categories {sid} --by=id", True)

    tags = [t.strip() for t in (item.get("tags") or "").split(",") if t.strip()]
    for tag in tags[:8]:
        tslug = re_slug(tag)
        tid = ensure_term("post_tag", tag, tslug, state)
        if tid:
            cli(f"wp post term add {post_id} post_tag {tid} --by=id", True)
    return post_id


def re_slug(text: str) -> str:
    import re
    import unicodedata

    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.U).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text[:60] or "tag"


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
        print("option", key, st, (data or {}).get("exit_code") if isinstance(data, dict) else data)

    # Do NOT flip pretty permalinks until /eg/.htaccess rewrites exist.
    # Pretty URLs currently 404 at LiteSpeed and would break working ?p= / ?name= links.


def create_pages(state: dict, posts: list[dict]) -> None:
    html_map = []
    for item in posts:
        html_map.append(
            f'<li><a href="{BASE.replace("/index.php","")}/?name={item["post_name"]}">{item["post_title"]}</a></li>'
        )
    pages = {
        "contact-us": {
            "title": "تواصل معنا — ركن التطور مصر / Contact Egypt",
            "content": f"""<h1>تواصل مع ركن التطور في مصر</h1>
<p>المعاينة والمقايسات بالجنيه المصري. أرسل المنطقة ونوع الوحدة ووصف العمل عبر واتساب.</p>
<p><a href="https://wa.me/{WHATSAPP}?text=%D9%85%D8%B1%D8%AD%D8%A8%D8%A7%D9%8B%20%D8%B1%D9%83%D9%86%20%D8%A7%D9%84%D8%AA%D8%B7%D9%88%D8%B1%20%D9%85%D8%B5%D8%B1">واتساب مصر</a></p>
<h2>Contact in English</h2>
<p>Inspection and written estimates in EGP. Message the Egypt desk on WhatsApp with your city, compound, and job.</p>
""",
        },
        "about-egypt": {
            "title": "عن ركن التطور في مصر / About",
            "content": """<h1>ركن التطور في مصر</h1>
<p>نقدم التشطيبات والديكور والحرفيين والصيانة داخل محافظات مصر، بمحتوى وعقود وخامات مناسبة للسوق المصري وليس نسخة من الإمارات أو السعودية.</p>
<p>Rukn El Tatawer in Egypt delivers finishing, trades and maintenance for Egyptian homes, priced in EGP.</p>
""",
        },
        "privacy-egypt": {
            "title": "سياسة الخصوصية / Privacy",
            "content": """<h1>سياسة الخصوصية</h1>
<p>نستخدم بيانات التواصل فقط للرد على طلب الخدمة داخل مصر. لا نبيع البيانات لأطراف إعلانية.</p>
<p>Contact details are used only to fulfil Egypt service requests.</p>
""",
        },
        "html-sitemap": {
            "title": "خريطة الموقع — مصر / HTML Sitemap",
            "content": "<h1>كل صفحات ركن التطور مصر</h1><ul>"
            + "".join(html_map)
            + "</ul>",
        },
    }
    for slug, page in pages.items():
        if slug in state["pages"]:
            pid = state["pages"][slug]
            req(
                f"/wp/v2/pages/{pid}",
                "POST",
                {"title": page["title"], "content": page["content"], "status": "publish", "slug": slug},
            )
            continue
        st, data = req(
            "/wp/v2/pages",
            "POST",
            {"title": page["title"], "content": page["content"], "status": "publish", "slug": slug, "comment_status": "closed"},
        )
        if st in (200, 201) and isinstance(data, dict):
            state["pages"][slug] = data["id"]
            save_state(state)
            print("page", slug, data["id"])
        else:
            print("PAGE FAIL", slug, st, data)


def delete_hello_world() -> None:
    st, data = req("/wp/v2/posts/1", "DELETE", {"force": True})
    print("delete hello", st, data if not isinstance(data, dict) else data.get("deleted") or data.get("code"))


def build_menu(state: dict) -> None:
    st, data = cli("wp menu create Egypt --porcelain", True)
    print("menu", st, data)
    home = "https://rukn-eltatawer.com/eg/"
    cli(f"wp menu item add-custom Egypt الرئيسية {home}", True)
    if "contact-us" in state["pages"]:
        cli(f"wp menu item add-post Egypt {state['pages']['contact-us']}", True)
    if "about-egypt" in state["pages"]:
        cli(f"wp menu item add-post Egypt {state['pages']['about-egypt']}", True)
    if "html-sitemap" in state["pages"]:
        cli(f"wp menu item add-post Egypt {state['pages']['html-sitemap']}", True)
    cli("wp menu location assign Egypt main-menu", True)


def main() -> None:
    if not PASSWORD:
        raise SystemExit("Set WP_EG_APP_PASSWORD to the WordPress application password.")
    payload = json.loads(DIST.read_text(encoding="utf-8"))
    state = load_state()
    print("configure site…")
    configure_site()
    items = payload["arabic"] + payload["english"]
    print(f"publishing {len(items)} posts")
    ok = 0
    for i, item in enumerate(items, 1):
        pid = upsert_post(item, state)
        if pid:
            ok += 1
        if i % 25 == 0:
            print(f"  {i}/{len(items)} ok={ok}")
            save_state(state)
        time.sleep(0.05)
    save_state(state)
    print("pages…")
    create_pages(state, payload["arabic"] + payload["english"])
    build_menu(state)
    delete_hello_world()
    cli("wp cache flush", True)
    cli("wp litespeed-purge all", True)
    print(f"DONE ok={ok}/{len(items)} state={STATE}")


if __name__ == "__main__":
    main()
