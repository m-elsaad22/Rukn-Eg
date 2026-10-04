#!/usr/bin/env python3
"""Live Egypt fixes. Does NOT change rank_math_title / SEO titles."""

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
FEATURED_ID = 1742  # existing rukn-eltatawer-picture.webp
CTX = ssl.create_default_context()

NOINDEX_JS = (
    'if(location.pathname.indexOf("/en/")!==-1){var m=document.createElement("meta");'
    'm.name="robots";m.content="noindex,follow";document.head.appendChild(m);}'
)

HREFLANG_SNIPPET = r"""
add_action('template_redirect', function () {
    if (function_exists('remove_action')) {
        foreach (array(1, 2, 3, 10) as $pri) {
            remove_action('wp_head', 'pll_rel_hreflang_attributes', $pri);
        }
    }
}, 1);

add_action('wp_head', function () {
    if (is_admin()) {
        return;
    }
    $home = 'https://www.rukn-eltatawer.com/eg';
    $ar = $en = '';
    if (is_front_page() || is_home()) {
        $ar = $home . '/';
        $en = $home . '/en/';
    } elseif (is_singular()) {
        $p = get_queried_object();
        if (!$p || empty($p->post_name)) {
            return;
        }
        $slug = $p->post_name;
        if (substr($slug, -3) === '-en') {
            $base = substr($slug, 0, -3);
            $en = $home . '/en/' . $slug . '/';
            $ar = $home . '/' . $base . '/';
        } else {
            $ar = $home . '/' . $slug . '/';
            $en = $home . '/en/' . $slug . '-en/';
        }
    } else {
        return;
    }
    echo '<link rel="alternate" hreflang="ar" href="' . esc_url($ar) . '" />' . "\n";
    echo '<link rel="alternate" hreflang="en" href="' . esc_url($en) . '" />' . "\n";
    echo '<link rel="alternate" hreflang="x-default" href="' . esc_url($ar) . '" />' . "\n";
}, 20);
""".strip()


def req(route, method="GET", data=None, timeout=90):
    url = f"{BASE}?rest_route={route}"
    body = None
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode(),
        "Accept": "application/json",
        "User-Agent": "rukn-egypt-fix/1.0",
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
            return exc.code, raw.decode("utf-8", "replace")[:800]


def cli(command, confirm_write=False):
    return req("/wpvibe/v1/cli/run", "POST", {"command": command, "confirm_write": confirm_write})


def fix_header_codes():
    st, data = cli("wp option get header___codes")
    current = (data or {}).get("stdout") or ""
    if not current:
        print("WARN empty header___codes", st, data)
        return
    if NOINDEX_JS not in current:
        print("header___codes: noindex snippet not found (already clean?)")
        return
    updated = current.replace(NOINDEX_JS, "")
    st, data = cli(
        "wp option update header___codes " + json.dumps(updated, ensure_ascii=False),
        True,
    )
    print("header___codes update", (data or {}).get("exit_code"), (data or {}).get("stdout", "")[:200])


def add_hreflang_snippet():
    st, data = req(
        "/wpvibe/v1/code-snippet",
        "POST",
        {
            "action": "create",
            "title": "Egypt hreflang www + /en/ (do not edit SEO titles)",
            "code": HREFLANG_SNIPPET,
            "code_type": "php",
            "location": "everywhere",
            "insert_method": "auto",
        },
    )
    print("snippet", st, str(data)[:500])


def rename_double_en_terms():
    for tax in ("cities", "category", "service_categories"):
        st, data = cli(f"wp term list {tax} --number=400 --format=json")
        if not (data or {}).get("stdout"):
            print("no terms", tax, data)
            continue
        rows = json.loads(data["stdout"])
        by_slug = {r["slug"]: r for r in rows}
        for row in rows:
            slug = row["slug"]
            if not slug.endswith("-en-en"):
                continue
            target = slug[:-3]  # drop last -en -> foo-en
            empty = by_slug.get(target)
            if empty and empty["term_id"] != row["term_id"]:
                # free the short slug
                park = target + "-unused"
                cli(
                    f"wp term update {tax} {empty['term_id']} --by=id --slug={park}",
                    True,
                )
            st2, data2 = cli(
                f"wp term update {tax} {row['term_id']} --by=id --slug={target}",
                True,
            )
            print(
                "term",
                tax,
                slug,
                "->",
                target,
                (data2 or {}).get("exit_code"),
            )


