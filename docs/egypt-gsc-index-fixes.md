# إصلاح فهرسة Google Search Console — `/eg/sitemap_index.xml`

لقطة Search Console (آخر بيانات 2026-10-12): **873 مفهرسة** و**108 غير مفهرسة**.

| السبب في GSC | العدد | المصدر الحقيقي على `/eg/` |
|---|---:|---|
| نسخة بديلة بعلامة canonical صحيحة | 1 | زوج لغة واحد عولج بشكل سليم |
| تم الاكتشاف - لم تتم الفهرسة حتى الآن | 58 | أرشيفات مدن `*-en-unused` + صفحات إنجليزية ضعيفة اكتُشفت من السايت ماب |
| نسخة مكررة، اختارت Google نسخة أساسية غير التي حددها المستخدم | 36 | أرشيفات `/eg/en/city/` و`/eg/en/category/` مقابل العربية |
| تم الزحف - لم تتم الفهرسة حتى الآن | 13 | صفحات رقيقة (`leak`/`insul`/`maint`/`clean`) ومسار خدمات 404 |
| تم استبعاد الصفحة بواسطة علامة noindex | 0 | لم يكن هناك noindex فعّال قبل هذا الإصلاح |

لا يمكن تعديل ملفات القالب (`DISALLOW_FILE_EDIT`). كل الإصلاحات عبر Rank Math REST/خيارات ووردبريس.

## ما طُبّق على الموقع الحي

### محتوى ومسارات أُخرجت من الفهرسة أو من السايت ماب

- **421 مقالاً إنجليزياً**: `rank_math_robots = noindex, follow` (ما عدا صفحة Privacy).
- **851 عنوان Rank Math** كانت تتضمن رقم `01151481000` ونص إعلانات؛ استُبدلت بـ `%title% %sep% %sitename%`.
- **99 مصطلحاً** (مدن إنجليزية + مدن `*-en-unused` + تصنيفات إنجليزية + `leak`/`insul`/`maint`/`clean`): `rank_math_robots = noindex, follow` عبر Rank Math REST.
- **16 مدينة unused** فُرّغت من المقالات سابقاً (`count=0`) وأُسقطت من `cities-sitemap.xml`.
- أرشيف نوع المحتوى `services` (عربي وإنجليزي): noindex لأن الصفحة الوحيدة (`general-maintenance`) تُرجع **404 من القالب**. السايت ماب `services-sitemap.xml` أُوقف حتى يُصلح القالب النهائي مسار الخدمات.
- كاش LiteSpeed + كاش سايت ماب Rank Math بعد كل دفعة.

### السايت ماب بعد الإصلاح (متحقق 2026-10-20)

قبل الإصلاح كان الفهرس يضم نحو **982** رابطاً (منها ~475 `/en/`). بعده:

| ملف | روابط | ملاحظات |
|---|---:|---|
| `post-sitemap.xml` | 432 | المقالات العربية + `/eg/` + `/eg/en/` |
| `page-sitemap.xml` | 5 | بينها `/eg/en/privacy-policy/` (مفهرسة عمداً) |
| `category-sitemap.xml` | 7 | التصنيفات العربية فقط |
| `cities-sitemap.xml` | 43 | المدن العربية فقط |
| `services-sitemap.xml` | — | أُوقف |

**المجموع: 487.** لم يعد هناك `unused` ولا أرشيفات `/en/category` أو `/en/city` داخل السايت ماب.

### تحقق robots على صفحات حية

| URL | robots بعد الإصلاح |
|---|---|
| `/eg/` | `index, follow` |
| `/eg/category/craftsmen/` | `index, follow` |
| `/eg/city/north-coast/` | `index, follow` |
| `/eg/en/privacy-policy/` | `index, follow` |
| `/eg/en/city/north-coast-en/` | `noindex, follow` |
| `/eg/en/category/craftsmen-en/` | `noindex, follow` |
| `/eg/city/zamalek-en-unused/` | `noindex, follow` |
| `/eg/category/leak/` | `noindex, follow` |
| `/eg/en/services/` و`/eg/services/` | `noindex, follow` |
| `/eg/en/` (الرئيسية الإنجليزية = أرشيف المقالات) | ما زالت `index, follow` |

`/eg/robots.txt` ما زال 404 بسبب ThemeStatic. ملف `robots.txt` على جذر النطاق يتضمن بالفعل `Sitemap: https://www.rukn-eltatawer.com/eg/sitemap_index.xml`.

## ما يبقى بعد زحف Google القادم

Search Console لن تتحرك الأرقام فوراً؛ لقطة 12 أكتوبر سابقة على هذه التغييرات. بعد إعادة الزحف:

- المقالات والأرشيفات الإنجليزية + unused + التصنيفات الرقيقة ستنتقل إلى **تم استبعادها بواسطة noindex** بدل «اكتشاف/زحف/تكرار».
- العربية (مدن، تصنيفات، مقالات، الرئيسية) تبقى قابلة للفهرسة.

باقي يحتاج تفعيل المقتطف أو القالب النهائي:

1. **`/eg/en/`** ما زالت تُعامل كصفحة رئيسية (Polylang + `show_on_front=posts`) وتأخذ `homepage_robots` نفسه كالصفحة العربية. لا يوجد post/term meta لها. الحل: تفعيل `designs/egypt-live-hotfixes.php` في WPCode (PHP / Run Everywhere) — إنشاء المقتطف من WPVibe CLI محظور ويحتاج موافقة اللوحة.
2. **`/eg/robots.txt` 404** — نفس المقتطف يقدّم الملف كنص.
3. **`/eg/services/general-maintenance/` 404** — خطأ قالب (ThemeStatic/مسار CPT). المحتوى موجود (منشور 3042) لكن الزائر يُرجع 404. أُخرج من السايت ماب حتى تركيب قالب KAYAN النهائي.

لا تغيّر `homepage_custom_robots` إلى noindex: ذلك سيُخرج الرئيسية العربية أيضاً.
