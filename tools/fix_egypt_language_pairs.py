#!/usr/bin/env python3
"""Add EN pairs for orphan AR extras/pages and hreflang. Does NOT change SEO titles."""

from __future__ import annotations

import base64
import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request

socket.setdefaulttimeout(50)

BASE = "https://rukn-eltatawer.com/eg/index.php"
USER = os.environ.get("WP_EG_USER", "melsaad")
PASSWORD = os.environ.get("WP_EG_APP_PASSWORD", "")
HOME = "https://www.rukn-eltatawer.com/eg"
PHONE = "+201007707742"
WA = "https://wa.me/201007707742"
FEATURED_ID = 1742
CTX = ssl.create_default_context()

EXTRAS = [
    {
        "ar_id": 3008,
        "en_cat": 713,
        "ar_cat": 238,
        "slug": "water-leak-detection-en",
        "title": "Water leak detection in Egypt",
        "html": f"""<h2>Water leak detection without reckless demolition</h2>
<p>Rukn El Tatawer locates leaks in Egyptian apartments and villas with moisture meters so we cut less plaster. Call or WhatsApp <a href="tel:{PHONE}">{PHONE}</a>.</p>
<h2>Signs you should book an inspection</h2>
<p>A rising water bill, blistered paint, a damp ceiling patch, a soft floor, or water noise inside a wall. On the coast, condensation can mimic a leak; an on-site check separates the two.</p>
<h2>After the report</h2>
<p>We point to plumbing, waterproofing, or a visible reroute. Repair is quoted in Egyptian pounds after the visit, not from a Gulf rate card.</p>
<h2>Book</h2>
<p>Send photos of the stain, the governorate, and the floor on <a href="{WA}">WhatsApp</a>. Desk hours 9:00–21:00 Cairo time.</p>""",
    },
    {
        "ar_id": 3009,
        "en_cat": 713,
        "ar_cat": 238,
        "slug": "roof-waterproofing-en",
        "title": "Roof waterproofing in Egypt",
        "html": f"""<h2>Roof waterproofing and heat insulation in Egypt</h2>
<p>Thermal and waterproof layers for concrete and metal roofs, with a written scope after inspection. <a href="tel:{PHONE}">{PHONE}</a>.</p>
<h2>When a roof needs work</h2>
<p>Ceiling stains after rain, a last-floor unit that overheats in summer, or a bare roof over a Cairo, Delta, or Upper Egypt apartment. Correct insulation cuts AC load and stops paint failure.</p>
<h2>How we work</h2>
<p>Find weak points, clean the slab, treat cracks, then a system that matches the roof type and local climate. Pricing is in EGP from measured area on site.</p>
<h2>Coverage</h2>
<p>Greater Cairo, Lower and Upper Egypt by crew schedule. Send roof photos and the governorate on WhatsApp.</p>""",
    },
    {
        "ar_id": 3010,
        "en_cat": 707,
        "ar_cat": 236,
        "slug": "ac-maintenance-egypt-en",
        "title": "Air-conditioner maintenance in Egypt",
        "html": f"""<h2>Air-conditioner maintenance in Egypt</h2>
<p>Split, concealed, and compound AC units serviced in Egyptian homes and offices. Quotes in EGP. Daily 9:00–21:00 Cairo time on <a href="tel:{PHONE}">{PHONE}</a> or <a href="{WA}">WhatsApp</a>.</p>
<h2>What a visit covers</h2>
<p>Indoor/outdoor wash, gas and leak check, filters and coil, electrical and thermostat, cooling test before summer.</p>
<h2>Why Egypt climate matters</h2>
<p>Coastal humidity, Cairo dust, and Upper Egypt heat kill compressors if the set is left dirty. A service before May/June costs less than a mid-summer replacement.</p>
<h2>Areas</h2>
<p>Cairo, Giza, Alexandria, the Delta, Upper Egypt, and coastal cities by schedule. Send the brand, unit type, and governorate.</p>""",
    },
    {
        "ar_id": 3011,
        "en_cat": 703,
        "ar_cat": 237,
        "slug": "home-cleaning-disinfection-en",
        "title": "Home cleaning and disinfection in Egypt",
        "html": f"""<h2>Home cleaning and disinfection in Egypt</h2>
<p>Deep cleaning for apartments, villas, and offices with household-safe products and EGP contracts. <a href="tel:{PHONE}">{PHONE}</a>.</p>
<h2>Scope</h2>
<p>Kitchens, bathrooms, floors and ceramic, windows and balconies, plus touch-point disinfection after finishing or before move-in. Compound units and compact Cairo flats use the same checklist as Alexandria and the Delta.</p>
<h2>When to book</h2>
<p>After the contractor hands over, after painting, before a new lease, or on a cycle for furnished rentals. Disinfection helps after plumbing or damp repairs.</p>
<h2>Inspection</h2>
<p>Send approximate area, room count, and governorate on <a href="{WA}">WhatsApp</a>. Desk 9:00–21:00 Cairo time.</p>""",
    },
    {
        "ar_id": 3012,
        "en_cat": 719,
        "ar_cat": 239,
        "slug": "pest-control-egypt-en",
        "title": "Pest control for Egyptian homes",
        "html": f"""<h2>Pest control for Egyptian homes</h2>
<p>Cockroaches, ants, bed bugs, and rodents treated according to the unit. <a href="tel:{PHONE}">{PHONE}</a>.</p>
<h2>Method</h2>
<p>Find the source (kitchen, drains, garden, store), then residential-approved products with guidance for children and pets. A follow-up visit if the case needs it.</p>
<h2>After finishing works</h2>
<p>Closed apartments and plumbing jobs often trigger infestations. Pest control prepares a unit for living; it does not replace a damp repair.</p>
<h2>Request</h2>
<p>Describe the insect, governorate, and area on WhatsApp. Hours 9:00–21:00 Cairo time, priced in EGP.</p>""",
    },
    {
        "ar_id": 3013,
        "en_cat": 659,
        "ar_cat": 235,
        "slug": "plumbing-general-maintenance-en",
        "title": "Plumbing and general maintenance in Egypt",
        "html": f"""<h2>Plumbing and general maintenance in Egypt</h2>
<p>Household plumbing, electrical snags, and day-to-day faults in Egyptian apartments and villas. Contracts in EGP. <a href="tel:{PHONE}">{PHONE}</a>.</p>
<h2>Typical jobs</h2>
<p>Taps and tanks, blocked drains, heaters, pumps, visible switches and cables, simple doors and wood after finishing. We split a quick fix from a job that needs parts and a return visit.</p>
<h2>Egyptian building stock</h2>
<p>Old downtown stacks and new compounds in 6th of October, Sheikh Zayed, and Fifth Settlement do not share the same pipework. We do not copy Gulf villa kits; we inspect the actual unit.</p>
<h2>Book</h2>
<p>Governorate, district, and a short fault note on WhatsApp. Daily 9:00–21:00 Cairo time.</p>""",
    },
    {
        "ar_id": 3024,
        "en_cat": 707,
        "ar_cat": 236,
        "slug": "home-care-tips-egypt-en",
        "title": "Home care tips for Egypt",
        "html": f"""<h2>Home care tips for apartments in Egypt</h2>
<p>Small monthly habits extend finishing inside Egyptian flats. For a maintenance visit: <a href="tel:{PHONE}">{PHONE}</a>.</p>
<h2>Monthly</h2>
<p>Clean AC filters, check taps for drips, clear balcony drains before rain, and run the heater briefly even in summer so scale does not sit.</p>
<h2>Seasonal</h2>
<p>Before summer: AC wash and roof check. Before winter: heater, shower mixer, bathroom floors. After dust storms: compound doors and windows.</p>
<h2>When to call a technician</h2>
<p>Repeat faults, damp, or electrical sparking should not wait. Send a short note on WhatsApp and we route plumbing, AC, or waterproofing — in Egypt, in EGP.</p>""",
    },
    {
        "ar_id": 3025,
        "en_cat": 713,
        "ar_cat": 238,
        "slug": "when-to-inspect-leaks-en",
        "title": "When to inspect for water leaks in Egypt",
        "html": f"""<h2>When to inspect for water leaks in Egypt</h2>
<p>Do not wait for ceiling paint to collapse. An early leak check in Egypt saves demolition. Rukn El Tatawer: <a href="tel:{PHONE}">{PHONE}</a>.</p>
<h2>Early signs</h2>
<p>A spreading circular stain, a musty wardrobe, hollow ceramic, a meter that moves with taps closed, or downstairs neighbours reporting seepage.</p>
<h2>Do not delay</h2>
<p>Top-floor units, roofs without recent waterproofing, newly finished flats, and old iron pipe stacks. Alexandria humidity is not the same as drier Cairo; the inspection names the cause.</p>
<h2>Next step</h2>
<p>A photo of the stain plus the governorate on WhatsApp. Inspection in EGP. Desk 9:00–21:00 Cairo time.</p>""",
    },
    {
        "ar_id": 3026,
        "en_cat": 707,
        "ar_cat": 236,
        "slug": "preventive-home-maintenance-en",
        "title": "Why preventive home maintenance matters in Egypt",
        "html": f"""<h2>Why preventive home maintenance matters in Egypt</h2>
<p>A planned visit costs less than a failed AC in July or a heater fault in January. Rukn El Tatawer schedules EGP maintenance via <a href="tel:{PHONE}">{PHONE}</a>.</p>
<h2>What to review</h2>
<p>AC before summer, heater before winter, visible plumbing, breakers, roof waterproofing before rain, and dusty compound doors and windows.</p>
<h2>Real savings</h2>
<p>A burnt compressor or swollen wood from a small leak costs multiples of an inspection. Heat, coastal humidity, and dust make neglect show up faster in Egypt.</p>
<h2>Start</h2>
<p>Send the governorate and unit type. We use a short checklist and fix what we can in one visit. Daily 9:00–21:00 Cairo time.</p>""",
    },
]

