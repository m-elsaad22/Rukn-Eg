#!/usr/bin/env python3
"""REST-only Egypt follow-up: H1->H2, featured images, HTML sitemap. Never writes titles."""

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


def req(route, method="GET", data=None, timeout=90):
    url = f"{BASE}?rest_route={route}"
    body = None
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode(),
        "Accept": "application/json",
        "User-Agent": "rukn-egypt-rest-fix/1.0",
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
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, raw.decode("utf-8", "replace")[:400]


def cli(command, confirm_write=False):
    return req("/wpvibe/v1/cli/run", "POST", {"command": command, "confirm_write": confirm_write})


def assert_no_title(payload, context):
    for key in payload:
        if key in {"title", "rank_math_title", "post_title"} or str(key).endswith("_title"):
            raise RuntimeError(f"refusing {key} in {context}")


def main():
    if not PASSWORD:
        raise SystemExit("Set WP_EG_APP_PASSWORD")

    sample_slugs = {
        "apartment-finishing-fifth-settlement-en",
        "apartment-finishing-fifth-settlement",
    }
    sample_ids = []
    titles_before = {}

    h1_ok = thumb_ok = fail = 0
    all_posts = []
    page = 1
    while True:
        st, batch = req(
            f"/wp/v2/posts&per_page=50&page={page}&context=edit&_fields=id,slug,content,featured_media,title"
        )
        if st != 200 or not isinstance(batch, list) or not batch:
            print("list stop", page, st, flush=True)
            break
        print(f"page {page} n={len(batch)}", flush=True)
        for p in batch:
            pid = p["id"]
            slug = p.get("slug") or ""
            wp_title = (p.get("title") or {}).get("raw") or (p.get("title") or {}).get("rendered")
            if slug in sample_slugs:
                sample_ids.append(pid)
                st_m, meta = cli(f"wp post meta get {pid} rank_math_title")
                titles_before[pid] = {
                    "slug": slug,
                    "wp_title": wp_title,
                    "rank_math_title": ((meta or {}).get("stdout") or "").strip(),
                }
            raw = ""
            if isinstance(p.get("content"), dict):
                raw = p["content"].get("raw") or ""
            payload = {}
            if "<h1>" in raw or "</h1>" in raw:
                payload["content"] = raw.replace("<h1>", "<h2>").replace("</h1>", "</h2>")
            if not p.get("featured_media"):
                payload["featured_media"] = FEATURED_ID
            if payload:
                assert_no_title(payload, f"post {pid}")
                st2, data = req(f"/wp/v2/posts/{pid}", "POST", payload)
                if st2 in (200, 201):
                    if "content" in payload:
                        h1_ok += 1
                    if "featured_media" in payload:
                        thumb_ok += 1
                else:
                    fail += 1
                    print("fail", pid, slug, st2, str(data)[:140], flush=True)
            all_posts.append({"id": pid, "slug": slug, "title": wp_title})
        if len(batch) < 50:
            break
        page += 1
        time.sleep(0.05)

    print(f"posts={len(all_posts)} h1={h1_ok} thumbs={thumb_ok} fail={fail}", flush=True)
    print("titles before", json.dumps(titles_before, ensure_ascii=False), flush=True)

    st, pages = req("/wp/v2/pages&per_page=20&_fields=id,slug")
    sitemap_id = None
    for p in pages if isinstance(pages, list) else []:
        if p.get("slug") == "html-sitemap":
            sitemap_id = p["id"]
    items = []
    for p in all_posts:
        slug = p["slug"]
        href = f"{HOME}/en/{slug}/" if slug.endswith("-en") else f"{HOME}/{slug}/"
        items.append(f'<li><a href="{href}">{p["title"]}</a></li>')
    if sitemap_id:
        payload = {"content": "<h2>صفحات ركن التطور مصر</h2><ul>" + "".join(items) + "</ul>"}
        assert_no_title(payload, "sitemap")
        st, data = req(f"/wp/v2/pages/{sitemap_id}", "POST", payload)
        cli(f"wp post meta update {sitemap_id} rank_math_robots noindex,follow --force", True)
        print("sitemap", sitemap_id, st, "links", len(items), flush=True)

    cli("wp cache purge", True)
    cli("wp litespeed-purge all", True)

    titles_after = {}
    for pid in sample_ids:
        st, post = req(f"/wp/v2/posts/{pid}&_fields=id,slug,title,featured_media")
        st_m, meta = cli(f"wp post meta get {pid} rank_math_title")
        titles_after[pid] = {
            "slug": (post or {}).get("slug"),
            "wp_title": ((post or {}).get("title") or {}).get("rendered"),
            "featured_media": (post or {}).get("featured_media"),
            "rank_math_title": ((meta or {}).get("stdout") or "").strip(),
        }
    print("titles after", json.dumps(titles_after, ensure_ascii=False), flush=True)
    for pid, before in titles_before.items():
        after = titles_after.get(pid) or {}
        if before["rank_math_title"] != after.get("rank_math_title"):
            print("ERROR rank_math_title changed", pid, flush=True)
        if before["wp_title"] not in {after.get("wp_title"), None}:
            # rendered may entity-encode; compare loosely
            if before["wp_title"] != after.get("wp_title"):
                print("WARN wp_title differs", pid, before["wp_title"], after.get("wp_title"), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
