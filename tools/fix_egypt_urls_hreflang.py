#!/usr/bin/env python3
"""Fix live post/page URLs and hreflang. Does NOT change SEO titles."""

from __future__ import annotations

import base64
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request

BASE = "https://rukn-eltatawer.com/eg/index.php"
USER = os.environ.get("WP_EG_USER", "melsaad")
PASSWORD = os.environ.get("WP_EG_APP_PASSWORD", "")
HOME = "https://www.rukn-eltatawer.com/eg"
CTX = ssl.create_default_context()

HREFLANG_RE = re.compile(
    r'<link rel="alternate" href="https://(?:www\.)?rukn-eltatawer\.com/eg/(?:en/)?'
    r'([^"\']+)" hreflang="ar"\s*/>\s*'
    r'<link rel="alternate" href="https://(?:www\.)?rukn-eltatawer\.com/eg/(?:en/)?'
    r'([^"\']+)" hreflang="en"\s*/>'
    r'(?:\s*<link rel="alternate" href="[^"]+" hreflang="x-default"\s*/>)?',
    re.I,
)
EN_PATH_RE = re.compile(
    r"https://www\.rukn-eltatawer\.com/eg/(?!en/)([^\"'\s<>]+-en)/?",
    re.I,
)


def req(route, method="GET", data=None, timeout=90):
    url = f"{BASE}?rest_route={route}"
    body = None
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode(),
        "Accept": "application/json",
        "User-Agent": "rukn-egypt-urls/1.0",
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
                time.sleep(4 + attempt * 4)
                last = (exc.code, "508")
                continue
            try:
                return exc.code, json.loads(raw)
            except Exception:
                return exc.code, raw.decode("utf-8", "replace")[:300]
        except Exception as exc:
            time.sleep(2 + attempt)
            last = (0, str(exc))
    return last or (0, "retries exhausted")


def cli(command, confirm_write=False):
    return req("/wpvibe/v1/cli/run", "POST", {"command": command, "confirm_write": confirm_write})


def assert_no_title(payload, context):
    for key in payload:
        if key in {"title", "rank_math_title", "post_title"} or str(key).endswith("_title"):
            raise RuntimeError(f"refusing {key} in {context}")


def rewrite_html(html: str, slug: str) -> str:
    html = html.replace("https://rukn-eltatawer.com/eg", HOME)
    html = EN_PATH_RE.sub(lambda m: f"{HOME}/en/{m.group(1)}/", html)
    base = slug[:-3] if slug.endswith("-en") else slug
    ar = f"{HOME}/{base}/"
    en = f"{HOME}/en/{base}-en/"
    block = (
        f'<link rel="alternate" href="{ar}" hreflang="ar" />'
        f'<link rel="alternate" href="{en}" hreflang="en" />'
        f'<link rel="alternate" href="{ar}" hreflang="x-default" />'
    )
    if HREFLANG_RE.search(html):
        html = HREFLANG_RE.sub(block, html)
    return html


def snapshot(pid):
    st, data = cli(f"wp post meta get {pid} rank_math_title")
    st2, post = req(f"/wp/v2/posts/{pid}&_fields=id,title")
    return {
        "rank_math_title": ((data or {}).get("stdout") or "").strip(),
        "wp_title": ((post or {}).get("title") or {}).get("rendered") if isinstance(post, dict) else None,
    }


def walk(route, extra_fields=""):
    page = 1
    while True:
        st, batch = req(
            f"{route}&per_page=50&page={page}&context=edit&_fields=id,slug,content{extra_fields}"
        )
        if st != 200 or not isinstance(batch, list) or not batch:
            break
        yield from batch
        if len(batch) < 50:
            break
        page += 1
        time.sleep(0.15)


def main():
    if not PASSWORD:
        raise SystemExit("Set WP_EG_APP_PASSWORD")
    sample = {}
    for pid in (677, 256):
        sample[pid] = snapshot(pid)
    print("SEO titles before", json.dumps(sample, ensure_ascii=False), flush=True)

    changed = fail = scanned = 0
    for kind, route in (("post", "/wp/v2/posts"), ("page", "/wp/v2/pages")):
        for item in walk(route):
            scanned += 1
            slug = item.get("slug") or ""
            raw = ""
            if isinstance(item.get("content"), dict):
                raw = item["content"].get("raw") or ""
            if not raw:
                continue
            new = rewrite_html(raw, slug)
            if new == raw:
                continue
            payload = {"content": new}
            assert_no_title(payload, f"{kind} {item['id']}")
            st, data = req(f"{route}/{item['id']}", "POST", payload)
            if st in (200, 201):
                changed += 1
            else:
                fail += 1
                print("fail", kind, item["id"], slug, st, str(data)[:120], flush=True)
            if scanned % 50 == 0:
                print(f"  scanned={scanned} changed={changed} fail={fail}", flush=True)
            time.sleep(0.05)
    print(f"content scanned={scanned} changed={changed} fail={fail}", flush=True)

    cli(
        'wp option patch insert rewrite_rules "robots\\.txt$" "index.php?robots=1"',
        True,
    )
    cli("wp cache purge", True)
    cli("wp litespeed-purge all", True)

    after = {pid: snapshot(pid) for pid in sample}
    print("SEO titles after", json.dumps(after, ensure_ascii=False), flush=True)
    for pid, before in sample.items():
        a = after.get(pid) or {}
        if before.get("rank_math_title") != a.get("rank_math_title"):
            print("ERROR title changed", pid, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
