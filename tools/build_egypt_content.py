#!/usr/bin/env python3
"""Rebuild Egypt CSVs into unique, publish-ready Arabic + English posts."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from egypt_data import (
    BRAND_AR,
    BRAND_EN,
    CAT_EN,
    CAT_SLUG,
    PHONE_TEL,
    SERVICE_EN,
    SITE_HOME,
    UPDATED_AR,
    UPDATED_EN,
    WHATSAPP_URL,
    city_info,
    page_url,
    post_url,
    service_key,
)

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
CSV_GLOB = "rukn-eltatawer-egypt-*.csv"

IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
PLACEHOLDER_RE = re.compile(r"\{[A-Z0-9_]+\}")
FIRST_P_RE = re.compile(r"(<p>)(.*?</p>)", re.S)
H1_RE = re.compile(r"<h1\b[^>]*>.*?</h1>", re.I | re.S)
CTA_BLOCK = f"""<div class="rukn-cta" style="display:flex;gap:12px;flex-wrap:wrap;margin:20px 0;">
  <a href="tel:{PHONE_TEL}" style="background:#1976d2;color:#fff;padding:12px 22px;border-radius:10px;font-weight:bold;text-decoration:none;">اتصل الآن {PHONE_TEL}</a>
  <a href="{WHATSAPP_URL}" rel="noopener" style="background:#25D366;color:#fff;padding:12px 22px;border-radius:10px;font-weight:bold;text-decoration:none;">واتساب مباشر — مصر</a>
  <a href="{page_url('contact-us')}" style="background:#0A1F4E;color:#fff;padding:12px 22px;border-radius:10px;font-weight:bold;text-decoration:none;">صفحة التواصل</a>
</div>"""


def read_rows() -> list[dict]:
    rows = []
    for path in sorted(ROOT.glob(CSV_GLOB)):
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for raw in reader:
                row = {k.strip().strip('"'): v for k, v in raw.items()}
                row["_file"] = path.name
                rows.append(row)
    return rows


def strip_broken_media(html: str) -> str:
    html = IMG_RE.sub("", html)
    html = PLACEHOLDER_RE.sub("", html)
    html = re.sub(r'href="tel:"', f'href="tel:{PHONE_TEL}"', html)
    html = re.sub(r'href="#"', f'href="tel:{PHONE_TEL}"', html)
    html = html.replace("https://wa.me/971586634710", WHATSAPP_URL.split("?")[0])
    html = html.replace(f"{SITE_HOME}/?name=", f"{SITE_HOME}/")
    html = re.sub(
        r'href="https://wa\.me/"',
        f'href="{WHATSAPP_URL}"',
        html,
    )
    html = re.sub(
        r'href="https://wa\.me/\{WHATSAPP_RUKN_EGYPT\}"',
        f'href="{WHATSAPP_URL}"',
        html,
    )
    return html


def replace_dates(html: str) -> str:
    return html.replace("أغسطس 2026", UPDATED_AR).replace("August 2026", UPDATED_EN)


def unique_ar_intro(row: dict) -> str:
    city = row["emirate"]
    info = city_info(city)
    svc = service_key(row["post_title"], city)
    return (
        f"<p>ركن التطور يقدّم <strong>{escape(svc)}</strong> في <strong>{escape(city)}</strong> "
        f"داخل محافظة {escape(info['gov_ar'])}، لمنازل وكمبوندات مصرية تُسعَّر وتُنفَّذ بالجنيه المصري "
        f"وليس بأسعار أو لوائح دول الخليج.</p>"
        f"<p>{escape(info['stock_ar'])} {escape(info['climate_ar'])}</p>"
        f"<p>نغطي بشكل معتاد: {escape(info['places_ar'])}. {escape(info['access_ar'])}</p>"
    )


def unique_ar_local(row: dict) -> str:
    city = row["emirate"]
    info = city_info(city)
    svc = service_key(row["post_title"], city)
    return f"""<section>
