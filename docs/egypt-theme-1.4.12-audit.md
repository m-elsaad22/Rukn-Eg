# ركن التطور مصر `/eg/` — محتوى وبيانات + مشاكل القالب المؤجلة

Live: https://www.rukn-eltatawer.com/eg  
Active theme on the server: **KAYAN Theme 1.4.12** (`kayan-theme`)  
Date: 2026-09-22  
WordPress: 7.1.1

## Scope of this round

Egypt’s theme will later be replaced by the **final UAE KAYAN build**. This round:

- **Did not** edit theme PHP/CSS/JS.
- **Did not** patch Canonical, `robots.txt`, `/en/`, UAE strings inside theme PHP, or KAYAN SEO.
- **Did** change `/eg/` posts, pages, plugin options, and taxonomies that do not depend on theme files.
- Theme/PHP issues are **recorded below only**, for the final-theme install.

`DISALLOW_FILE_EDIT` still blocks theme-file writes from WPVibe. That matches the new instruction: do not try.

Already-applied live options from the previous round stay as-is (`kayan_seo_disable=1`, `kayan_i18n_disable=1`, Egypt phone, Egypt menu). They were **not** changed again.

---

## Content / data scan (no theme files)

### Clean in published posts, terms, and city taxonomies

| Check | Result |
|---|---|
| Published `post_content` / titles containing دبي، أبوظبي، الإمارات، درهم، +971, Dubai, Emirates | **0 rows** |
| `cities` taxonomy (131 terms) | Egypt only |
| Tags (198) | no UAE leftovers |
| `kayan_numbers` table | empty |
| Public tel/WhatsApp on key URLs | `+201007707742` / `wa.me/+201007707742` |

English service posts that mention **AED** do so as a negation (“priced in Egyptian pounds — not Gulf villas or AED rate cards”). That is Egypt positioning, not leftover UAE copy.

### Leftovers that are data, not PHP

| Location | What it is | Action this round |
|---|---|---|
| `widgets__posts` **7, 8, 10, 11, 12, 15, 16** (published, old homepage pack) | Serialized `widget_post_meta` still has UAE copy, e.g. «ثقة الآلاف … في جميع أنحاء **الإمارات**», «خدماتنا في جميع **إمارات الدولة**» | Attempted `draft`; WPVibe refused `widgets__posts`. Live homepage currently uses Egypt widgets **19–28** (`اختر المدينة`, Cairo/Giza/…). **Remaining data** — draft or rewrite in wp-admin, or at final-theme install. |
| Widgets **19–28** | Egypt homepage widgets, status `future`; theme still renders them | Left untouched (content already Egypt). |
| `kayan_seo_home_reviews` | Option matches الإمارات in SQL | Left untouched (**KAYAN SEO** deferred). |
| `KayanPricePay` JS (`currency: "AED"`) | `wp_localize_script` from theme pack `kayan-price-pay` | Theme PHP — deferred. |
| CSS class `.uae-svg` / comment «خريطة الإمارات الكحلية» | Theme CSS | Deferred. |

### Thin / stub content that *is* WordPress data

Nine published posts were 4–9 words (old service stubs). Pages 1725–1727 were 2 short paragraphs. Page **3** was the default WordPress English “Suggested text” privacy policy at `/eg/en/privacy-policy/`. CPT `services` #3042 was «صيانة عامه للمباني».

Duplicate/empty categories remain from Polylang (`cleaning-en` count 0 vs `cleaning-en-en`, `غير مصنف` 96 English posts, 318 English posts under Cleaning). **`/en/` routing is deferred**; only the nine Arabic stubs were recategorized.

---

## Content / data fixes applied on the live site

Phone options remain `+201007707742`. No theme files were written.

### Rank Math (plugin options, not theme)

| Field | Before | After (live HTML) |
|---|---|---|
| `opening_hours` | `09:00-17:00` (mismatched contact 9am–9pm Cairo) | **`09:00-21:00` every day** |
| Local address | missing → JSON-LD had no `PostalAddress` | القاهرة / EG |
| `price_range` | missing | **EGP** |
| `url` / about / contact pages | missing | `/eg`, `/eg/about-egypt/`, `/eg/contact-us/` |
| Breadcrumbs 404 / archive / search | English | Arabic |
| Rank Math TOC title | `Table of Contents` | **محتويات الصفحة** |

After filling Rank Math’s website `url` + address, the homepage **canonical**, `og:url`, and CollectionPage `@id` currently print `https://rukn-eltatawer.com/eg/` (no extra `/eg/eg/`). That came from **plugin data**, not a theme PHP patch. Treat doubled `/eg/eg/` as a **theme/i18n regression risk** when the final KAYAN pack is installed (see deferred list).

`phone` / `knowledgegraph_phone` were already `+201007707742`. JSON-LD **still has no `telephone`**. Rank Math is not emitting it from those fields without a Local SEO location object. Remaining plugin-data gap; not theme PHP.

### Easy TOC (plugin)

- `heading_text` → **محتويات الصفحة**
- `heading-text-direction` → **rtl**

### Posts / pages / service CPT

