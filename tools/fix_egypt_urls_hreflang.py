#!/usr/bin/env python3
"""Fix live post/page URLs and hreflang. Does NOT change SEO titles."""

from __future__ import annotations

import base64
import json
import os
import re
import socket
import ssl
import time
import urllib.error
import urllib.request

socket.setdefaulttimeout(40)

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
    for attempt in range(8):
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, context=CTX, timeout=timeout) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            if exc.code in (508, 503, 502, 429):
                wait = 6 + attempt * 7
                print(f"  HTTP {exc.code} {route[:70]} sleep {wait}s", flush=True)
                time.sleep(wait)
                last = (exc.code, str(exc.code))
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


def db_rows(sql: str) -> list:
    st, data = cli(f'wp db query "{sql}" --limit=2000')
    out = (data or {}).get("stdout") if isinstance(data, dict) else ""
    try:
        return json.loads(out or "{}").get("results") or []
    except Exception:
        print("db parse fail", st, str(data)[:200], flush=True)
        return []


def remaining_rows() -> list:
    return db_rows(
        "SELECT ID, post_name, post_type FROM ZeBDvesG5_posts "
        "WHERE post_status='publish' AND post_type IN ('post','page') "
        "AND post_content LIKE '%rukn-eltatawer.com/eg/%-en/%' "
        "AND post_content NOT LIKE '%/eg/en/%-en/%'"
    )


def content_edit(pid: int, old: str, new: str, replace_all: bool = True):
    return req(
        "/wpvibe/v1/content/edit",
        "POST",
        {
            "target_type": "post",
            "post_id": pid,
            "field": "post_content",
            "old_content": old,
            "new_content": new,
            "replace_all": replace_all,
        },
    )


def rewrite_one(row: dict) -> str:
    pid = int(row["ID"])
    slug = row.get("post_name") or ""
    base = slug[:-3] if slug.endswith("-en") else slug
    en_slug = slug if slug.endswith("-en") else f"{slug}-en"
    old_en = f"{HOME}/{en_slug}/"
    new_en = f"{HOME}/en/{en_slug}/"
    st, data = content_edit(pid, old_en, new_en, True)
    if st == 422:
        st, data = content_edit(pid, old_en.rstrip("/"), new_en.rstrip("/"), True)
    url_ok = st == 200
    if st not in (200, 422):
        print("url fail", pid, slug, st, str(data)[:140], flush=True)
        return "fail"
    st2, data2 = content_edit(
        pid,
        'hreflang="en" />',
        f'hreflang="en" /><link rel="alternate" href="{HOME}/{base}/" hreflang="x-default" />',
        False,
    )
    if st2 not in (200, 422):
        print("xd fail", pid, slug, st2, str(data2)[:140], flush=True)
        return "fail"
    if url_ok or st2 == 200:
        return "ok"
    return "skip"


