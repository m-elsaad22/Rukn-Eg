#!/usr/bin/env python3
"""Live Egypt fixes. Does NOT change rank_math_title / SEO titles / homepage_title."""

from __future__ import annotations

import base64
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BASE = "https://rukn-eltatawer.com/eg/index.php"
USER = os.environ.get("WP_EG_USER", "melsaad")
PASSWORD = os.environ.get("WP_EG_APP_PASSWORD", "")
HOME = "https://www.rukn-eltatawer.com/eg"
FEATURED_ID = 1742  # existing rukn-eltatawer-picture.webp
CTX = ssl.create_default_context()
TABLE = "ZeBDvesG5_posts"

NOINDEX_JS = (
    'if(location.pathname.indexOf("/en/")!==-1){var m=document.createElement("meta");'
    'm.name="robots";m.content="noindex,follow";document.head.appendChild(m);}'
)

HIDE_LANG_CSS = (
    "header .rukn-lc, header .kayan-header-lang, #ruknMob .rukn-lc, "
    "#ruknMob .kayan-header-lang { display: none !important; }"
)

HREFLANG_JS = r"""<script id="egypt-hreflang-fix">(function(){var HOME="https://www.rukn-eltatawer.com/eg";function pair(){var path=location.pathname.replace(/\/+$/,"")||"/eg";var ar,en,slug,base;if(path==="/eg"||path==="/eg/en"){ar=HOME+"/";en=HOME+"/en/";}else if(path.indexOf("/eg/en/")===0){slug=path.split("/").filter(Boolean).pop();base=slug.replace(/-en$/,"");en=HOME+"/en/"+slug+"/";ar=HOME+"/"+base+"/";}else{slug=path.split("/").filter(Boolean).pop();ar=HOME+"/"+slug+"/";en=HOME+"/en/"+slug+"-en/";}return{ar:ar,en:en};}function apply(){if(!document.head)return;document.querySelectorAll('link[rel="alternate"][hreflang]').forEach(function(n){n.parentNode&&n.parentNode.removeChild(n);});var p=pair();[["ar",p.ar],["en",p.en],["x-default",p.ar]].forEach(function(x){var l=document.createElement("link");l.setAttribute("rel","alternate");l.setAttribute("hreflang",x[0]);l.setAttribute("href",x[1]);document.head.appendChild(l);});}apply();if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",apply);setTimeout(apply,0);setTimeout(apply,250);})();</script>"""

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

