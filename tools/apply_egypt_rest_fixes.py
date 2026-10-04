#!/usr/bin/env python3
"""Gentle Egypt follow-up: H1->H2 via content/edit, thumbs via REST. Never writes titles."""

from __future__ import annotations

import base64
import json
import os
import ssl
import time
import urllib.error
import urllib.request

BASE = "https://rukn-eltatawer.com/eg/index.php"
USER = os.environ.get("WP_EG_USER", "melsaad")
PASSWORD = os.environ.get("WP_EG_APP_PASSWORD", "")
HOME = "https://www.rukn-eltatawer.com/eg"
FEATURED_ID = 1742
CTX = ssl.create_default_context()


def req(route, method="GET", data=None, timeout=60):
    url = f"{BASE}?rest_route={route}"
    body = None
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode(),
        "Accept": "application/json",
        "User-Agent": "rukn-egypt-rest-fix/1.1",
    }
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    last = None
    for attempt in range(5):
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, context=CTX, timeout=timeout) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            if exc.code == 508:
                wait = 4 + attempt * 5
                print(f"  508 {route[:70]} sleep {wait}s", flush=True)
                time.sleep(wait)
                last = (exc.code, "508")
                continue
            try:
                return exc.code, json.loads(raw)
            except Exception:
                return exc.code, raw.decode("utf-8", "replace")[:200]
        except Exception as exc:
            print(f"  err {exc} sleep", flush=True)
            time.sleep(2 + attempt)
            last = (0, str(exc))
    return last or (0, "retries exhausted")


def cli(command, confirm_write=False):
    return req("/wpvibe/v1/cli/run", "POST", {"command": command, "confirm_write": confirm_write})


def content_edit_post(post_id: int, old: str, new: str):
    return req(
        "/wpvibe/v1/content/edit",
        "POST",
        {
            "target_type": "post",
            "post_id": post_id,
            "field": "post_content",
            "old_content": old,
            "new_content": new,
            "replace_all": True,
        },
    )


def list_posts():
    posts = []
    page = 1
    while True:
        st, batch = req(f"/wp/v2/posts&per_page=100&page={page}&_fields=id,slug,featured_media,title")
        if st != 200 or not isinstance(batch, list) or not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        time.sleep(0.2)
    return posts


def main():
    if not PASSWORD:
        raise SystemExit("Set WP_EG_APP_PASSWORD")
    posts = list_posts()
    print("listed", len(posts), "thumbs", sum(1 for p in posts if p.get("featured_media")), flush=True)
    sample = [p for p in posts if p.get("slug") in (
        "apartment-finishing-fifth-settlement-en",
        "apartment-finishing-fifth-settlement",
    )]
    before = {}
    for p in sample:
        st, meta = cli(f"wp post meta get {p['id']} rank_math_title")
        before[p["id"]] = ((meta or {}).get("stdout") or "").strip()
    print("seo before", before, flush=True)

    h1 = thumbs = skipped = fail = 0
    for i, p in enumerate(posts, 1):
        pid = p["id"]
        st1, d1 = content_edit_post(pid, "<h1>", "<h2>")
        if st1 == 200 and isinstance(d1, dict) and d1.get("replaced"):
            content_edit_post(pid, "</h1>", "</h2>")
            h1 += 1
        elif st1 not in (200, 422):
            fail += 1
            print("h1 fail", pid, p.get("slug"), st1, str(d1)[:120], flush=True)
        if not p.get("featured_media"):
            payload = {"featured_media": FEATURED_ID}
            st2, d2 = req(f"/wp/v2/posts/{pid}", "POST", payload)
            if st2 in (200, 201):
                thumbs += 1
            else:
                fail += 1
                print("thumb fail", pid, p.get("slug"), st2, str(d2)[:120], flush=True)
        else:
            skipped += 1
        if i % 25 == 0:
            print(f"  {i}/{len(posts)} h1={h1} thumbs={thumbs} skip={skipped} fail={fail}", flush=True)
        time.sleep(0.08)

    items = []
    for p in posts:
        slug = p.get("slug") or ""
        title = p["title"]["rendered"] if isinstance(p.get("title"), dict) else p.get("title")
        href = f"{HOME}/en/{slug}/" if slug.endswith("-en") else f"{HOME}/{slug}/"
        items.append(f'<li><a href="{href}">{title}</a></li>')
    st, pages = req("/wp/v2/pages&per_page=20&_fields=id,slug")
    for page in pages if isinstance(pages, list) else []:
        if page.get("slug") == "html-sitemap":
            req(f"/wp/v2/pages/{page['id']}", "POST", {
                "content": "<h2>صفحات ركن التطور مصر</h2><ul>" + "".join(items) + "</ul>"
            })
            cli(f"wp post meta update {page['id']} rank_math_robots noindex,follow --force", True)
            print("sitemap", page["id"], "links", len(items), flush=True)

    cli("wp cache purge", True)
    cli("wp litespeed-purge all", True)
    after = {}
    for p in sample:
        st, meta = cli(f"wp post meta get {p['id']} rank_math_title")
        st2, post = req(f"/wp/v2/posts/{p['id']}&_fields=id,title,featured_media")
        after[p["id"]] = {
            "rank_math_title": ((meta or {}).get("stdout") or "").strip(),
            "wp_title": ((post or {}).get("title") or {}).get("rendered"),
            "featured_media": (post or {}).get("featured_media"),
        }
    print("seo after", json.dumps(after, ensure_ascii=False), flush=True)
    for pid, title in before.items():
        if after.get(pid, {}).get("rank_math_title") != title:
            print("ERROR title changed", pid, flush=True)
    print(f"DONE h1={h1} thumbs={thumbs} skip={skipped} fail={fail}", flush=True)


if __name__ == "__main__":
    main()