PAGES = [
    {
        "ar_id": 1725,
        "kind": "page",
        "slug": "contact-us-en",
        "title": "Contact Rukn El Tatawer Egypt",
        "html": f"""<h2>Contact Rukn El Tatawer in Egypt</h2>
<p>Inspections and quotes in Egyptian pounds for finishing, maintenance, and trades inside Egypt. WhatsApp or call <a href="tel:{PHONE}">{PHONE}</a> — desk 9:00–21:00 Cairo time.</p>
<p>Send the governorate, district, unit type, and the work needed. We do not use Gulf rate cards for Egypt jobs.</p>
<p><a href="{WA}">WhatsApp Egypt desk</a></p>""",
    },
    {
        "ar_id": 1726,
        "kind": "page",
        "slug": "about-egypt-en",
        "title": "About Rukn El Tatawer in Egypt",
        "html": f"""<h2>Rukn El Tatawer in Egypt</h2>
<p>Finishing, décor, trades, and maintenance inside Egyptian governorates. Contracts and materials in EGP for Egyptian climate and compounds — not a copied Gulf branch page.</p>
<p>Work is scoped after an on-site look at the unit. Phone <a href="tel:{PHONE}">{PHONE}</a>.</p>""",
    },
]


def req(route, method="GET", data=None, timeout=70):
    url = f"{BASE}?rest_route={route}"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode(),
        "Accept": "application/json",
        "User-Agent": "rukn-egypt-pairs/1.0",
    }
    body = None
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
                wait = 5 + attempt * 6
                print(f"  HTTP {exc.code} sleep {wait}s {route[:70]}", flush=True)
                time.sleep(wait)
                last = (exc.code, str(exc.code))
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


