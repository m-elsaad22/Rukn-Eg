#!/usr/bin/env python3
"""Fix GSC indexing issues on Egypt WP. Does NOT change SEO titles."""

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
CTX = ssl.create_default_context()
INDEX = ["index", "follow"]
NOINDEX = ["noindex", "follow"]


def req(route, method="GET", data=None, timeout=90):
    url = f"{BASE}?rest_route={route}"
    body = None
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode(),
        "Accept": "application/json",
        "User-Agent": "rukn-egypt-index/1.0",
    }
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    last = None
    for attempt in range(5):
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
                return exc.code, raw.decode("utf-8", "replace")[:400]
        except Exception as exc:
            time.sleep(2 + attempt)
            last = (0, str(exc))
    return last or (0, "retries exhausted")


def cli(command, confirm_write=False):
    return req("/wpvibe/v1/cli/run", "POST", {"command": command, "confirm_write": confirm_write})


def sql(query, limit=1000):
    st, data = cli(f"wp db query {json.dumps(query)} --limit={limit}")
    out = (data or {}).get("stdout") if isinstance(data, dict) else ""
    try:
        parsed = json.loads(out) if out else {}
    except Exception:
        parsed = {}
    return parsed.get("results") or []


def rm_bulk(ids):
    """updateMetaBulk reports success but does not persist robots. Use per-post updateMeta."""
    ok = fail = 0
    for i, pid in enumerate(ids, 1):
        st, data = rm_meta("post", pid, {"rank_math_robots": INDEX})
        if st == 200:
            ok += 1
        else:
            fail += 1
            print("post fail", pid, st, str(data)[:120], flush=True)
        if i % 50 == 0:
            print(f"  posts {i}/{len(ids)} ok={ok} fail={fail}", flush=True)
        time.sleep(0.04)
    return 200, {"ok": ok, "fail": fail}


def rm_meta(object_type, object_id, meta):
    return req(
        "/rankmath/v1/updateMeta",
        "POST",
        {"objectType": object_type, "objectID": int(object_id), "meta": meta},
    )


def snapshot_title(pid):
    st, data = cli(f"wp post meta get {pid} rank_math_title")
    st2, post = req(f"/wp/v2/posts/{pid}&_fields=id,slug,title")
    return {
        "rank_math_title": ((data or {}).get("stdout") or "").strip(),
        "wp_title": ((post or {}).get("title") or {}).get("rendered") if isinstance(post, dict) else None,
        "slug": (post or {}).get("slug") if isinstance(post, dict) else None,
    }