<h2>ما الذي يختلف في {escape(city)} عن باقي مصر؟</h2>
<p>طلب <strong>{escape(svc)}</strong> هنا يتأثر بثلاثة أمور محلية: نوع العقار، المناخ، وسهولة التوريد. {escape(info['price_note_ar'])}</p>
<ul>
<li>العقار: {escape(info['stock_ar'])}</li>
<li>المناخ: {escape(info['climate_ar'])}</li>
<li>الوصول: {escape(info['access_ar'])}</li>
</ul>
<p>لذلك لا ننسخ مقايسة مدينة أخرى على {escape(city)}؛ المعاينة على الطبيعة هي أساس السعر بالجنيه المصري.</p>
</section>"""


def related_links(row: dict, by_city: dict, by_cat: dict) -> str:
    city = row["emirate"]
    slug = row["post_name"]
    same_city = [r for r in by_city[city] if r["post_name"] != slug][:4]
    same_cat = [
        r
        for r in by_cat[row["categories"]]
        if r["emirate"] != city and r["post_name"] != slug
    ][:3]
    items = []
    for r in same_city + same_cat:
        items.append(
            f'<li><a href="{post_url(r["post_name"])}">{escape(r["post_title"])}</a></li>'
        )
    if not items:
        return ""
    return (
        "<section><h2>خدمات مرتبطة في مصر</h2><ul>"
        + "".join(items)
        + "</ul></section>"
    )


def faq_schema(title: str, extra_q: str, extra_a: str) -> str:
    faqs = [
        (f"هل تعملون في {title}؟", "نعم، الخدمة متاحة داخل مصر بعد تأكيد المنطقة وموعد المعاينة."),
        ("بأي عملة يتم التسعير؟", "كل المقايسات والعقود بالجنيه المصري بعد المعاينة."),
        (extra_q, extra_a),
    ]
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in faqs
        ],
    }
    return (
        '<script type="application/ld+json">'
        + json.dumps(data, ensure_ascii=False)
        + "</script>"
    )


def service_schema(title: str, city: str, desc: str) -> str:
    info = city_info(city)
    data = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": title,
        "serviceType": title,
        "areaServed": {
            "@type": "City",
            "name": city,
            "containedInPlace": {"@type": "AdministrativeArea", "name": info["gov_ar"]},
        },
        "provider": {
            "@type": "LocalBusiness",
            "name": "ركن التطور — مصر",
            "url": SITE_HOME,
            "areaServed": "EG",
            "currenciesAccepted": "EGP",
        },
        "description": desc,
    }
    return (
        '<script type="application/ld+json">'
        + json.dumps(data, ensure_ascii=False)
        + "</script>"
    )


def rebuild_ar(row: dict, by_city: dict, by_cat: dict) -> str:
    html = strip_broken_media(row["post_content"] or "")
    html = replace_dates(html)
    city = row["emirate"]
    info = city_info(city)
    svc = service_key(row["post_title"], city)

    # Replace first two generic paragraphs after the byline when possible
    intro = unique_ar_intro(row)
    # Drop the duplicated Gulf-style compound opener if present (same text reused).
    html = re.sub(
        r"<p>القاهرة الجديدة والتجمع الخامس.*?</p>",
        "",
        html,
        count=3,
        flags=re.S,
    )
    # Insert unique intro after H1 / byline
    if H1_RE.search(html):
        html = H1_RE.sub(lambda m: m.group(0) + intro, html, count=1)
    else:
        html = intro + html

    html += unique_ar_local(row)
    html += related_links(row, by_city, by_cat)
    html += (
        f'<p><link rel="alternate" href="{post_url(row["post_name"])}" hreflang="ar" />'
        f'<link rel="alternate" href="{post_url(row["post_name"] + "-en")}" hreflang="en" /></p>'
    )
    extra_q = f"هل المقايسة تشمل خامات مناسبة لمناخ {city}؟"
    extra_a = f"نعم، نختار الخامات حسب {info['climate_ar']}"
    html += faq_schema(row["post_title"], extra_q, extra_a)
    html += service_schema(row["post_title"], city, row.get("rank_math_description") or svc)
    return html


def build_en(row: dict, by_city: dict) -> dict:
    city = row["emirate"]
    info = city_info(city)
    svc_ar = service_key(row["post_title"], city)
    svc_en = SERVICE_EN.get(svc_ar, svc_ar)
    city_en = info["en"]
    title = f"{svc_en} in {city_en}, Egypt"
    slug = f"{row['post_name']}-en"
    desc = (
        f"{svc_en} in {city_en}, {info['gov_en']}, Egypt. "
        f"EGP quotes after inspection. WhatsApp Rukn El Tatawer Egypt."
    )[:160]
    related = []
    for r in by_city[city]:
        if r["post_name"] == row["post_name"]:
            continue
        sk = service_key(r["post_title"], city)
        related.append(
            f'<li><a href="{post_url(r["post_name"] + "-en")}">'
            f"{escape(SERVICE_EN.get(sk, sk))} in {escape(info['en'])}</a></li>"
        )
        if len(related) >= 4:
            break
    related_html = (
        "<h2>Related Egypt services</h2><ul>" + "".join(related) + "</ul>" if related else ""
    )
    content = f"""<section>
<h1>{escape(title)}</h1>
<p><strong>Written by:</strong> Rukn El Tatawer Egypt technical desk &nbsp;|&nbsp; <strong>Updated:</strong> {UPDATED_EN}</p>
<p>Rukn El Tatawer provides <strong>{escape(svc_en)}</strong> in <strong>{escape(city_en)}</strong>, {escape(info['gov_en'])} Governorate, Egypt. Work is scoped and priced in Egyptian pounds for Egyptian homes — not Gulf villas or AED rate cards.</p>
<p>{escape(info['stock_en'])} {escape(info['climate_en'])}</p>
<p>Typical coverage: {escape(info['places_en'])}. {escape(info['access_en'])}</p>
<div style="display:flex;gap:12px;flex-wrap:wrap;margin:20px 0;">
  <a href="tel:{PHONE_TEL}" style="background:#1976d2;color:#fff;padding:12px 22px;border-radius:10px;font-weight:bold;text-decoration:none;">Call {PHONE_TEL}</a>
  <a href="{WHATSAPP_URL}" rel="noopener" style="background:#25D366;color:#fff;padding:12px 22px;border-radius:10px;font-weight:bold;text-decoration:none;">WhatsApp Egypt desk</a>