def main():
    if not PASSWORD:
        raise SystemExit("Set WP_EG_APP_PASSWORD")
    sample = {}
    for pid in (677, 256):
        sample[pid] = snapshot(pid)
    print("SEO titles before", json.dumps(sample, ensure_ascii=False), flush=True)

    www_rows = db_rows(
        "SELECT ID, post_name, post_type FROM ZeBDvesG5_posts "
        "WHERE post_status='publish' AND post_type IN ('post','page') "
        "AND post_content LIKE '%://rukn-eltatawer.com/eg%'"
    )
    print("non-www candidates", len(www_rows), flush=True)
    www_ok = www_skip = www_fail = 0
    for i, row in enumerate(www_rows, 1):
        pid = int(row["ID"])
        st, data = req(
            "/wpvibe/v1/content/edit",
            "POST",
            {
                "target_type": "post",
                "post_id": pid,
                "field": "post_content",
                "old_content": "https://rukn-eltatawer.com/eg",
                "new_content": HOME,
                "replace_all": True,
            },
        )
        if st == 200:
            www_ok += 1
        elif st == 422:
            www_skip += 1
        else:
            www_fail += 1
            print("www fail", pid, row.get("post_name"), st, str(data)[:120], flush=True)
        if i % 50 == 0:
            print(f"  www {i}/{len(www_rows)} ok={www_ok} skip={www_skip} fail={www_fail}", flush=True)
        time.sleep(0.05)
    print(f"www ok={www_ok} skip={www_skip} fail={www_fail}", flush=True)

    rows = remaining_rows()
    print("hreflang /en/ remaining", len(rows), flush=True)

    changed = fail = scanned = skipped = 0
    failed_rows = []
    for row in rows:
        scanned += 1
        result = rewrite_one(row)
        if result == "ok":
            changed += 1
        elif result == "skip":
            skipped += 1
        else:
            fail += 1
            failed_rows.append(row)
        if scanned % 10 == 0:
            print(
                f"  hreflang {scanned}/{len(rows)} changed={changed} skip={skipped} fail={fail}",
                flush=True,
            )
        time.sleep(0.12)
    if failed_rows:
        print("retry fails", len(failed_rows), flush=True)
        time.sleep(8)
        still = []
        for row in failed_rows:
            result = rewrite_one(row)
            if result == "ok":
                changed += 1
                fail -= 1
            else:
                still.append(row)
            time.sleep(0.4)
        failed_rows = still
    print(
        f"hreflang scanned={scanned} changed={changed} skip={skipped} fail={fail}",
        flush=True,
    )
    leftover = remaining_rows()
    print("still missing /en/ on -en urls", len(leftover), flush=True)
    if leftover:
        print("leftover sample", leftover[:8], flush=True)

    related = db_rows(
        "SELECT ID, post_name, post_type FROM ZeBDvesG5_posts "
        "WHERE post_status='publish' AND post_type IN ('post','page') "
        "AND post_content REGEXP 'rukn-eltatawer\\\\.com/eg/[a-z0-9-]+-en/'"
    )
    print("related EN links remaining", len(related), flush=True)
    rel_ok = rel_skip = rel_fail = 0
    failed_related = []
    for i, row in enumerate(related, 1):
        pid = int(row["ID"])
        slug = row.get("post_name") or ""
        kind = row.get("post_type") or "post"
        route = "/wp/v2/posts" if kind == "post" else "/wp/v2/pages"
        st, item = req(f"{route}/{pid}&context=edit&_fields=id,slug,content")
        raw = ""
        if isinstance(item, dict) and isinstance(item.get("content"), dict):
            raw = item["content"].get("raw") or ""
        if not raw:
            rel_fail += 1
            failed_related.append(row)
            print("related empty", pid, slug, st, flush=True)
            continue
        new = rewrite_html(raw, slug)
        if new == raw:
            rel_skip += 1
        else:
            st, data = content_edit(pid, raw, new, False)
            if st == 200:
                rel_ok += 1
            else:
                rel_fail += 1
                failed_related.append(row)
                print("related fail", pid, slug, st, str(data)[:140], flush=True)
        if i % 10 == 0:
            print(
                f"  related {i}/{len(related)} ok={rel_ok} skip={rel_skip} fail={rel_fail}",
                flush=True,
            )
        time.sleep(0.12)
    if failed_related:
        print("retry related", len(failed_related), flush=True)
        time.sleep(8)
        for row in failed_related:
            pid = int(row["ID"])
            slug = row.get("post_name") or ""
            st, item = req(f"/wp/v2/posts/{pid}&context=edit&_fields=id,slug,content")
            raw = ""
            if isinstance(item, dict) and isinstance(item.get("content"), dict):
                raw = item["content"].get("raw") or ""
            if not raw:
                continue
            new = rewrite_html(raw, slug)
            if new != raw:
                content_edit(pid, raw, new, False)
            time.sleep(0.4)
    related_left = db_rows(
        "SELECT ID, post_name FROM ZeBDvesG5_posts "
        "WHERE post_status='publish' AND post_type IN ('post','page') "
        "AND post_content REGEXP 'rukn-eltatawer\\\\.com/eg/[a-z0-9-]+-en/'"
    )
    print(
        f"related ok={rel_ok} skip={rel_skip} fail={rel_fail} leftover={len(related_left)}",
        flush=True,
    )

    cli("wp rewrite flush", True)
    cli("wp cache purge", True)
    cli("wp litespeed-purge all", True)

    after = {pid: snapshot(pid) for pid in sample}
    print("SEO titles after", json.dumps(after, ensure_ascii=False), flush=True)
    for pid, before in sample.items():
        a = after.get(pid) or {}
        if before.get("rank_math_title") != a.get("rank_math_title"):
            print("ERROR title changed", pid, flush=True)
        if before.get("wp_title") != a.get("wp_title"):
            print("ERROR wp title changed", pid, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
