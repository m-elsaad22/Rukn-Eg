# ركن التطور — مصر (Rukn-Eg)

محتوى ووردبريس لموقع [rukn-eltatawer.com/eg](https://rukn-eltatawer.com/eg/) جاهز للفهرسة بالعربية والإنجليزية.

## لماذا لم يظهر أي مقال في البحث؟

موقع مصر ووردبريس مستقل تحت `/eg/`. الروابط الدائمة الآن `/%postname%/` وخريطة Rank Math تعمل. الواجهة البرمجية:

`https://rukn-eltatawer.com/eg/index.php?rest_route=/wp/v2/...`

مواقع `/sa/` و`/qa/` و`/kw/` و`/om/` مفهرسة لأنها تثبيتات مكتملة مع `sitemap_index.xml` و`robots.txt` ومقالات منشورة.

## ما الذي يفعله هذا المستودع

- يصحّح 421 مقالًا عربيًا: حالة **publish**، إزالة الصور المعطوبة، استبدال العناصر النائبة، نص مصري (محافظة / جنيه / مناخ / كمبوندات)، وربط داخلي، وSchema.
- يولّد 421 مقالًا إنجليزيًا موازيًا (`*-en`) لاستهداف البحث بالإنجليزية.
- ينشر عبر REST بعد ضبط التصنيفات والصفحات الأساسية، ثم يثبّت الروابط الدائمة وبيانات Rank Math.

```bash
python3 tools/build_egypt_content.py
WP_EG_USER=melsaad WP_EG_APP_PASSWORD='xxxx' python3 tools/harden_egypt_seo.py
```

## الفهرسة

الروابط الدائمة `/%postname%/` تعمل، وخريطة Rank Math على:

https://rukn-eltatawer.com/eg/sitemap_index.xml

وأُضيفت في روبوتس الموقع الرئيسي. المتبقي: إرسال الخريطة في Google Search Console.
