# =============================================================
# Rasd App — Sources Configuration
# =============================================================
# All monitored accounts grouped by category.
# Each entry: name_ar (Arabic display), handle (platform username),
# platform ("x" for Twitter/X, "fb" for Facebook).
# =============================================================

SOURCES = {
    "scholars": {
        "name_ar": "الشخصيات والعلماء",
        "name_en": "Scholars & Personalities",
        "color": "#5dafa3",
        "accounts": [
            {"name_ar": "د. علي القره داغي",        "handle": "Ali_AlQaradaghi",  "platform": "x"},
            {"name_ar": "أ.د. عصام البشير",         "handle": "dressamalbashir",  "platform": "x"},
            {"name_ar": "أنيس منصور",               "handle": "anesmansory",      "platform": "x"},
            {"name_ar": "د. عبدالله النفيسي",       "handle": "DrAlnefisi",       "platform": "x"},
            {"name_ar": "د. مصطفى جاويش",           "handle": "drmgaweesh",       "platform": "x"},
            {"name_ar": "محمد الهاشمي الحامدي",    "handle": "MALHACHIMI",       "platform": "x"},
            {"name_ar": "Dr. Zawba",                "handle": "drzawba",          "platform": "x"},
            {"name_ar": "تاج السر عثمان",           "handle": "tajalsserosman",   "platform": "x"},
            {"name_ar": "أسامة جاويش",              "handle": "osgaweesh",        "platform": "x"},
            {"name_ar": "محمد الصغير",              "handle": "drassagheer",      "platform": "x"},
            {"name_ar": "محمد مختار الشنقيطي",     "handle": "mshinqiti",        "platform": "x"},
            {"name_ar": "د. يحيى غنيم",             "handle": "YahyaGhoniem",     "platform": "x"},
            {"name_ar": "عماد البحيري",             "handle": "EmadAlbeheery",    "platform": "x"},
            {"name_ar": "عبدالله الشريف",           "handle": "AbdullahElshrif",  "platform": "x"},
            {"name_ar": "عبدالحميد قطب",            "handle": "AbdAlhamed_kotb",  "platform": "x"},
        ],
    },

    "brotherhood_official": {
        "name_ar": "الإخوان المسلمين - الحسابات الرسمية",
        "name_en": "Muslim Brotherhood - Official",
        "color": "#c084fc",
        "accounts": [
            {"name_ar": "الإخوان المسلمين", "handle": "ikhwansocial", "platform": "x"},
            {"name_ar": "إخوان أونلاين",    "handle": "ikhwanonline", "platform": "x"},
        ],
    },

    "europe": {
        "name_ar": "المنظمات الأوروبية",
        "name_en": "European Organizations",
        "color": "#60a5fa",
        "accounts": [
            {"name_ar": "مجلس مسلمي أوروبا",                 "handle": "eumuslims_org",   "platform": "x"},
            {"name_ar": "المجلس الأوروبي للإفتاء والبحوث",   "handle": "ecfrorg",         "platform": "x"},
            {"name_ar": "Islamic Relief UK",                  "handle": "IslamicReliefUK", "platform": "x"},
            {"name_ar": "Muslim Association of Britain",      "handle": "MABOnline1",      "platform": "x"},
            {"name_ar": "FEMYSO",                             "handle": "FEMYSO",          "platform": "x"},
            {"name_ar": "Deutsche Muslimische Gemeinschaft",  "handle": "dmgonlinede",     "platform": "x"},
            {"name_ar": "Islamiska Förbundet (Sweden)",       "handle": "IslamiskaForbun", "platform": "x"},
            {"name_ar": "Musulmans de France",                "handle": "MF_Musulmans",    "platform": "x"},
            {"name_ar": "Islamic Relief DE",                  "handle": "IslamicReliefDE", "platform": "x"},
            {"name_ar": "IGMG — رؤية وطنية",                  "handle": "igmgorg",         "platform": "x"},
            {"name_ar": "المجلس المركزي للمسلمين بألمانيا",   "handle": "der_zmd",         "platform": "x"},
            {"name_ar": "مؤسسة قرطبة",                        "handle": "cordobafoundati", "platform": "x"},
            {"name_ar": "الصندوق الشرعي الإسلامي (MLFA)",     "handle": "mlfa",            "platform": "x"},
            {"name_ar": "Muslim Council of Britain",          "handle": "muslimcouncil",   "platform": "x"},
        ],
    },

    "americas": {
        "name_ar": "أمريكا الشمالية",
        "name_en": "North America",
        "color": "#f97316",
        "accounts": [
            {"name_ar": "CAIR National", "handle": "CAIRNational", "platform": "x"},
            {"name_ar": "ISNA",          "handle": "ISNAHQ",       "platform": "x"},
            {"name_ar": "ICNA",          "handle": "icna",         "platform": "x"},
        ],
    },

    "asia": {
        "name_ar": "آسيا والمحيط الهادي",
        "name_en": "Asia & Pacific",
        "color": "#fbbf24",
        "accounts": [
            {"name_ar": "DPP PKS (Indonesia)",              "handle": "PKSejahtera",  "platform": "x"},
            {"name_ar": "Australian National Imams Council","handle": "ImamsCouncil", "platform": "x"},
            {"name_ar": "Jamaat-e-Islami Hind",             "handle": "JIHMarkaz",    "platform": "x"},
            {"name_ar": "Jamaat-e-Islami Pakistan",         "handle": "JIPOfficial",  "platform": "x"},
            {"name_ar": "Bangladesh Jamaat-e-Islami",       "handle": "BJI_Official", "platform": "x"},
            {"name_ar": "IUMS Online",                      "handle": "iumsonline",   "platform": "x"},
            {"name_ar": "Jamaat Women",                     "handle": "jamaatwomen",  "platform": "x"},
        ],
    },

    "facebook_pages": {
        "name_ar": "صفحات فيسبوك",
        "name_en": "Facebook Pages",
        "color": "#1877f2",
        "accounts": [
            {"name_ar": "المعهد العالمي للفكر الإسلامي (IIIT)", "handle": "IIITfriends",     "platform": "fb"},
            {"name_ar": "Jamaat-e-Islami Kerala",               "handle": "giokerala",       "platform": "fb"},
            {"name_ar": "المركز الإسلامي بجنيف",                "handle": "100064719756947", "platform": "fb"},
            {"name_ar": "الجمعية الإسلامية في بريطانيا",        "handle": "BritIslam",       "platform": "fb"},
            {"name_ar": "حزب النهضة - طاجيكستان",               "handle": "nahzat.org",      "platform": "fb"},
            {"name_ar": "North American Islamic Trust (NAIT)",  "handle": "naitofficial",    "platform": "fb"},
        ],
    },
}


def flatten(categories=None, platform=None):
    out = []
    cats = categories if categories else list(SOURCES.keys())
    for cat_id in cats:
        cat = SOURCES.get(cat_id)
        if not cat:
            continue
        for acc in cat["accounts"]:
            if platform and acc["platform"] != platform:
                continue
            out.append({**acc, "category": cat_id, "category_name_ar": cat["name_ar"]})
    return out


def categories_meta():
    return [
        {
            "id": cid,
            "name_ar": c["name_ar"],
            "name_en": c["name_en"],
            "color": c["color"],
            "count": len(c["accounts"]),
        }
        for cid, c in SOURCES.items()
    ]
