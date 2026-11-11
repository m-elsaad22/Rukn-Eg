# ركن التطور — مصر (Rukn-Eg)

محتوى ووردبريس لموقع [rukn-eltatawer.com/eg](https://rukn-eltatawer.com/eg/) جاهز للفهرسة بالعربية والإنجليزية.

## لماذا لم يظهر أي مقال في البحث؟

موقع مصر ووردبريس مستقل تحت `/eg/`، لكن كان يحتوي فقط على «Hello world!»، بلا خريطة موقع، وبلا روابط دائمة (`permalink_structure` فارغ). مسارات مثل `/eg/wp-json/` و`/eg/sitemap_index.xml` تُرجع 404 من لايت سبيد. الواجهة البرمجية تعمل عبر:

`https://rukn-eltatawer.com/eg/index.php?rest_route=/wp/v2/...`

مواقع `/sa/` و`/qa/` و`/kw/` و`/om/` مفهرسة لأنها تثبيتات مكتملة مع `sitemap_index.xml` و`robots.txt` ومقالات منشورة.

## ما الذي يفعله هذا المستودع

- يصحّح 421 مقالًا عربيًا: حالة **publish**، إزالة الصور المعطوبة، استبدال العناصر النائبة، نص مصري (محافظة / جنيه / مناخ / كمبوندات)، وربط داخلي، وSchema.
- يولّد 421 مقالًا إنجليزيًا موازيًا (`*-en`) لاستهداف البحث بالإنجليزية.
- ينشر عبر REST بعد ضبط التصنيفات والصفحات الأساسية.

```bash
python3 tools/build_egypt_content.py
WP_EG_USER=melsaad WP_EG_APP_PASSWORD='xxxx' python3 tools/publish_egypt.py
```

## بعد الرفع — لإكمال الفهرسة

1. من لوحة ووردبريس مصر: **الإعدادات ← الروابط الدائمة ← اسم المقالة** ثم حفظ. هذا يكتب قواعد `/eg/.htaccess` حتى تعمل `/eg/slug/` و`/eg/sitemap_index.xml` و`/eg/robots.txt`.
2. أضف في `robots.txt` للموقع الرئيسي:  
   `Sitemap: https://rukn-eltatawer.com/eg/sitemap_index.xml`
3. أرسل خريطة الموقع في Search Console (نسخة مصر + الإنجليزية).
4. ضع رقم واتساب/هاتف مصري (`+20`) في إعدادات القالب إن توفر؛ الرقم الحالي على الموقع هو واتساب الخليج المضبوط في `RuknCS`.
