# 📡 رصد — Rasd Monitoring App

لوحة متابعة المصادر — تجمع آخر منشورات الشخصيات والمنظمات المرصودة من X (تويتر)
+ روابط مباشرة لصفحات فيسبوك، مقسمة بالفئات (علماء وشخصيات، الإخوان، أوروبا،
أمريكا الشمالية، آسيا، فيسبوك).

## التشغيل

### الطريقة الأسرع (Windows)

دبل-كليك على **`START.bat`** — هيـ:
1. يتأكد من تثبيت requirements
2. يشغّل الـ backend على `http://127.0.0.1:8765`
3. يفتح المتصفح تلقائياً

### يدوياً

```bash
cd backend
pip install -r requirements.txt
python main.py
# افتح http://127.0.0.1:8765
```

## الهيكل

```
rasd-app/
├── backend/
│   ├── main.py           # FastAPI + يقدّم الواجهة
│   ├── x_client.py       # سحب تويتر بـ guest token (مفيش كوكيز شخصية)
│   ├── sources.py        # قائمة الحسابات بالفئات
│   └── requirements.txt
├── frontend/
│   └── index.html        # React عبر CDN — ملف واحد بدون build
├── START.bat
└── README.md
```

## المصادر المرصودة

| الفئة | العدد | المصادر |
|---|---|---|
| الشخصيات والعلماء | 15 | علي القره داغي، عصام البشير، النفيسي، الشنقيطي، عبدالله الشريف، ... |
| الإخوان الرسمية | 2 | ikhwansocial, ikhwanonline |
| المنظمات الأوروبية | 14 | ecfrorg، FEMYSO، MAB، Cordoba، MCB، ... |
| أمريكا الشمالية | 3 | CAIR، ISNA، ICNA |
| آسيا والمحيط الهادى | 7 | JI Pakistan، JI Hind، BJI، PKS، IUMS، ... |
| صفحات Facebook | 6 | IIIT، GIO Kerala، BritIslam، NAIT، ... |

**إجمالى:** 41 حساب X + 6 صفحات فيسبوك.

لتعديل المصادر، عدّل [`backend/sources.py`](backend/sources.py).

## API endpoints

- `GET /api/categories` — قائمة الفئات بألوانها
- `GET /api/sources?category=X` — قائمة الحسابات (فلتر بالفئة اختيارى)
- `GET /api/feed?category=X&per_account=5&date_filter=7d&force=0`
  — يجمع آخر منشورات كل الحسابات بالتوازى. كاش 10 دقائق.

## ملاحظات

- **بدون كوكيز شخصية** — الـ scraper يستخدم guest token عام بس، آمن للنشر.
- **Facebook** — حالياً بيظهر رابط مباشر للصفحة بس (مش سحب فعلى)، لأن
  Facebook بيمنع الـ scraping للصفحات الرسمية بدون OAuth.
- **Caching** — الـ feed مكاشش 10 دقائق، وكل حساب 15 دقيقة. استخدم زر "تحديث"
  للتجاهل.
- **Rate limits** — لو X رجّع 429، استنى دقيقة وحاول تانى أو قلّل
  `per_account`.