def main():
    if not PASSWORD:
        raise SystemExit("Set WP_EG_APP_PASSWORD")

    sample_ids = []
    rows = sql(
        "SELECT ID, post_name FROM ZeBDvesG5_posts "
        "WHERE post_type='post' AND post_status='publish' AND post_name LIKE '%-en'"
    )
    en_ids = [r["ID"] for r in rows]
    for r in rows:
        if r.get("post_name") == "apartment-finishing-fifth-settlement-en":
            sample_ids.append(r["ID"])
    ar_rows = sql(
        "SELECT ID FROM ZeBDvesG5_posts WHERE post_name='apartment-finishing-fifth-settlement' LIMIT 1"
    )
    sample_ids.extend(r["ID"] for r in ar_rows)
    sample_ids = [int(x) for x in sample_ids]
    before = {pid: snapshot_title(pid) for pid in sample_ids}
    print("SEO titles before", json.dumps(before, ensure_ascii=False), flush=True)
    print("EN posts", len(en_ids), flush=True)

    ok = 0
    for i in range(0, len(en_ids), 80):
        chunk = en_ids[i : i + 80]
        st, data = rm_bulk(chunk)
        print(f"bulk posts {i+1}-{i+len(chunk)}", st, data, flush=True)
        if st == 200:
            ok += len(chunk)
        time.sleep(0.4)
    print("indexed posts", ok, flush=True)

    terms = sql(
        "SELECT t.term_id, t.slug, tt.taxonomy, tt.count "
        "FROM ZeBDvesG5_terms t JOIN ZeBDvesG5_term_taxonomy tt ON tt.term_id=t.term_id "
        "WHERE tt.taxonomy IN ('cities','category') "
        "AND t.slug LIKE '%-en' AND t.slug NOT LIKE '%-unused'"
    )
    skip_slugs = {"egypt-en", "%d8%ba%d9%8a%d8%b1-%d9%85%d8%b5%d9%86%d9%81-en", "uncategorized-en"}
    indexed_terms = 0
    for t in terms:
        slug = t.get("slug") or ""
        count = int(t.get("count") or 0)
        if slug in skip_slugs or count <= 0:
            continue
        st, data = rm_meta("term", t["term_id"], {"rank_math_robots": INDEX})
        if st == 200:
            indexed_terms += 1
        else:
            print("term fail", t, st, str(data)[:160], flush=True)
        time.sleep(0.05)
    print("indexed terms", indexed_terms, "of", len(terms), flush=True)

    unused = sql(
        "SELECT t.term_id, t.slug, tt.taxonomy FROM ZeBDvesG5_terms t "
        "JOIN ZeBDvesG5_term_taxonomy tt ON tt.term_id=t.term_id "
        "WHERE t.slug LIKE '%-unused'"
    )
    canon_ok = 0
    for t in unused:
        slug = (t.get("slug") or "").replace("-unused", "")
        tax = t.get("taxonomy")
        if tax == "cities":
            target = f"{HOME}/en/city/{slug}/"
        elif tax == "category":
            target = f"{HOME}/en/category/{slug}/"
        else:
            continue
        st, data = rm_meta(
            "term",
            t["term_id"],
            {"rank_math_robots": NOINDEX, "rank_math_canonical_url": target},
        )
        if st == 200:
            canon_ok += 1
        time.sleep(0.04)
    print("unused canonicals", canon_ok, flush=True)

    # keep html sitemap noindex
    req(
        "/rankmath/v1/updateMeta",
        "POST",
        {"objectType": "post", "objectID": 1728, "meta": {"rank_math_robots": NOINDEX}},
    )

    robots = (
        "User-Agent: *\n"
        "Allow: /\n"
        "Allow: /wp-admin/admin-ajax.php\n"
        "Allow: /wp-content/uploads/\n"
        "Disallow: /wp-admin/\n"
        "Disallow: /wp-includes/\n"
        "Disallow: /wp-content/plugins/\n"
        "Disallow: /wp-login.php\n"
        "Sitemap: https://www.rukn-eltatawer.com/eg/sitemap_index.xml\n"
    )
    for key in ("robots_txt", "rank_math_robots_txt", "robots.txt"):
        st, data = cli(f"wp option update {key} {json.dumps(robots)}", True)
        print("robots option", key, (data or {}).get("exit_code") if isinstance(data, dict) else st, flush=True)

    cli(
        'wp option patch insert rewrite_rules "robots\\.txt$" "index.php?robots=1"',
        True,
    )
    cli(
        'wp option patch insert rewrite_rules "en/robots\\.txt$" "index.php?robots=1"',
        True,
    )

    for action in (
        "clear_internal_sitemap_cache",
        "sitemap_cache",
        "clear_transients",
        "clear_seo_analysis",
    ):
        st, data = req("/rankmath/v1/toolsAction", "POST", {"action": action})
        print("tools", action, st, str(data)[:160], flush=True)

    cli("wp cache purge", True)
    cli("wp litespeed-purge all", True)

    after = {pid: snapshot_title(pid) for pid in sample_ids}
    print("SEO titles after", json.dumps(after, ensure_ascii=False), flush=True)
    for pid, b in before.items():
        a = after.get(pid) or {}
        if b.get("rank_math_title") != a.get("rank_math_title"):
            print("ERROR title meta changed", pid, flush=True)
        if b.get("wp_title") != a.get("wp_title"):
            print("WARN wp_title differs", pid, b.get("wp_title"), a.get("wp_title"), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