def assert_no_title_keys(payload, context):
    for key in payload:
        if key in {"rank_math_title"} or str(key).endswith("_title") and key != "title":
            raise RuntimeError(f"refusing {key} in {context}")


def content_edit(kind, pid, old, new, replace_all=False):
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


def hreflang_block(ar_url, en_url):
    ar_url = ar_url.rstrip("/") + "/"
    en_url = en_url.rstrip("/") + "/"
    return (
        f'<p><link rel="alternate" href="{ar_url}" hreflang="ar" />'
        f'<link rel="alternate" href="{en_url}" hreflang="en" />'
        f'<link rel="alternate" href="{ar_url}" hreflang="x-default" /></p>'
    )


def get_raw(route, pid):
    st, item = req(f"{route}/{pid}&context=edit&_fields=id,slug,link,title,content")
    raw = ""
    if isinstance(item, dict) and isinstance(item.get("content"), dict):
        raw = item["content"].get("raw") or ""
    return st, item if isinstance(item, dict) else {}, raw


def snapshot(pid):
    st, data = cli(f"wp post meta get {pid} rank_math_title")
    return ((data or {}).get("stdout") or "").strip() if isinstance(data, dict) else ""


def ensure_hreflang(pid, raw, ar_url, en_url):
    block = hreflang_block(ar_url, en_url)
    if 'hreflang="x-default"' in raw and "/en/" in raw:
        return "skip"
    if "hreflang=" in raw:
        st, data = content_edit("post", pid, raw, raw + block if block not in raw else raw, False)
        if st == 200:
            return "ok"
        print("append fail", pid, st, str(data)[:120], flush=True)
        return "fail"
    st, data = content_edit("post", pid, raw[-80:] if len(raw) > 80 else raw, (raw[-80:] if len(raw) > 80 else raw) + block, False)
    if st == 200:
        return "ok"
    st, data = content_edit("post", pid, raw, raw + block, False)
    print("full append", pid, st, str(data)[:120], flush=True)
    return "ok" if st == 200 else "fail"


def create_en(kind, payload):
    route = "/wp/v2/posts" if kind == "post" else "/wp/v2/pages"
    assert_no_title_keys(payload, kind)
    st, data = req(route, "POST", payload)
    return st, data