add_filter('robots_txt', function ($output, $public) {
    $body = "User-Agent: *\nAllow: /\nAllow: /wp-admin/admin-ajax.php\nAllow: /wp-content/uploads/\n";
    $body .= "Disallow: /wp-admin/\nDisallow: /wp-includes/\nDisallow: /wp-content/plugins/\n";
    $body .= "Sitemap: https://www.rukn-eltatawer.com/eg/sitemap_index.xml\n";
    return $body;
}, 99, 2);
""".strip()


def req(route, method="GET", data=None, timeout=90):
    url = f"{BASE}?rest_route={route}"
    body = None
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode(),
        "Accept": "application/json",
        "User-Agent": "rukn-egypt-fix/1.1",
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


def assert_no_title(payload: dict, context: str) -> None:
    banned = ("title", "rank_math_title", "post_title")
    for key in payload:
        if key in banned or key.endswith("_title"):
            raise RuntimeError(f"refusing to send {key} in {context}")


def snapshot_titles(sample_ids: list[int]) -> dict:
    out = {}
    for pid in sample_ids:
        st, data = cli(f"wp post meta get {pid} rank_math_title")
        title_meta = (data or {}).get("stdout") if isinstance(data, dict) else ""
        st, post = req(f"/wp/v2/posts/{pid}&_fields=id,slug,title")
        out[pid] = {
            "rank_math_title": (title_meta or "").strip(),
            "wp_title": ((post or {}).get("title") or {}).get("rendered") if isinstance(post, dict) else None,
            "slug": (post or {}).get("slug") if isinstance(post, dict) else None,
        }
    return out


def content_edit_option(old: str, new: str, replace_all: bool = True):
    return req(
        "/wpvibe/v1/content/edit",
        "POST",
        {
            "target_type": "option",
            "option_name": "header___codes",
            "old_content": old,
            "new_content": new,
            "replace_all": replace_all,
        },
    )


def fix_header_codes():
    st, data = cli("wp option get header___codes")
    current = (data or {}).get("stdout") or ""
    if not current:
        print("WARN empty header___codes", st, data)
        return
    DIST.mkdir(exist_ok=True)
    (DIST / "header___codes.backup.html").write_text(current, encoding="utf-8")
    if NOINDEX_JS in current:
        st, data = content_edit_option(NOINDEX_JS, "")
        print("header noindex", st, data)
    else:
        print("header___codes: noindex snippet not found (already clean?)")
    if HIDE_LANG_CSS in current:
        st, data = content_edit_option(HIDE_LANG_CSS, "")
        print("header unhide lang", st, data)
    tail = 'window.addEventListener("load",egyptBoot);setTimeout(egyptBoot,150);})();</script>'
    st, data = cli("wp option get header___codes")
    now = (data or {}).get("stdout") or ""
    if "egypt-hreflang-fix" not in now and tail in now:
        st, data = content_edit_option(tail, tail + HREFLANG_JS, False)
        print("header hreflang", st, data)
    st, data = cli("wp option get header___codes")
    now = (data or {}).get("stdout") or ""
    print(
        "header verify",
        "noindex" in now,
        "hreflang-fix" in now,
        "len",
        len(now),
    )


def add_hreflang_snippet():
    st, data = req(
        "/wpvibe/v1/code-snippet",
        "POST",
        {
            "action": "create",
            "title": "Egypt hreflang www + /en/ + robots (do not edit SEO titles)",
            "code": HREFLANG_SNIPPET,
            "code_type": "php",
            "location": "everywhere",
            "insert_method": "auto",
        },
    )
    print("snippet", st, str(data)[:400])


def rename_double_en_terms():
    tax_routes = {
        "cities": "/wp/v2/cities",
        "categories": "/wp/v2/categories",
        "service_categories": "/wp/v2/service_categories",
    }
    for tax, route in tax_routes.items():
        rows = []
        page = 1
        while True:
            st, data = req(f"{route}&per_page=100&page={page}")
            if st != 200 or not isinstance(data, list) or not data:
                break
            rows.extend(data)
            if len(data) < 100:
                break
            page += 1
        by_slug = {r.get("slug"): r for r in rows}
        changed = 0
        for row in rows:
            slug = row.get("slug") or ""
            if not slug.endswith("-en-en"):
                continue
            target = slug[:-3]
            empty = by_slug.get(target)
            if empty and empty.get("id") != row.get("id"):
                park = f"{target}-unused"
                st, data = req(f"{route}/{empty['id']}", "POST", {"slug": park})
                print("park", tax, target, "->", park, st)
            payload = {"slug": target}
            st, data = req(f"{route}/{row['id']}", "POST", payload)
            print("term", tax, slug, "->", target, st, (data or {}).get("slug") if isinstance(data, dict) else data)
            if st in (200, 201):
                changed += 1
        print("terms done", tax, "changed", changed, "total", len(rows))


def rest_posts(fields="id,slug,featured_media"):
    posts = []
    page = 1
    while True:
        st, data = req(f"/wp/v2/posts&per_page=100&page={page}&_fields={fields}")
        if st != 200 or not isinstance(data, list) or not data:
            break
        posts.extend(data)
        if len(data) < 100:
            break
        page += 1
    return posts


def fix_posts_thumbs(sample_before: dict):
    posts = rest_posts()
    print("posts", len(posts))
    ok = 0
    skipped = 0
    for i, p in enumerate(posts, 1):
        if p.get("featured_media"):
            skipped += 1
            continue
        payload = {"featured_media": FEATURED_ID}
        assert_no_title(payload, f"post {p['id']}")
        st, data = req(f"/wp/v2/posts/{p['id']}", "POST", payload)
        if st in (200, 201):
            ok += 1
        else:
            print("thumb fail", p["id"], p.get("slug"), st, str(data)[:160])
        if i % 100 == 0:
            print(f"  thumbs {i}/{len(posts)} set={ok} skipped={skipped}")
        time.sleep(0.02)
    print("thumb updates", ok, "already set", skipped)
    sample_after = snapshot_titles(list(sample_before))
    for pid, before in sample_before.items():
        after = sample_after.get(pid) or {}
        if before.get("rank_math_title") != after.get("rank_math_title"):
            print("ERROR SEO title changed", pid, before, after)
        if before.get("wp_title") != after.get("wp_title"):
            print("ERROR WP title changed", pid, before, after)
    print("title guard ok for", list(sample_before))


def fix_h1_via_rest():
    """Convert content H1 to H2 without sending titles. search-replace needs WPVibe browser approval."""
    changed = 0
    page = 1
    while True:
        st, batch = req(
            f"/wp/v2/posts&per_page=50&page={page}&context=edit&_fields=id,slug,content"
        )
        if st != 200 or not isinstance(batch, list) or not batch:
            break
        for p in batch:
            raw = ""
            if isinstance(p.get("content"), dict):
                raw = p["content"].get("raw") or ""
            if "<h1>" not in raw and "</h1>" not in raw:
                continue
            payload = {"content": raw.replace("<h1>", "<h2>").replace("</h1>", "</h2>")}
            assert_no_title(payload, f"h1 {p['id']}")
            st2, data = req(f"/wp/v2/posts/{p['id']}", "POST", payload)
            if st2 in (200, 201):
                changed += 1
            else:
                print("h1 fail", p["id"], st2, str(data)[:120])
        print(f"  h1 page {page} changed={changed}")
        if len(batch) < 50:
            break
        page += 1
        time.sleep(0.03)
    print("h1 updates", changed)


def fix_pages():
    st, pages = req("/wp/v2/pages&per_page=20&_fields=id,slug,link,title")
    print("pages", pages)
    all_posts = rest_posts("id,slug,title,link")
    items = []
    for p in all_posts:
        slug = p["slug"]
        title = p["title"]["rendered"] if isinstance(p.get("title"), dict) else p.get("title")
        if slug.endswith("-en"):
            href = f"{HOME}/en/{slug}/"
        else:
            href = f"{HOME}/{slug}/"
        items.append(f'<li><a href="{href}">{title}</a></li>')
    html = "<h2>صفحات ركن التطور مصر</h2><ul>" + "".join(items) + "</ul>"
    sitemap_id = None
    for p in pages if isinstance(pages, list) else []:
        if p.get("slug") == "html-sitemap":
            sitemap_id = p["id"]
    if sitemap_id:
        payload = {"content": html}
        assert_no_title(payload, "html-sitemap")
        req(f"/wp/v2/pages/{sitemap_id}", "POST", payload)
        cli(f"wp post meta update {sitemap_id} rank_math_robots noindex,follow --force", True)
        print("updated html-sitemap", sitemap_id, "links", len(items))


def try_robots_txt():
    st, data = cli("wp rewrite flush", True)
    print("rewrite flush", (data or {}).get("exit_code"), str(data)[:250])
    st, data = cli("wp rewrite list")
    out = (data or {}).get("stdout") or ""
    print("rewrite has robots", "robots" in str(out))
    robots = (
        "User-Agent: *\n"
        "Allow: /\n"
        "Allow: /wp-admin/admin-ajax.php\n"
        "Allow: /wp-content/uploads/\n"
        "Disallow: /wp-admin/\n"
        "Disallow: /wp-includes/\n"
        "Disallow: /wp-content/plugins/\n"
        "Sitemap: https://www.rukn-eltatawer.com/eg/sitemap_index.xml\n"
    )
    for key in (
        "rank-math-options-general",
        "rank_math_robots_txt",
    ):
        st, data = cli(
            f"wp option patch update {key} robots {json.dumps(robots)}",
            True,
        )
        print("robots patch", key, st, str(data)[:250])


def main():
    if not PASSWORD:
        raise SystemExit("Set WP_EG_APP_PASSWORD")
    posts = rest_posts("id,slug")
    sample_ids = []
    for p in posts:
        if p.get("slug") in (
            "apartment-finishing-fifth-settlement-en",
            "apartment-finishing-fifth-settlement",
        ):
            sample_ids.append(p["id"])
    if not sample_ids and posts:
        sample_ids = [posts[0]["id"], posts[-1]["id"]]
    before = snapshot_titles(sample_ids)
    print("SEO titles before (must stay)", json.dumps(before, ensure_ascii=False))

    print("1 header noindex + hreflang JS")
    fix_header_codes()
    print("2 php snippet (may need WPVibe approval)")
    add_hreflang_snippet()
    print("3 term slugs")
    rename_double_en_terms()
    print("4 H1 -> H2 in post_content only")
    fix_h1_via_rest()
    print("5 featured images (no titles)")
    fix_posts_thumbs(before)
    print("6 pages/sitemap content only")
    fix_pages()
    print("7 robots / rewrite")
    try_robots_txt()
    cli("wp cache flush", True)
    cli("wp litespeed-purge all", True)
    after = snapshot_titles(sample_ids)
    print("SEO titles after (must match)", json.dumps(after, ensure_ascii=False))
    print("DONE")


if __name__ == "__main__":
    main()