| ID | URL | Change |
|---|---|---|
| 3008 | كشف تسربات المياه | Full Egypt article; category → `leaks-insulation` (238) |
| 3009 | عزل الأسطح | Full Egypt article; category → `leaks-insulation` (238) |
| 3010 | صيانة التكييف | Full Egypt article; category → `maintenance` (236) |
| 3011 | تنظيف وتعقيم | Full Egypt article; category → `cleaning` (237) |
| 3012 | مكافحة الحشرات | Full Egypt article; category → `pest-control` (239) |
| 3013 | سباكة وصيانة عامة | Full Egypt article; category → `maintenance` (236) |
| 3024 | نصائح للعناية بالمنزل | Full Egypt article; category → `maintenance` (236) |
| 3025 | متى تحتاج لفحص التسربات؟ | Full Egypt article; category → `leaks-insulation` (238) |
| 3026 | أهمية الصيانة الدورية | Full Egypt article; category → `maintenance` (236) |
| 3042 | `/eg/services/general-maintenance/` | Egypt service body (EGP, Cairo hours, +201007707742) |
| 1725 | `/eg/contact-us/` | Hours 9–9 Cairo, what to send, same phone |
| 1726 | `/eg/about-egypt/` | Egypt-only positioning (not a Gulf branch / AED) |
| 1727 | `/eg/privacy-egypt/` | Real Arabic privacy for `/eg/` |
| 3 | `/eg/en/privacy-policy/` | Replaced WP “Suggested text” stub with Egypt English privacy (same phone). **Did not change `/en/` routing.** |

LiteSpeed + object cache purged after the writes.

Live checks after purge: contact/about/privacy/AC/service pages show the new copy and `+201007707742`. Finder step 2 remains **اختر المدينة**. Homepage schema hours **09:00–21:00**, `priceRange` EGP, address القاهرة.

---

## Theme issues — record only (final KAYAN UAE theme install)

Do **not** patch these on the current Egypt theme.

1. **Canonical / `og:url` / CollectionPage `@id` doubling to `/eg/eg/`**  
   Caused by KAYAN i18n treating Egypt path as `/eg` on an install that already lives at `/eg/`. Currently Rank Math data prints `/eg/`; the PHP path logic can bring `/eg/eg/` back when i18n is enabled. Fix in `kayan-i18n` (empty `path` for this subdirectory) or a canonical filter **in the final theme**.

2. **`/eg/robots.txt` is a 404 HTML page**  
   ThemeStatic intercepts `template_redirect` before `is_robots()`. Domain-root `https://www.rukn-eltatawer.com/robots.txt` already lists the Egypt sitemap. ThemeStatic should return early for `is_robots()`, favicon, feeds, sitemaps.

3. **`/en/`**  
   Hardcoded `<html lang="ar" dir="rtl">` in `components/packs/#header/part.php` (never calls `language_attributes()`). `/eg/en/` is still an Arabic homepage duplicate. Polylang English has no translated front widgets. Hide, `noindex`, or ship real English front content **with the final theme**.

4. **UAE strings inside theme PHP** (defaults; widget meta usually overrides):  
   - `RuknContact/setup.php` `RUKN_CS_DEFAULT_WA = 971586634710`  
   - `city__widget.php` default copy (دبي، أبوظبي، 7 إمارات) when `use_default_content` is on  
   - Finder admin copy «الخدمة + الإمارة»  
   - Category/post metabox placeholders `+9715xxxxxxxx`  
   - `kayan-price-pay` localizes **`currency: "AED"`** (visible in every page’s JS)  
   - CSS comment «خريطة الإمارات الكحلية» / `.uae-svg`

5. **KAYAN SEO**  
   Pack disables Rank Math `Head::head` while Rank Math has already removed `_wp_render_title_tag` → **no `<title>` / OG / robots** unless `kayan_seo_disable=1`. Keep that option on this install. Final theme must print titles/canonical/OG itself **or** stop disabling Rank Math. Related options `kayan_hp_*` and `kayan_seo_home_reviews` are demo/SEO pack data — leave for the swap.

6. **Other theme HTML/assets (not content)**  
   Missing classic templates are by design (`index.php` + ThemeStatic). `/blog/` and `/cities/` 404. Font Awesome requested three times; footer still loads bundled `jquery-3.4.1.min.js`. Invalid `<link rel="preload" as="font">` with no `href`. Header splash `#loader` / `body.before-start`.

---

## Remaining `/eg/` content (not theme files)

These can wait for a later content pass; they were out of this round’s “no theme, no `/en/` routing” slice.

| Item | Notes |
|---|---|
| ~842 city×service articles | Thin/template; unique ratio low (see SEO audit PR). Not rewritten. |
| English categories | 318 posts under `cleaning-en-en`; empty `*-en` twins; `غير مصنف` on `/en/`. Tied to `/en/` / Polylang — deferred. |
| Featured images | Still none on posts. |
| UAE widget posts 6–18 | Published leftover pack; WPVibe cannot `post update` `widgets__posts`. Draft or delete in wp-admin. |
| Rank Math `telephone` in JSON-LD | Phone option is set; graph still omits `telephone`. Add a Local SEO location in Rank Math UI if the field is required. |
| Widget posts 19–28 status `future` | Harmless while the theme renders them; publish in wp-admin if desired. |

---

## Do not re-enable KAYAN SEO or i18n on this install

Until the **final** theme prints `<title>` / canonical / OG and uses an empty Egypt path under `/eg/`, keep:

```
kayan_seo_disable = 1
kayan_i18n_disable = 1
kayan_i18n_default_country = eg
```

Re-enabling either pack on 1.4.12 will blank titles and/or double URLs to `/eg/eg/` again.