def rest_posts():
    st, first_headers_body = None, None
    url_path = "/wp/v2/posts&per_page=100&page=1&_fields=id,slug,content,featured_media,type"
    # use req
    # headers not returned separately easily; call raw
    posts = []
    page = 1
    while True:
        st, data = req(f"/wp/v2/posts&per_page=100&page={page}&_fields=id,slug,featured_media")
        if st != 200 or not isinstance(data, list) or not data:
            break
        posts.extend(data)
        if len(data) < 100:
            break
        page += 1
    return posts


def rest_get_content(post_id):
    st, data = req(f"/wp/v2/posts/{post_id}&context=edit&_fields=id,content,featured_media")
    return data if st == 200 else None


def fix_posts_h1_and_thumbs():
    posts = rest_posts()
    print("posts", len(posts))
    ok = 0
    for i, p in enumerate(posts, 1):
        payload = {}
        if not p.get("featured_media"):
            payload["featured_media"] = FEATURED_ID
        full = rest_get_content(p["id"])
        raw = ""
        if isinstance(full, dict):
            raw = (full.get("content") or {}).get("raw") or (full.get("content") or {}).get("rendered") or ""
        if "<h1>" in raw:
            payload["content"] = raw.replace("<h1>", "<h2>").replace("</h1>", "</h2>")
        if payload:
            # never send title
            st, data = req(f"/wp/v2/posts/{p['id']}", "POST", payload)
            if st in (200, 201):
                ok += 1
            else:
                print("post fail", p["id"], p["slug"], st, str(data)[:160])
        if i % 50 == 0:
            print(f"  posts {i}/{len(posts)} changed={ok}")
        time.sleep(0.03)
    print("post updates", ok)


def fix_pages():
    st, pages = req("/wp/v2/pages&per_page=20&_fields=id,slug,link,title")
    print("pages", pages)
    # html sitemap
    st, posts = req("/wp/v2/posts&per_page=100&page=1&_fields=id,slug,title,link")
    all_posts = list(posts) if isinstance(posts, list) else []
    page = 2
    while True:
        st, batch = req(f"/wp/v2/posts&per_page=100&page={page}&_fields=id,slug,title,link")
        if st != 200 or not isinstance(batch, list) or not batch:
            break
        all_posts.extend(batch)
        page += 1
    items = []
    for p in all_posts:
        slug = p["slug"]
        title = p["title"]["rendered"] if isinstance(p.get("title"), dict) else p.get("title")
        if slug.endswith("-en"):
            href = f"{HOME}/en/{slug}/"
        else:
            href = f"{HOME}/{slug}/"
        items.append(f'<li><a href="{href}">{title}</a></li>')
    html = (
        "<h2>صفحات ركن التطور مصر</h2><ul>"
        + "".join(items)
        + "</ul>"
    )
    # find sitemap page
    sitemap_id = None
    for p in pages if isinstance(pages, list) else []:
        if p.get("slug") == "html-sitemap":
            sitemap_id = p["id"]
    if sitemap_id:
        req(
            f"/wp/v2/pages/{sitemap_id}",
            "POST",
            {"content": html},
        )
        cli(f'wp post meta update {sitemap_id} rank_math_robots "noindex,follow" --force', True)
        print("updated html-sitemap", sitemap_id, "links", len(items))
    # do not change page titles


def try_robots_txt():
    # Rank Math virtual robots if option exists; also flush cache.
    st, data = cli("wp option pluck rank-math-options-general robots")
    print("rm robots key", data)
    robots = (
        "User-Agent: *\n"
        "Allow: /\n"
        "Disallow: /wp-admin/\n"
        "Allow: /wp-admin/admin-ajax.php\n"
        "Sitemap: https://www.rukn-eltatawer.com/eg/sitemap_index.xml\n"
    )
    st, data = cli(
        "wp option patch update rank-math-options-general robots "
        + json.dumps(robots),
        True,
    )
    print("robots patch", st, str(data)[:400])


def main():
    if not PASSWORD:
        raise SystemExit("Set WP_EG_APP_PASSWORD")
    print("1 header noindex")
    fix_header_codes()
    print("2 hreflang snippet")
    add_hreflang_snippet()
    print("3 term slugs")
    rename_double_en_terms()
    print("4 posts H1 + thumbs (no titles)")
    fix_posts_h1_and_thumbs()
    print("5 pages/sitemap")
    fix_pages()
    print("6 robots attempt")
    try_robots_txt()
    cli("wp cache flush", True)
    cli("wp litespeed-purge all", True)
    print("DONE")


if __name__ == "__main__":
    main()
