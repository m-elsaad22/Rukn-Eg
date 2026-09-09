#!/usr/bin/env python3
"""Live SEO hardening for https://rukn-eltatawer.com/eg after pretty permalinks."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from egypt_data import (  # noqa: E402
    CAT_SLUG,
    PHONE_TEL,
    WHATSAPP_INTL,
)
from publish_egypt import (  # noqa: E402
    DIST,
    cli,
    configure_site,
    create_pages,
    load_state,
    req,
    save_state,
    upsert_post,
)

AR_CATS = {
    "خدمات التشطيبات والديكور": ("finishing-decor", "خدمات التشطيبات والديكور"),
    "خدمات التشطيبات والديكور الساحلية": ("coastal-finishing", "خدمات التشطيبات والديكور الساحلية"),
    "خدمات الحرفيين والفنيين": ("craftsmen", "خدمات الحرفيين والفنيين"),
    "خدمات الصيانة": ("maintenance", "خدمات الصيانة"),
    "خدمات التنظيف": ("cleaning", "خدمات التنظيف"),
    "خدمات كشف التسربات والعزل": ("leaks-insulation", "خدمات كشف التسربات والعزل"),
    "خدمات مكافحة الحشرات والتعقيم": ("pest-control", "خدمات مكافحة الحشرات والتعقيم"),
}
EN_CATS = {
    "Finishing and décor": ("finishing-decor-en", "Finishing and décor"),
    "Coastal finishing and décor": ("coastal-finishing-en", "Coastal finishing and décor"),
    "Trades and technicians": ("craftsmen-en", "Trades and technicians"),
    "Maintenance": ("maintenance-en", "Maintenance"),
    "Cleaning": ("cleaning-en", "Cleaning"),
    "Leak detection and insulation": ("leaks-insulation-en", "Leak detection and insulation"),
    "Pest control and sanitizing": ("pest-control-en", "Pest control and sanitizing"),
}


def sh_single(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def ensure_categories() -> None:
    wanted = list(AR_CATS.values()) + list(EN_CATS.values())
    for slug, name in wanted:
        st, data = cli(
            f"wp term create category {sh_single(name)} --slug={slug} --porcelain",
            True,
        )
        print("term", slug, (data or {}).get("exit_code") if isinstance(data, dict) else st)


def category_slug_for(item: dict) -> str:
    cat = item.get("categories") or ""
    if item.get("lang") == "en":
        for name, (slug, _) in EN_CATS.items():
            if cat == name:
                return slug
        base = item.get("category_slug") or CAT_SLUG.get(cat, "finishing-decor")
        return f"{base}-en" if not base.endswith("-en") else base
    if cat in AR_CATS:
        return AR_CATS[cat][0]
    return item.get("category_slug") or CAT_SLUG.get(cat, "finishing-decor")


def service_slug_for(item: dict) -> str:
    return item.get("category_slug") or CAT_SLUG.get(item.get("categories") or "", "")


def set_terms_and_meta(post_id: int, item: dict) -> None:
    cat_slug = category_slug_for(item)
    cli(f"wp post term set {post_id} category {cat_slug}", True)
    svc = service_slug_for(item)
    if svc:
        cli(f"wp post term add {post_id} service_categories {svc}", True)
    title = item.get("rank_math_title") or item["post_title"]
    desc = item.get("rank_math_description") or ""
    focus = item.get("rank_math_focus_keyword") or ""
    cli(f"wp post meta update {post_id} rank_math_title {sh_single(title)} --force", True)
    if desc:
        cli(
            f"wp post meta update {post_id} rank_math_description {sh_single(desc)} --force",
            True,
        )
    if focus:
        cli(
            f"wp post meta update {post_id} rank_math_focus_keyword {sh_single(focus)} --force",
            True,
        )


def patch_rank_math() -> None:
    patches = [
        (
            "wp option patch update rank-math-options-titles homepage_description "
            + sh_single(
                "ركن التطور مصر — تشطيبات وصيانة وحرفيون في محافظات مصر. معاينة ومقايسة بالجنيه المصري."
            )
        ),
        "wp option patch update rank-math-options-sitemap authors_sitemap off",
        "wp option patch update rank-math-options-sitemap items_per_page 500 --format=json",
        "wp option patch update rank-math-options-general breadcrumbs on",
        "wp option patch update rank-math-options-general breadcrumbs_home_label الرئيسية",
        (
            "wp option patch update rank-math-options-titles phone "
            + sh_single(PHONE_TEL)
        ),
    ]
    for cmd in patches:
        st, data = cli(cmd, True)
        print("patch", cmd[:70], (data or {}).get("exit_code") if isinstance(data, dict) else st)


def draft_default_privacy() -> None:
    st, data = req("/wp/v2/pages/3", "POST", {"status": "draft"})
    print("privacy-policy draft", st, data.get("status") if isinstance(data, dict) else data)


def main() -> None:
    payload = json.loads(DIST.read_text(encoding="utf-8"))
    state = load_state()
    items = payload["arabic"] + payload["english"]
    print("configure site…")
    configure_site()
    patch_rank_math()
    print("categories…")
    ensure_categories()
    print("pages…")
    create_pages(state, items)
    draft_default_privacy()
    ok = 0
    for i, item in enumerate(items, 1):
        slug = item["post_name"]
        pid = upsert_post(item, state, None, [])
        if not pid and slug in state["posts"]:
            pid = state["posts"][slug]
        if pid:
            set_terms_and_meta(pid, item)
            ok += 1
        if i % 10 == 0:
            print(f"  {i}/{len(items)} ok={ok}")
            save_state(state)
    save_state(state)
    cli("wp rewrite flush", True)
    cli("wp cache flush", True)
    cli("wp litespeed-purge all", True)
    print(f"DONE ok={ok}/{len(items)} whatsapp={WHATSAPP_INTL} phone={PHONE_TEL}")


if __name__ == "__main__":
    if not os.environ.get("WP_EG_APP_PASSWORD"):
        raise SystemExit("Set WP_EG_APP_PASSWORD")
    main()