</div>
</section>
<section>
<h2>What we handle</h2>
<p>On-site inspection, a written EGP estimate, materials suited to {escape(city_en)}, and handover with a snag list. We coordinate compound permits and delivery windows where the developer requires them.</p>
</section>
<section>
<h2>Local conditions in {escape(city_en)}</h2>
<ul>
<li>{escape(info['stock_en'])}</li>
<li>{escape(info['climate_en'])}</li>
<li>{escape(info['access_en'])}</li>
</ul>
<p>{escape(info['price_note_en'])}</p>
</section>
<section>
<h2>FAQ</h2>
<h3>Do you work in {escape(city_en)}, Egypt?</h3>
<p>Yes. Confirm the compound or street and we schedule an inspection.</p>
<h3>Is pricing in EGP?</h3>
<p>Yes. All estimates and contracts for Egypt jobs are in Egyptian pounds.</p>
<h3>How do I book?</h3>
<p>Message the Egypt WhatsApp desk with the area, unit type, and the work needed.</p>
</section>
{related_html}
<section>
<h2>Arabic version</h2>
<p><a href="{post_url(row['post_name'])}">{escape(row['post_title'])}</a></p>
<p><link rel="alternate" href="{post_url(row['post_name'])}" hreflang="ar" /><link rel="alternate" href="{post_url(row['post_name'] + '-en')}" hreflang="en" /></p>
</section>
"""
    content += faq_schema(title, f"Do you serve {city_en}?", f"Yes, {svc_en} is available in {city_en}, Egypt.")
    return {
        "post_type": "post",
        "post_status": "publish",
        "categories": CAT_EN.get(row["categories"], row["categories"]),
        "category_slug": CAT_SLUG.get(row["categories"], "egypt-services"),
        "country": "Egypt",
        "city": city_en,
        "city_ar": city,
        "post_title": title,
        "post_name": slug,
        "rank_math_title": f"{title} 2026 | {BRAND_EN}",
        "rank_math_description": desc,
        "rank_math_focus_keyword": f"{svc_en}, {city_en}, Egypt",
        "tags": f"{svc_en}, {city_en}, Egypt, {BRAND_EN}",
        "post_content": content,
        "lang": "en",
        "translation_of": row["post_name"],
    }


def seo_ar(row: dict) -> tuple[str, str, str]:
    city = row["emirate"]
    svc = service_key(row["post_title"], city)
    title = f"{row['post_title']} {UPDATED_AR.split()[0]} 2026 | {BRAND_AR} مصر"
    if len(title) > 65:
        title = f"{row['post_title']} | {BRAND_AR} مصر"
    desc = (
        f"{svc} في {city}، مصر — معاينة ومقايسة بالجنيه المصري. "
        f"فريق ركن التطور للتنفيذ من المعاينة حتى التسليم. تواصل واتساب."
    )[:160]
    focus = f"{svc}, {city}, مصر"
    return title, desc, focus


def main() -> None:
    rows = read_rows()
    by_city = defaultdict(list)
    by_cat = defaultdict(list)
    for r in rows:
        by_city[r["emirate"]].append(r)
        by_cat[r["categories"]].append(r)

    ar_out = []
    en_out = []
    for r in rows:
        title, desc, focus = seo_ar(r)
        content = rebuild_ar(r, by_city, by_cat)
        ar_out.append(
            {
                "post_type": "post",
                "post_status": "publish",
                "categories": r["categories"],
                "category_slug": CAT_SLUG.get(r["categories"], "egypt-services"),
                "country": "مصر",
                "city": r["emirate"],
                "post_title": r["post_title"],
                "post_name": r["post_name"],
                "rank_math_title": title,
                "rank_math_description": desc,
                "rank_math_focus_keyword": focus,
                "tags": f"{r.get('tags','')}, مصر, جنيه مصري",
                "post_content": content,
                "lang": "ar",
            }
        )
        en_out.append(build_en(r, by_city))

    DIST.mkdir(exist_ok=True)
    payload = {"arabic": ar_out, "english": en_out}
    (DIST / "egypt-posts.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    fields = [
        "post_type",
        "post_status",
        "categories",
        "country",
        "city",
        "post_title",
        "post_name",
        "rank_math_title",
        "rank_math_description",
        "rank_math_focus_keyword",
        "tags",
        "post_content",
        "lang",
    ]
    for name, data in (("rukn-egypt-ar-publish.csv", ar_out), ("rukn-egypt-en-publish.csv", en_out)):
        with (DIST / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(data)

    print(f"AR {len(ar_out)} EN {len(en_out)} -> {DIST}")


if __name__ == "__main__":
    main()