def indexnow_ping(urls):
    st, data = cli("wp option get rank-math-options-instant-indexing --format=json")
    raw = (data or {}).get("stdout") if isinstance(data, dict) else ""
    try:
        opts = json.loads(raw or "{}")
    except Exception:
        opts = {}
    key = (opts or {}).get("indexnow_api_key") or ""
    if not key:
        print("indexnow: no key", flush=True)
        return
    locations = [
        f"{HOME}/{key}.txt",
        f"https://www.rukn-eltatawer.com/{key}.txt",
    ]
    key_loc = None
    for loc in locations:
        try:
            with urllib.request.urlopen(loc, context=CTX, timeout=20) as resp:
                body = resp.read().decode("utf-8", "replace").strip()
            if key in body or body == key:
                key_loc = loc
                break
        except Exception:
            continue
    if not key_loc:
        print("indexnow: key file not public, skip ping", flush=True)
        return
    payload = {
        "host": "www.rukn-eltatawer.com",
        "key": key,
        "keyLocation": key_loc,
        "urlList": urls[:80],
    }
    body = json.dumps(payload).encode()
    request = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, context=CTX, timeout=30) as resp:
            print("indexnow", resp.status, resp.read()[:120], flush=True)
    except urllib.error.HTTPError as exc:
        print("indexnow HTTP", exc.code, exc.read()[:200], flush=True)
    except Exception as exc:
        print("indexnow err", exc, flush=True)


def main():
    if not PASSWORD:
        raise SystemExit("Set WP_EG_APP_PASSWORD")
    sample_ids = [256, 677, 3008, 1725]
    before = {pid: snapshot(pid) for pid in sample_ids}
    print("SEO titles before", json.dumps(before, ensure_ascii=False), flush=True)

    created = []
    for row in EXTRAS:
        st, ar, raw = get_raw("/wp/v2/posts", row["ar_id"])
        ar_url = (ar.get("link") or f"{HOME}/").split("?")[0]
        en_url = f"{HOME}/en/{row['slug']}/"
        html = row["html"] + hreflang_block(ar_url, en_url)
        payload = {
            "title": row["title"],
            "slug": row["slug"],
            "status": "publish",
            "featured_media": FEATURED_ID,
            "categories": [row["en_cat"]],
            "content": html,
        }
        st, data = create_en("post", payload)
        if st in (200, 201) and isinstance(data, dict):
            created.append(("post", data.get("id"), data.get("link")))
            print("created post", data.get("id"), data.get("link"), flush=True)
            ensure_hreflang(row["ar_id"], raw, ar_url, (data.get("link") or en_url))
        elif st == 400 and isinstance(data, dict) and "slug" in str(data).lower():
            print("slug exists?", row["slug"], data, flush=True)
        else:
            print("create fail post", row["slug"], st, str(data)[:200], flush=True)
        time.sleep(0.2)

    for row in PAGES:
        route = "/wp/v2/pages"
        st, ar, raw = get_raw(route, row["ar_id"])
        ar_url = (ar.get("link") or f"{HOME}/").split("?")[0]
        en_url = f"{HOME}/en/{row['slug']}/"
        html = row["html"] + hreflang_block(ar_url, en_url)
        payload = {
            "title": row["title"],
            "slug": row["slug"],
            "status": "publish",
            "content": html,
        }
        st, data = create_en("page", payload)
        if st in (200, 201) and isinstance(data, dict):
            created.append(("page", data.get("id"), data.get("link")))
            print("created page", data.get("id"), data.get("link"), flush=True)
            ensure_hreflang(row["ar_id"], raw, ar_url, (data.get("link") or en_url))
        else:
            print("create fail page", row["slug"], st, str(data)[:200], flush=True)
        time.sleep(0.2)

    st, priv_ar, raw_ar = get_raw("/wp/v2/pages", 1727)
    st, priv_en, raw_en = get_raw("/wp/v2/pages", 3)
    ar_url = (priv_ar.get("link") or f"{HOME}/privacy-egypt/").split("?")[0]
    en_url = (priv_en.get("link") or f"{HOME}/en/privacy-policy/").split("?")[0]
    print("privacy hreflang AR", ensure_hreflang(1727, raw_ar, ar_url, en_url), flush=True)
    print("privacy hreflang EN", ensure_hreflang(3, raw_en, ar_url, en_url), flush=True)

    after = {pid: snapshot(pid) for pid in sample_ids}
    print("SEO titles after", json.dumps(after, ensure_ascii=False), flush=True)
    for pid, title in before.items():
        if title != after.get(pid):
            print("ERROR title changed", pid, title, after.get(pid), flush=True)

    ping_urls = [
        f"{HOME}/",
        f"{HOME}/en/",
        f"{HOME}/sitemap_index.xml",
        ar_url,
        en_url,
    ]
    ping_urls.extend(link for _, _, link in created if link)
    indexnow_ping([u for u in ping_urls if u])

    cli("wp litespeed-purge all", True)
    print("created", created, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
