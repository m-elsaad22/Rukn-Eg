# KAYAN Theme 1.4.12 — Egypt site re-audit

Live site: https://www.rukn-eltatawer.com/eg  
Active theme: **KAYAN Theme 1.4.12** (`kayan-theme`)  
Date: 2026-09-17  
Constraint: `DISALLOW_FILE_EDIT` — theme PHP cannot be patched from WPVibe; completable gaps were fixed via options, menus, Rank Math, Polylang, and header codes.

## What the new template changed

1.4.12 keeps the ThemeTree / YourColor widget architecture but adds packs: `kayan-seo`, `kayan-i18n`, `kayan-price-pay`, `fa-free-fixes`, `kayan-track`, `kayan-booking`. `style.css` says SEO is via Rank Math; the PHP actually **disables Rank Math on the frontend** unless `kayan_seo_disable` is set.

Classic templates `single.php`, `page.php`, `archive.php`, `404.php`, `search.php` are still absent by design (`index.php` + ThemeStatic Blade). That is not a missing-file bug for this theme.

## Critical frontend bug (fixed)

KAYAN SEO turns off Rank Math `Head::head` while relying on `title-tag`. Rank Math already removes WordPress `_wp_render_title_tag`, so **every URL had no `<title>`, no Open Graph, no robots meta**. Singular pages only had WordPress’s default canonical.

Fix applied (theme-supported escape hatch):

```
kayan_seo_disable = 1
```

After LiteSpeed purge, Rank Math prints title / description / canonical / OG / robots / JSON-LD again.

| URL | Before | After |
|---|---|---|
| Homepage | no title | `تشطيبات وصيانة وحرفيون في محافظات مصر - ركن التطور - مصر` |
| Contact | no title | `تواصل معنا - ركن التطور - مصر` |
| Article | no title | `{post title} - ركن التطور - مصر` |
| 404 | no title | `الصفحة غير موجودة - ركن التطور - مصر` |
| Category | no title | `{term} - ركن التطور - مصر` |

## Other completable fixes applied

| Change | Why |
|---|---|
| `kayan_i18n_disable = 1` | This WP install already lives at `/eg/`. KAYAN i18n treats Egypt as path `/eg` and builds `home_url() + /eg` → `/eg/eg/`. It also defaults missing country to **UAE**. |
| `kayan_i18n_default_country = eg` | Safety if i18n is turned back on. |
| Polylang `browser = false` | Stop sending English-browser visitors to `/en/`, which is still an Arabic duplicate (`html lang="ar"`). |
| Menu location `main-menu` → **Egypt** (term 215) | Theme mods had assigned leftover menu 748 (خدمات/المدن/المشاريع). Polylang already mapped 215 for ar+en; location now matches. |
| `YourColor_Schema_business` filled (Cairo / +201007707742 / EGP) | Theme schema printed an **empty** LocalBusiness when KAYAN SEO was on. With KAYAN SEO off, Rank Math owns JSON-LD. |
| `sitename__schema` + `logo__schema` | Used by theme schema if KAYAN SEO is re-enabled. |
| Rank Math `404_title` → Arabic | Was `Page Not Found %sep% %sitename%`. |
| `header___codes` | Kept `kayanShowCallButtons=true` and RTL isolate CSS. Removed the old “اختر الإمارة → محافظة” JS (finder PHP already says **اختر المدينة**). |
| Rewrite flush + LiteSpeed purge | So title/OG changes are public. |

Phone options remain `+201007707742` (call + WhatsApp). Homepage source has that number 16 times; old UAE/Egypt numbers are 0.

## Visitor-facing checks after the fix

- Nav (Egypt menu): الرئيسية، المدونة، تواصل معنا، عن الموقع، خريطة الموقع — all 200.
- Finder: step 1 **اختر الخدمة**, step 2 **اختر المدينة** (Egypt cities: القاهرة، الجيزة، …).
- WhatsApp / tel links use `201007707742`.
- Rank Math schema `@type` HomeAndConstructionBusiness, name ركن التطور - مصر, organization `url` is `https://rukn-eltatawer.com/eg` (correct).
- Remaining “إمارات” string is **only a CSS comment** in `city__widget.css` (`خريطة الإمارات الكحلية + كروت المدن القابلة للفتح`), not visible UI.

## Remaining blockers (need theme PHP or server)

These cannot be finished while `DISALLOW_FILE_EDIT` is on.

1. **Homepage canonical / og:url / CollectionPage `@id` are `https://rukn-eltatawer.com/eg/eg/`** (a **404**). Inner pages (contact, posts, categories) canonicalize correctly. JSON-LD Organization `url` is already `/eg`. Likely Rank Math + subdirectory `/eg` (and/or KAYAN i18n country path). Inner fix belongs in `kayan-i18n` (`path` for `eg` should be `''` on this install) or a Rank Math `frontend/canonical` filter that strips the extra `/eg`. A DB insert into `rank_math_redirections` was rejected by WPVibe.

2. **`/eg/robots.txt` is a 404 HTML page** (ThemeStatic intercepts `template_redirect` before `is_robots()`). Domain-root `https://www.rukn-eltatawer.com/robots.txt` already lists the Egypt sitemap. ThemeStatic should `return` early for `is_robots()`, `is_favicon()`, feeds, sitemaps.

3. **`<html lang="ar" dir="rtl">` is hardcoded** in `components/packs/#header/part.php`. KAYAN i18n has `kayan_i18n_get_html_attrs()` and a `language_attributes` filter, but the header never calls `language_attributes()`. `/en/` stays Arabic RTL.

4. **`/en/` is a duplicate of the Arabic homepage** (same widgets, same Arabic title). Polylang English has no translated front content. Hide `/en/` from the switcher or build real English pages; `noindex` the duplicate until then.

5. **UAE leftovers in PHP defaults** (not used when widget meta is filled, but still in the template):
   - `RuknContact/setup.php` `RUKN_CS_DEFAULT_WA = 971586634710`
   - `city__widget.php` default copy (دبي، أبوظبي، 7 إمارات) when `use_default_content` is on
   - Finder admin description still says “الخدمة + الإمارة”
   - Category/post metabox placeholders `+9715xxxxxxxx`

6. **`/blog/` and `/cities/` 404** — nav “المدونة” correctly goes to `/category/finishing-decor/`. Do not advertise `/blog/` or `/cities/` until those archives exist.

7. **Font Awesome is requested three times** (preload + print-onload + noscript) plus `fa-free-fixes.css?v=1.4.10` while theme version is 1.4.12. Footer still loads bundled `jquery-3.4.1.min.js` in addition to WordPress jQuery.

8. Invalid `<link rel="preload" as="font">` with **no `href`**.

9. Widget posts 19–28 are `future`; the homepage still renders them. WPVibe `post update` refused `widgets__posts`. Set them to `publish` in wp-admin if desired.

10. Rank Math LocalBusiness JSON-LD has **no `telephone`** even though `phone` / `knowledgegraph_phone` are `+201007707742`. Add a Local SEO location (address + phone) in Rank Math so the graph includes `telephone`.

## Do not re-enable KAYAN SEO on this site

Until the theme re-adds `_wp_render_title_tag` (or prints `<title>` itself) **and** emits canonical/OG, `kayan_seo_disable` must stay `1`. Re-enabling it will blank titles again.

If i18n is re-enabled, set Egypt `path` to empty string for this subdirectory install, or canonicals will keep doubling to `/eg/eg/`.
