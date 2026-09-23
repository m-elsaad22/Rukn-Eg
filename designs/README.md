# تصاميم الصفحات (Call-main) وإصلاحات مصر الحية

`Call-main.zip` فُكّ إلى `designs/Call-main/`. هذه ملفات HTML لشكل الصفحات (هيدر، هيرو، أقسام) وليست محتوى مصر.

مرجع الهيدر في `home.html`: شعار + قائمة + بحث. بدون قائمة لغة ظاهرة في التدفق، وبدون همبرغر على سطح المكتب بجانب القائمة الكاملة.

## ما طُبّق على https://www.rukn-eltatawer.com/eg

ملفات القالب مقفلة (`DISALLOW_FILE_EDIT`). الإصلاحات عبر خيارات ووردبريس وCSS/JS في `header___codes`:

| مشكلة | إصلاح حي |
|---|---|
| شاشة `#loader` تغطي الهيدر | إخفاء فوري للّودر + إزالة `before-start` |
| حرف n / قائمة EN فوق الشعار | قواعد `.rukn-lc-menu{display:none}` وإخفاء زر اللغة (غير موجود في Call-main و`/en/` مكرر عربي) |
| همبرغر سطح المكتب | `header .ham.icon-btn{display:none!important}` من 769px |
| `"currency":"AED"` | خيار `currency` و`kayan_booking_currency` = **EGP** + JS |
| خريطة `.uae-svg` | مخفية بالـ CSS |
| الهاتف | ما زال `+201007707742` |

المصادر: `egypt-live-hotfixes.css` (يُحقن في `header___codes`).

## يحتاج موافقة في wp-admin (WPCode)

نُصّب **WPCode Lite**. إنشاء snippet من CLI محظور (يحتاج موافقة WPVibe). الصق `egypt-live-hotfixes.php` كـ PHP / Run Everywhere / Active لكي:

- يُخرج `/eg/robots.txt` كنص بدل 404
- `noindex` لمسار `/en/`

## ما لا يُحل بدون تعديل ملفات القالب

- قوالب `/blog/` و`/cities/` (ThemeStatic 404)
- أرقام الإمارات داخل PHP إن فُرغت الخيارات
- أيقونات `/wp-content/uploads/icon/` على دومين الإمارات الأب (الملفات غير موجودة تحت `/eg/`)
- ودجات `widgets__posts` 7–16
