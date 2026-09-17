#!/usr/bin/env python3
"""Technical SEO + content-quality audit for the Egypt WordPress site.

Reads published posts/pages from the live REST API (or local import CSVs),
then flags thin copy, shared templates, near-duplicates, search-intent
mismatches, and missing SEO structure. Stdlib only.

Credentials (REST mode): WP_USER, WP_APP_PASS, optional WP_BASE_URL.
Never print or write the application password.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html as html_lib
import json
import os
import re
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


DEFAULT_BASE = "https://www.rukn-eltatawer.com/eg"
THIN_WORDS = 1000
SIMILAR_THRESHOLD = 0.62
NEAR_DUP_THRESHOLD = 0.82
BOILER_DOC_FRAC = 0.18
UNIQUE_RATIO_WARN = 0.42
SHINGLE_N = 4

CITIES = [
    "التجمع الخامس", "التجمع", "الشيخ زايد", "الزمالك", "المهندسين", "مدينة نصر",
    "المعادي", "مصر الجديدة", "الرحاب", "مدينتي", "العاصمة الإدارية", "العاصمة الادارية",
    "السادس من أكتوبر", "6 أكتوبر", "أكتوبر", "العبور", "الشروق", "بدر",
    "القاهرة", "الجيزة", "الإسكندرية", "الاسكندرية", "المنصورة", "طنطا",
    "المحلة", "الزقازيق", "أسوان", "اسوان", "الأقصر", "الاقصر", "الأقصر",
    "بورسعيد", "الإسماعيلية", "الاسماعيلية", "السويس", "دمياط", "كفر الشيخ",
    "دمنهور", "بنها", "الفيوم", "بني سويف", "المنيا", "أسيوط", "سوهاج",
    "قنا", "أسوان", "الغردقة", "شرم الشيخ", "مرسى مطروح", "مطروح",
    "العين السخنة", "الساحل الشمالي", "شمال سيناء", "جنوب سيناء",
    "الوادي الجديد", "البحر الأحمر", "قناة السويس", "الدقهلية", "الشرقية",
    "المنوفية", "البحيرة", "القليوبية", "الجيزة", "حلوان", "شبرا",
    "فيصل", "الدقي", "المقطم", "الخليفة", "عين شمس", "شبرا الخيمة",
    "Cairo", "Giza", "Alexandria", "Aswan", "Luxor", "Mansoura", "Tanta",
    "Zagazig", "Ismailia", "Port Said", "Suez", "Damietta", "Fayoum",
    "Minya", "Assiut", "Sohag", "Qena", "Hurghada", "Sharm", "New Cairo",
    "Sheikh Zayed", "6th of October", "Fifth Settlement", "Maadi", "Zamalek",
    "Nasr City", "Heliopolis", "Rehab", "Madinaty", "New Administrative Capital",
]

SERVICES = [
    "تشطيب شقق", "تشطيب فلل", "تشطيب فيلا", "تشطيب", "ديكور", "تصميم داخلي",
    "تفصيل مطابخ", "مطابخ", "دريسينج روم", "دريسينج", "جبس بورد", "أرضيات",
    "كشف تسرب", "تسربات", "عزل الأسطح", "عزل أسطح", "عزل", "سباكة",
    "تسليك", "مجاري", "تكييف", "كهرباء", "نظافة", "تنظيف", "تعقيم",
    "مكافحة الحشرات", "مكافحة حشرات", "حشرات", "صيانة", "حرفيين", "نقاشة",
    "نجار", "سباك", "نقاش", "كهربائي", "جبساتي", "ألوميتال",
    "apartment finishing", "villa finishing", "interior design", "kitchens",
    "dressing room", "plumber", "carpenter", "painter", "electrician",
    "gypsum", "plumbing", "leak", "insulation", "cleaning", "pest",
    "electrical", "air conditioning", "maintenance",
]

PLACEHOLDER_PATTERNS = [
    r"lorem ipsum", r"\bplaceholder\b", r"\bTODO\b", r"\bTBD\b",
    r"\[\[", r"\{PHONE", r"\{WHATSAPP", r"نص تجريبي", r"اكتب هنا",
    r"coming soon", r"your text here", r"insert text", r"xxxx",
    r"dummy text", r"sample content",
]

LANG_AR_RE = re.compile(r"[\u0600-\u06FF]")
LANG_EN_RE = re.compile(r"[A-Za-z]")
TAG_RE = re.compile(r"(?is)<script[^>]*>.*?</script>|<style[^>]*>.*?</style>")
TOC_RE = re.compile(r'(?is)<div[^>]*id=["\']ez-toc-container["\'][^>]*>.*?</div>')
HTML_TAG_RE = re.compile(r"(?s)<[^>]+>")
WS_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"[A-Za-z0-9\u0600-\u06FF]+")
H_RE = re.compile(r"(?is)<h([1-6])[^>]*>(.*?)</h\1>")
IMG_RE = re.compile(r"(?is)<img\b[^>]*>")
SRC_RE = re.compile(r'(?is)\bsrc=["\']([^"\']+)["\']')
TEL_RE = re.compile(r"(?i)(?:tel:|wa\.me/)\+?(\d{8,15})")
CITY_RE = re.compile("|".join(re.escape(c) for c in sorted(CITIES, key=len, reverse=True)))
SERVICE_RE = re.compile("|".join(re.escape(s) for s in sorted(SERVICES, key=len, reverse=True)), re.I)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def rendered(value: Any) -> str:
    if isinstance(value, dict):
        return value.get("rendered") or value.get("raw") or ""
    return value or ""


def strip_ez_toc(raw: str) -> str:
    """Drop Easy TOC blocks (nested divs) so they do not inflate word counts."""
    marker = 'id="ez-toc-container"'
    alt = "id='ez-toc-container'"
    text = raw or ""
    lower = text.lower()
    start = lower.find(marker)
    if start < 0:
        start = lower.find(alt)
    if start < 0:
        return text
    open_div = text.rfind("<div", 0, start)
    if open_div < 0:
        return text
    i = open_div
    depth = 0
    while i < len(text):
        nxt_open = text.lower().find("<div", i)
        nxt_close = text.lower().find("</div>", i)
        if nxt_close < 0:
            break
        if 0 <= nxt_open < nxt_close:
            depth += 1
            i = nxt_open + 4
        else:
            depth -= 1
            i = nxt_close + 6
            if depth <= 0:
                return text[:open_div] + " " + text[i:]
    return text


def strip_html(raw: str) -> str:
    text = strip_ez_toc(raw or "")
    text = TAG_RE.sub(" ", text)
    text = TOC_RE.sub(" ", text)
    text = HTML_TAG_RE.sub(" ", text)
    text = html_lib.unescape(text)
    return WS_RE.sub(" ", text).strip()


def inner_text(chunk: str) -> str:
    return WS_RE.sub(" ", strip_html(chunk)).strip()


def words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def word_count(text: str) -> int:
    return len(words(text))


def headings(html: str) -> dict[int, list[str]]:
    found: dict[int, list[str]] = defaultdict(list)
    for level, body in H_RE.findall(html or ""):
        t = inner_text(body)
        if t:
            found[int(level)].append(t)
    return found


def lang_ratio(text: str) -> tuple[int, int]:
    return len(LANG_AR_RE.findall(text)), len(LANG_EN_RE.findall(text))


def dominant_lang(text: str) -> str:
    ar, en = lang_ratio(text)
    if ar == 0 and en == 0:
        return "unknown"
    if ar > en * 1.2:
        return "ar"
    if en > ar * 1.2:
        return "en"
    return "mixed"


def normalize_geo(text: str) -> str:
    t = CITY_RE.sub("CITY", text)
    t = re.sub(r"\b20\d{2}\b", "YEAR", t)
    t = re.sub(r"\d+", "N", t)
    return WS_RE.sub(" ", t).strip().lower()


def extract_city(text: str) -> str:
    m = CITY_RE.search(text or "")
    return m.group(0) if m else ""


def extract_service(text: str) -> str:
    m = SERVICE_RE.search(text or "")
    return m.group(0) if m else ""


def category_from_class_list(class_list: Any) -> str:
    if not isinstance(class_list, list):
        return ""
    cats = [c.replace("category-", "", 1) for c in class_list if str(c).startswith("category-")]
    return ",".join(cats)


def shingles(tokens: list[str], n: int = SHINGLE_N) -> set[str]:
    if len(tokens) < n:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / len(a | b)


def fingerprint(h2: list[str], first_paras: str) -> str:
    skeleton = " | ".join(normalize_geo(h) for h in h2[:12])
    lead = " ".join(words(normalize_geo(first_paras))[:40])
    raw = skeleton + " :: " + lead
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def rest_get(url: str, auth: str, timeout: int = 120) -> tuple[Any, dict[str, str]]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 RuknSeoAudit/1.0",
        },
    )
    last_err: Exception | None = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return payload, {k.lower(): v for k, v in resp.headers.items()}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_err = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"GET failed after retries: {url} ({last_err})")


def fetch_wp_items(base: str, auth: str, post_type: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page = 1
    per_page = 50
    fields = "id,date,slug,link,title,content,excerpt,class_list,status"
    endpoint = "posts" if post_type == "post" else "pages"
    while True:
        qs = urllib.parse.urlencode(
            {
                "per_page": per_page,
                "page": page,
                "status": "publish",
                "_fields": fields,
                "context": "view",
            }
        )
        url = f"{base.rstrip('/')}/wp-json/wp/v2/{endpoint}?{qs}"
        log(f"fetch {post_type} page {page}")
        payload, headers = rest_get(url, auth)
        if not isinstance(payload, list) or not payload:
            break
        for row in payload:
            row["_post_type"] = post_type
        items.extend(payload)
        total_pages = int(headers.get("x-wp-totalpages") or "1")
        if page >= total_pages:
            break
        page += 1
    return items


def load_csv_items(paths: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in paths:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for i, row in enumerate(reader, start=1):
                slug = row.get("post_name") or f"csv-{os.path.basename(path)}-{i}"
                items.append(
                    {
                        "id": f"csv:{os.path.basename(path)}:{i}",
                        "date": "",
                        "slug": slug,
                        "link": slug,
                        "title": {"rendered": row.get("post_title") or ""},
                        "content": {"rendered": row.get("post_content") or ""},
                        "excerpt": {"rendered": row.get("rank_math_description") or ""},
                        "class_list": [
                            f"category-{(row.get('categories') or '').strip()}".replace(" ", "-")
                        ],
                        "status": row.get("post_status") or "",
                        "_post_type": row.get("post_type") or "post",
                        "_csv_city": row.get("emirate") or "",
                    }
                )
    return items


@dataclass
class Record:
    id: str
    post_type: str
    title: str
    slug: str
    url: str
    category: str
    word_count: int
    h1: list[str]
    h2: list[str]
    h3: list[str]
    unique_ratio: float
    lang_title: str
    lang_body: str
    city: str
    service: str
    fingerprint: str
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    similar_to: str = ""
    similar_score: float = 0.0
    cluster_size: int = 1
    phones: str = ""
    img_count: int = 0
    missing_cta: bool = False


def analyze_item(item: dict[str, Any], boiler_sentences: set[str] | None = None) -> Record:
    html = rendered(item.get("content"))
    title = inner_text(rendered(item.get("title")))
    body = strip_html(html)
    heads = headings(html)
    h1, h2, h3 = heads.get(1, []), heads.get(2, []), heads.get(3, [])
    tokens = words(body)
    wc = len(tokens)
    sentences = [s.strip() for s in re.split(r"[.!?؟]+", body) if len(s.strip()) > 40]
    unique_ratio = 1.0
    if boiler_sentences and sentences:
        unique = [s for s in sentences if normalize_geo(s) not in boiler_sentences]
        unique_ratio = len(unique) / max(len(sentences), 1)

    imgs = IMG_RE.findall(html)
    srcs = [m for tag in imgs for m in SRC_RE.findall(tag)]
    phones = sorted(set(TEL_RE.findall(html)))
    city = item.get("_csv_city") or extract_city(title) or extract_city(body[:800])
    service = extract_service(title) or extract_service(" ".join(h2[:4]))
    fp = fingerprint(h2, body[:600])
    rec = Record(
        id=str(item.get("id")),
        post_type=str(item.get("_post_type") or "post"),
        title=title,
        slug=str(item.get("slug") or ""),
        url=str(item.get("link") or ""),
        category=category_from_class_list(item.get("class_list")),
        word_count=wc,
        h1=h1,
        h2=h2,
        h3=h3,
        unique_ratio=unique_ratio,
        lang_title=dominant_lang(title),
        lang_body=dominant_lang(body[:2000]),
        city=city,
        service=service,
        fingerprint=fp,
        phones=",".join(phones),
        img_count=len(imgs),
        missing_cta=not bool(phones),
    )

    # 1 thin
    if wc < THIN_WORDS:
        rec.problems.append("thin_content")
        rec.notes.append(f"عدد الكلمات {wc} أقل من {THIN_WORDS}")

    # 5 placeholders / incomplete
    blob = f"{title}\n{html}\n{body}".lower()
    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, blob, re.I):
            rec.problems.append("placeholder")
            rec.notes.append(f"نص نائب مطابق: {pat}")
            break
    if re.search(r"src=\"[^\"/]+\.webp\"", html):
        rec.problems.append("missing_media")
        rec.notes.append("صور نسبية .webp داخل المحتوى لم تُرفع غالباً")
    if rec.img_count == 0:
        rec.problems.append("missing_image")
        rec.notes.append("لا توجد وسمة <img> داخل المحتوى المنشور")
    if wc < 80 and rec.post_type == "post":
        rec.problems.append("stub_page")
        rec.notes.append("صفحة شبه فارغة (أقل من 80 كلمة) — غالباً تصنيف خدمة بلا دليل")

    # headings
    if not h1:
        rec.problems.append("missing_h1")
        rec.notes.append("لا يوجد H1 داخل المحتوى (قد يعتمد المقال على عنوان القالب فقط)")
    elif len(h1) > 1:
        rec.problems.append("duplicate_h1")
        rec.notes.append(f"عدد H1 داخل المحتوى = {len(h1)}")
    if h1 and title:
        n_h1 = normalize_geo(h1[0])
        n_title = normalize_geo(title)
        if n_h1 != n_title and title not in h1[0] and h1[0] not in title:
            rec.problems.append("h1_title_mismatch")
            rec.notes.append(f"H1 مختلف عن العنوان: «{h1[0][:80]}»")
    if len(h2) < 2:
        rec.problems.append("missing_h2")
        rec.notes.append(f"عدد H2 = {len(h2)}")
    if not h3 and wc >= 400:
        rec.problems.append("missing_h3")
        rec.notes.append("لا توجد عناوين H3 رغم طول نسبي للمحتوى")

    if rec.missing_cta and rec.post_type == "post":
        rec.problems.append("missing_cta")
        rec.notes.append("لا يوجد رابط tel: أو wa.me في المحتوى")

    faq_hit = any(re.search(r"أسئلة|سؤال|FAQ|faq", h) for h in h2 + h3)
    if rec.post_type == "post" and not faq_hit:
        rec.problems.append("missing_faq")
        rec.notes.append("لا يظهر قسم أسئلة شائعة في العناوين")

    # 4 intent / relevance
    if rec.lang_title != "unknown" and rec.lang_body != "unknown" and rec.lang_title != rec.lang_body:
        if rec.lang_title != "mixed" and rec.lang_body != "mixed":
            rec.problems.append("intent_language_mismatch")
            rec.notes.append(f"لغة العنوان {rec.lang_title} مقابل لغة النص {rec.lang_body}")

    title_tokens = set(words(normalize_geo(title)))
    lead_tokens = set(words(normalize_geo(body[:1200])))
    if title_tokens and lead_tokens:
        overlap = len(title_tokens & lead_tokens) / len(title_tokens)
        if overlap < 0.35 and rec.post_type == "post":
            rec.problems.append("intent_title_body")
            rec.notes.append(f"تطابق ضعيف بين العنوان ومقدمة النص ({overlap:.0%})")

    cat = rec.category.lower()
    title_l = title.lower()
    if "cleaning" in cat and not re.search(r"تنظيف|نظاف|clean|pest|حشر", title_l):
        rec.problems.append("intent_category_mismatch")
        rec.notes.append(f"التصنيف {rec.category} لا يطابق العنوان")
    if re.search(r"finishing-decor", cat) and re.search(r"تسرب|عزل|سباك|حشر|تنظيف|كهرباء|تكييف", title):
        rec.problems.append("intent_category_mismatch")
        rec.notes.append("عنوان صيانة/عزل تحت تصنيف تشطيبات وديكور")

    generic_geo = {"مصر", "القاهرة", "الجيزة", "Egypt", "Cairo", "Giza"}
    heading_cities = [extract_city(h) for h in h2]
    heading_cities = [c for c in heading_cities if c and c != city and c not in title and c not in generic_geo]
    if city and heading_cities:
        rec.problems.append("intent_geo_mismatch")
        rec.notes.append(f"العنوان عن «{city}» بينما H2 يذكر «{heading_cities[0]}»")

    if service and rec.post_type == "post":
        if normalize_geo(service) not in normalize_geo(body[:1500]):
            rec.problems.append("intent_service_missing")
            rec.notes.append(f"الخدمة «{service}» في العنوان ضعيفة الحضور في المقدمة")

    if rec.slug.endswith("-en") and rec.lang_body == "ar":
        rec.problems.append("intent_language_mismatch")
        rec.notes.append("slug إنجليزي بينما النص عربي")
    if (not rec.slug.endswith("-en")) and rec.lang_body == "en" and rec.post_type == "post":
        rec.problems.append("intent_language_mismatch")
        rec.notes.append("مقال عربي المسار بنص إنجليزي")

    rec.problems = sorted(set(rec.problems))
    return rec


def collect_boilerplate(bodies: list[str]) -> set[str]:
    """Boilerplate is computed inside language buckets so EN+AR mix does not hide clones."""
    buckets: dict[str, list[str]] = defaultdict(list)
    for body in bodies:
        buckets[dominant_lang(body[:2000])].append(body)
    boiler: set[str] = set()
    for group in buckets.values():
        n = max(len(group), 1)
        df: Counter[str] = Counter()
        for body in group:
            sents = {
                normalize_geo(s.strip())
                for s in re.split(r"[.!?؟]+", body)
                if len(s.strip()) > 40
            }
            df.update(sents)
        boiler.update({s for s, c in df.items() if c / n >= BOILER_DOC_FRAC and c >= 6})
    return boiler


def attach_full_similarity(records: list[Record], bodies: dict[str, str]) -> list[tuple[Record, Record, float]]:
    packed = [(rec, shingles(words(normalize_geo(bodies[rec.id])))) for rec in records]
    pairs: list[tuple[Record, Record, float]] = []
    for i, (a, sa) in enumerate(packed):
        best = 0.0
        best_b: Record | None = None
        for b, sb in packed[i + 1 :]:
            score = jaccard(sa, sb)
            if score >= SIMILAR_THRESHOLD:
                pairs.append((a, b, score))
            if score > best:
                best = score
                best_b = b
        if best_b is not None:
            a.similar_to = best_b.url
            a.similar_score = round(best, 3)
            if best > best_b.similar_score:
                best_b.similar_to = a.url
                best_b.similar_score = round(best, 3)
        if i % 60 == 0:
            log(f"similarity {i}/{len(packed)}")
    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs


def write_csv(path: str, records: list[Record]) -> None:
    fields = [
        "id",
        "post_type",
        "url",
        "title",
        "slug",
        "category",
        "word_count",
        "unique_ratio",
        "h1_count",
        "h2_count",
        "h3_count",
        "h1_text",
        "lang_title",
        "lang_body",
        "city",
        "service",
        "cluster_size",
        "fingerprint",
        "similar_score",
        "similar_to",
        "img_count",
        "phones",
        "problems",
        "notes",
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for rec in records:
            w.writerow(
                {
                    "id": rec.id,
                    "post_type": rec.post_type,
                    "url": rec.url,
                    "title": rec.title,
                    "slug": rec.slug,
                    "category": rec.category,
                    "word_count": rec.word_count,
                    "unique_ratio": f"{rec.unique_ratio:.3f}",
                    "h1_count": len(rec.h1),
                    "h2_count": len(rec.h2),
                    "h3_count": len(rec.h3),
                    "h1_text": " || ".join(rec.h1),
                    "lang_title": rec.lang_title,
                    "lang_body": rec.lang_body,
                    "city": rec.city,
                    "service": rec.service,
                    "cluster_size": rec.cluster_size,
                    "fingerprint": rec.fingerprint,
                    "similar_score": rec.similar_score,
                    "similar_to": rec.similar_to,
                    "img_count": rec.img_count,
                    "phones": rec.phones,
                    "problems": "|".join(rec.problems),
                    "notes": " • ".join(rec.notes),
                }
            )


def write_pairs_csv(path: str, pairs: list[tuple[Record, Record, float]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["score", "url_a", "title_a", "url_b", "title_b", "same_service", "same_city"],
        )
        w.writeheader()
        for a, b, score in pairs:
            w.writerow(
                {
                    "score": f"{score:.3f}",
                    "url_a": a.url,
                    "title_a": a.title,
                    "url_b": b.url,
                    "title_b": b.title,
                    "same_service": a.service == b.service and bool(a.service),
                    "same_city": a.city == b.city and bool(a.city),
                }
            )


def md_escape(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def table(rows: list[list[str]]) -> str:
    if not rows:
        return "_لا توجد صفوف._\n"
    width = len(rows[0])
    out = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
    for row in rows[1:]:
        out.append("| " + " | ".join(md_escape(c) for c in row) + " |")
    return "\n".join(out) + "\n"


def write_markdown(
    path: str,
    records: list[Record],
    pairs: list[tuple[Record, Record, float]],
    source: str,
) -> None:
    posts = [r for r in records if r.post_type == "post"]
    pages = [r for r in records if r.post_type == "page"]
    thin = sorted([r for r in records if "thin_content" in r.problems], key=lambda r: r.word_count)
    boiler = sorted(
        [r for r in posts if r.unique_ratio < UNIQUE_RATIO_WARN],
        key=lambda r: r.unique_ratio,
    )
    clusters = defaultdict(list)
    for r in posts:
        clusters[r.fingerprint].append(r)
    big_clusters = sorted(clusters.values(), key=len, reverse=True)
    intent = [r for r in records if any(p.startswith("intent_") for p in r.problems)]
    missing = [r for r in records if any(p.startswith("missing_") or p in {"duplicate_h1", "placeholder", "h1_title_mismatch"} for p in r.problems)]
    near = [(a, b, s) for a, b, s in pairs if s >= NEAR_DUP_THRESHOLD][:80]
    cannibal = [(a, b, s) for a, b, s in pairs if a.service and a.service == b.service and a.city != b.city][:40]

    wc_vals = [r.word_count for r in posts] or [0]
    avg_wc = sum(wc_vals) / len(wc_vals)

    lines: list[str] = []
    lines.append("# تدقيق سيو تقني ومحتوى — ركن التطور مصر")
    lines.append("")
    lines.append(f"**المصدر:** `{source}`  ")
    lines.append(f"**التاريخ:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ")
    lines.append(f"**المنشورات المفحوصة:** {len(posts)} مقالاً + {len(pages)} صفحات  ")
    lines.append(f"**حد المحتوى الضعيف:** أقل من {THIN_WORDS} كلمة")
    lines.append("")
    lines.append("## خلاصة تنفيذية")
    lines.append("")
    lines.append(
        f"متوسط طول المقال **{avg_wc:.0f} كلمة**. "
        f"**{len(thin)}/{len(records)}** عنصراً تحت حد الألف كلمة. "
        f"**{sum(1 for r in posts if r.cluster_size >= 8)}** مقالاً تنتمي لقالب هيكلي مكرر "
        f"(نفس تسلسل العناوين بعد إزالة اسم المدينة). "
        f"**{len(near)}** زوجاً بتشابه ≥ {NEAR_DUP_THRESHOLD:.0%}."
    )
    lines.append("")
    lines.append("| المؤشر | العدد |")
    lines.append("|---|---|")
    lines.append(f"| مقالات/صفحات مفحوصة | {len(records)} |")
    lines.append(f"| محتوى ضعيف (< {THIN_WORDS} كلمة) | {len(thin)} |")
    lines.append(f"| نسبة نص فريد < {UNIQUE_RATIO_WARN:.0%} | {len(boiler)} |")
    lines.append(f"| قوالب هيكلية (≥ 8 مقالات بنفس البصمة) | {sum(1 for c in big_clusters if len(c) >= 8)} |")
    lines.append(f"| أزواج متشابهة (≥ {SIMILAR_THRESHOLD:.0%}) | {len(pairs)} |")
    lines.append(f"| أزواج شبه مطابقة (≥ {NEAR_DUP_THRESHOLD:.0%}) | {len(near)} |")
    lines.append(f"| عدم تطابق نية بحث | {len(intent)} |")
    lines.append(f"| عناصر SEO/هيكل ناقصة أو نائبة | {len(missing)} |")
    lines.append(f"| مقالات بلا H1 داخل المحتوى | {sum(1 for r in records if 'missing_h1' in r.problems)} |")
    lines.append(f"| مقالات بـ H1 مكرر | {sum(1 for r in records if 'duplicate_h1' in r.problems)} |")
    lines.append(f"| مقالات بلا صورة في المحتوى | {sum(1 for r in records if 'missing_image' in r.problems)} |")
    stubs = [r for r in records if "stub_page" in r.problems]
    lines.append(f"| صفحات شبه فارغة (< 80 كلمة) | {len(stubs)} |")
    lines.append("")
    lines.append("الملفات التفصيلية: `reports/seo-content-audit.csv` و`reports/seo-similar-pairs.csv`.")
    lines.append("")

    lines.append("## 1. محتوى ضعيف (Thin Content)")
    lines.append("")
    lines.append(
        f"منها **{len(stubs)}** صفحات شبه فارغة (< 80 كلمة) — غالباً أعمدة خدمات بلا جسم مقال."
    )
    lines.append("")
    buckets = [
        ("أقل من 300", [r for r in thin if r.word_count < 300]),
        ("300–599", [r for r in thin if 300 <= r.word_count < 600]),
        ("600–999", [r for r in thin if 600 <= r.word_count < 1000]),
    ]
    lines.append("| الشريحة | العدد |")
    lines.append("|---|---|")
    for label, rows in buckets:
        lines.append(f"| {label} | {len(rows)} |")
    lines.append("")
    sample: list[Record] = []
    seen: set[str] = set()
    for group in (stubs, [r for r in thin if r.lang_body == "ar"], [r for r in thin if r.lang_body == "en"], thin):
        for r in group:
            if r.id in seen:
                continue
            sample.append(r)
            seen.add(r.id)
            if len(sample) >= 35:
                break
        if len(sample) >= 35:
            break
    rows = [["العنوان", "الرابط", "الكلمات", "التصنيف", "ملاحظات"]]
    for r in sample:
        rows.append([r.title, r.url, str(r.word_count), r.category, r.notes[0] if r.notes else ""])
    lines.append(table(rows))
    if len(thin) > 40:
        lines.append(f"_و{len(thin) - 40} صفاً إضافياً في CSV._")
        lines.append("")

    lines.append("## 2. إفراط القوالب والنصوص الجاهزة")
    lines.append("")
    lines.append(
        "البصمة الهيكلية تُحسب من تسلسل H2 بعد استبدال أسماء المدن والتواريخ. "
        "الجمل التي تتكرر في ≥ 18% من المقالات تُعد قالباً جاهزاً وتخفض نسبة النص الفريد."
    )
    lines.append("")
    rows = [["حجم المجموعة", "الخدمة المسيطرة", "مثال عنوان", "مثال رابط"]]
    for cluster in big_clusters[:15]:
        if len(cluster) < 5:
            continue
        svc = Counter(c.service or "—" for c in cluster).most_common(1)[0][0]
        rows.append([str(len(cluster)), svc, cluster[0].title, cluster[0].url])
    lines.append(table(rows))
    rows = [["العنوان", "الرابط", "نسبة النص الفريد", "حجم القالب", "ملاحظات"]]
    for r in boiler[:25]:
        rows.append(
            [
                r.title,
                r.url,
                f"{r.unique_ratio:.0%}",
                str(r.cluster_size),
                "نفس الهيكل يتكرر عبر مدن/خدمات متعددة",
            ]
        )
    lines.append(table(rows))

    lines.append("## 3. محتوى مكرر/متشابه وcannibalization")
    lines.append("")
    lines.append(
        f"التشابه = Jaccard على شرائح {SHINGLE_N} كلمات بعد تطبيع المدن. "
        f"العتبة {SIMILAR_THRESHOLD:.0%} تعني قالبًا مشتركًا؛ {NEAR_DUP_THRESHOLD:.0%} تعني شبه تطابق."
    )
    lines.append("")
    rows = [["التشابه", "المقال أ", "المقال ب", "نفس الخدمة؟", "نفس المدينة؟"]]
    for a, b, s in (near or pairs)[:30]:
        rows.append(
            [
                f"{s:.0%}",
                f"{a.title}",
                f"{b.title}",
                "نعم" if a.service == b.service and a.service else "لا",
                "نعم" if a.city == b.city and a.city else "لا",
            ]
        )
    lines.append(table(rows))
    if cannibal:
        lines.append("### تعارض كلمات مفتاحية (نفس الخدمة + مدينة مختلفة + تشابه عالٍ)")
        lines.append("")
        rows = [["التشابه", "خدمة", "مدينة أ", "مدينة ب", "رابط أ"]]
        for a, b, s in cannibal[:20]:
            rows.append([f"{s:.0%}", a.service, a.city, b.city, a.url])
        lines.append(table(rows))

    lines.append("## 4. عدم تطابق نية البحث والملاءمة")
    lines.append("")
    rows = [["العنوان", "الرابط", "فئة المشكلة", "ملاحظات"]]
    for r in intent[:40]:
        flags = [p for p in r.problems if p.startswith("intent_")]
        rows.append([r.title, r.url, ", ".join(flags), " • ".join(r.notes[:2])])
    lines.append(table(rows))
    if len(intent) > 40:
        lines.append(f"_و{len(intent) - 40} صفاً في CSV._")
        lines.append("")

    lines.append("## 5. أخطاء وعناصر مفقودة")
    lines.append("")
    err_counts = Counter()
    for r in records:
        for p in r.problems:
            if p.startswith("missing_") or p in {"duplicate_h1", "placeholder", "h1_title_mismatch", "missing_media"}:
                err_counts[p] += 1
    lines.append("| المشكلة | العدد |")
    lines.append("|---|---|")
    labels = {
        "missing_h1": "بدون H1 في المحتوى",
        "duplicate_h1": "H1 مكرر داخل المقال",
        "h1_title_mismatch": "H1 ≠ العنوان",
        "missing_h2": "H2 ناقص",
        "missing_h3": "بدون H3",
        "missing_image": "بدون صورة في المحتوى",
        "missing_media": "صور .webp نسبية غير مرفوعة",
        "missing_cta": "بدون tel/WhatsApp في المحتوى",
        "missing_faq": "بدون قسم أسئلة",
        "placeholder": "نصوص نائبة",
    }
    for key, n in err_counts.most_common():
        lines.append(f"| {labels.get(key, key)} | {n} |")
    lines.append("")
    rows = [["العنوان", "الرابط", "الكلمات", "فئة المشكلة", "ملاحظات"]]
    for r in missing[:40]:
        flags = [
            p
            for p in r.problems
            if p.startswith("missing_") or p in {"duplicate_h1", "placeholder", "h1_title_mismatch", "missing_media"}
        ]
        rows.append([r.title, r.url, str(r.word_count), ", ".join(flags), " • ".join(r.notes[:2])])
    lines.append(table(rows))

    lines.append("## صفحات أساسية")
    lines.append("")
    rows = [["العنوان", "الرابط", "الكلمات", "المشاكل"]]
    for r in pages:
        rows.append([r.title, r.url, str(r.word_count), ", ".join(r.problems) or "—"])
    lines.append(table(rows))

    lines.append("## توصيات أولوية")
    lines.append("")
    lines.append("1. إيقاف نشر قوالب مدينة×خدمة قصيرة؛ دمج المدن المتجاورة أو تحويلها إلى أقسام داخل دليل خدمة أبوي مع canonical واضح.")
    lines.append("2. إعادة كتابة المقدمة وH2 محلياً (خامات، كمبوندات، أسعار استرشادية، أخطاء شائعة) حتى ترتفع نسبة النص الفريد فوق 60%.")
    lines.append("3. إصلاح التصنيفات الإنجليزية التالفة (`cleaning-en-en` وغيرها) وربط كل مقال بخدمة واحدة ونية بحث واحدة.")
    lines.append("4. H1 واحد مطابق للعنوان، صور حقيقية بدل `.webp` النسبية، وقسم FAQ/CTA موحد من الحقول لا من نسخ القالب.")
    lines.append("5. الصفحات الأساسية (تواصل/عن/خصوصية) أطول وأغنى من فقرات قصيرة إذا كانت مستهدفة للبحث.")
    lines.append("")
    path_parent = os.path.dirname(path)
    os.makedirs(path_parent or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit published WordPress content for technical SEO issues.")
    p.add_argument("--source", choices=("rest", "csv"), default="rest")
    p.add_argument("--base-url", default=os.environ.get("WP_BASE_URL", DEFAULT_BASE))
    p.add_argument("--csv", nargs="*", default=[])
    p.add_argument("--out-dir", default="reports")
    p.add_argument("--cache", default="")
    p.add_argument("--thin-words", type=int, default=THIN_WORDS)
    return p.parse_args()


def main() -> int:
    global THIN_WORDS
    args = parse_args()
    THIN_WORDS = args.thin_words
    os.makedirs(args.out_dir, exist_ok=True)

    if args.source == "csv":
        paths = args.csv or [
            os.path.join(os.getcwd(), f)
            for f in os.listdir(os.getcwd())
            if f.startswith("rukn-eltatawer-egypt-") and f.endswith(".csv")
        ]
        log(f"loading {len(paths)} CSV files")
        items = load_csv_items(paths)
        source = "local CSV imports"
    else:
        user = os.environ.get("WP_USER") or ""
        password = (os.environ.get("WP_APP_PASS") or "").replace(" ", "")
        if not user or not password:
            log("Set WP_USER and WP_APP_PASS for REST mode, or pass --source csv")
            return 2
        auth = base64.b64encode(f"{user}:{password}".encode()).decode()
        cache_path = args.cache
        if cache_path and os.path.exists(cache_path):
            log(f"loading cache {cache_path}")
            with open(cache_path, encoding="utf-8") as fh:
                items = json.load(fh)
        else:
            items = fetch_wp_items(args.base_url, auth, "post")
            items += fetch_wp_items(args.base_url, auth, "page")
            if cache_path:
                with open(cache_path, "w", encoding="utf-8") as fh:
                    json.dump(items, fh, ensure_ascii=False)
        source = args.base_url

    log(f"analyzing {len(items)} items")
    bodies = []
    id_bodies: dict[str, str] = {}
    parsed_html: list[tuple[dict[str, Any], str, str]] = []
    for item in items:
        html = rendered(item.get("content"))
        body = strip_html(html)
        bodies.append(body)
        id_bodies[str(item.get("id"))] = body
        parsed_html.append((item, html, body))

    boiler = collect_boilerplate(bodies)
    log(f"boilerplate sentences: {len(boiler)}")

    records = [analyze_item(item, boiler) for item, _, _ in parsed_html]
    fp_groups = defaultdict(list)
    for rec in records:
        fp_groups[rec.fingerprint].append(rec)
    for group in fp_groups.values():
        for rec in group:
            rec.cluster_size = len(group)
            if len(group) >= 8 and "template_overuse" not in rec.problems:
                rec.problems.append("template_overuse")
                rec.notes.append(f"نفس القالب الهيكلي في {len(group)} مقالاً")
            if rec.unique_ratio < UNIQUE_RATIO_WARN:
                rec.problems.append("boilerplate_overuse")
                rec.notes.append(f"نسبة النص الفريد {rec.unique_ratio:.0%} (جمل القالب)")
            rec.problems = sorted(set(rec.problems))

    log("computing pairwise similarity")
    pairs = attach_full_similarity(records, id_bodies)
    for rec in records:
        rec.unique_ratio = max(0.0, 1.0 - rec.similar_score)
        if rec.similar_score >= SIMILAR_THRESHOLD:
            rec.problems.append("boilerplate_overuse")
            rec.notes.append(f"نسبة النص الفريد مقابل أقرب مقال {rec.unique_ratio:.0%}")
    for a, b, score in pairs:
        if score >= SIMILAR_THRESHOLD:
            if "similar_content" not in a.problems:
                a.problems.append("similar_content")
                a.notes.append(f"تشابه {score:.0%} مع {b.title[:60]}")
            if "similar_content" not in b.problems:
                b.problems.append("similar_content")
                b.notes.append(f"تشابه {score:.0%} مع {a.title[:60]}")
        if score >= NEAR_DUP_THRESHOLD:
            a.problems.append("near_duplicate")
            b.problems.append("near_duplicate")
        if a.service and a.service == b.service and a.city and b.city and a.city != b.city:
            a.problems.append("keyword_cannibalization")
            b.problems.append("keyword_cannibalization")
        a.problems = sorted(set(a.problems))
        b.problems = sorted(set(b.problems))

    records.sort(key=lambda r: (0 if r.post_type == "post" else 1, r.word_count, r.title))
    csv_path = os.path.join(args.out_dir, "seo-content-audit.csv")
    pairs_path = os.path.join(args.out_dir, "seo-similar-pairs.csv")
    md_path = os.path.join("docs", "egypt-seo-content-audit.md")
    write_csv(csv_path, records)
    write_pairs_csv(pairs_path, pairs)
    write_markdown(md_path, records, pairs, source)
    log(f"wrote {csv_path}")
    log(f"wrote {pairs_path}")
    log(f"wrote {md_path}")
    flagged = sum(1 for r in records if r.problems)
    log(f"done: {flagged}/{len(records)} items have at least one issue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
