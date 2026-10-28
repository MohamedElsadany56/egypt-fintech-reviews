"""
Label each review with complaint topics using keyword rules in Arabic, English and Franco.

A review can have several topics ("the app deducted my money and customer service never answered"
= failed transaction + customer service). Reviews matching no rule get no topic.

Rules run on `content_clean` from src/cleaning.py, where Arabic spelling is already unified
(أ/إ/آ -> ا, ة -> ه, ى -> ي), so each Arabic keyword needs only one spelling.
Arabic keywords match anywhere in a word, so "الكارت" also matches "والكارت" and "بالكارت";
keywords written with a leading "=" must be whole words ("=ربا" must not match "الكهربا").
English and Franco keywords match whole words only.

Usage:
    from topics import TOPICS, add_topics
    df = add_topics(df)        # adds one True/False column per topic + `topics` (list) + `n_topics`
"""

import re

import pandas as pd

# topic id -> (label, Arabic keywords, English/Franco keywords)
TOPICS = {
    "app_not_working": (
        "App won't open, crashes or is slow",
        ["مش بيفتح", "مبيفتحش", "ميفتحش", "مابيفتحش", "لا يفتح", "لم يفتح", "راضي يفتح", "عايز يفتح",
         "بيرضي يفتح", "بيقفل", "يقفل لوحده", "بيخرج لوحده", "يخرج لوحده", "بيخرجني", "يخرجني",
         "بيهنج", "هنج", "تهنيج", "بطي", "بطء", "تقيل", "مش شغال", "مش بيشتغل", "مبيشتغلش",
         "لا يعمل", "توقف عن العمل", "واقف", "كراش", "عطل", "اعطال", "ايرور", "خطا", "مشكله فنيه",
         "بعد التحديث", "التحديث الاخير", "التحديث الجديد", "اخر تحديث",
         "بيرضا يفتح", "التطبيق يقف", "البرنامج يقف", "بيقف", "راضي يشتغل", "عايز يشتغل", "عاوز يشتغل", "عاوز يفتح", "راضي يدخل", "عايز يخش", "مش بيحمل", "بيحمل", "يخرح"],
        ["crash", "crashes", "crashing", "crashed", "keeps stopping", "stopped working", "not working",
         "doesn't work", "does not work", "won't open", "wont open", "can't open", "cannot open",
         "doesn't open", "not opening", "not open", "freeze", "freezes", "freezing", "frozen", "lag",
         "lags", "lagging", "laggy", "slow", "bug", "bugs", "buggy", "glitch", "error", "white screen",
         "black screen", "msh sha8al", "msh shaghal", "mesh sha8al", "msh byft7", "closing", "closes", "keeps closing", "loading", "keeps loading", "erroring", "stopped", "not responding", "unresponsive", "crushing", "crushes", "crushed"],
    ),
    "failed_transaction": (
        "Money deducted, transfer failed or stuck",
        ["اتخصم", "اتخصمت", "خصم الفلوس", "خصم المبلغ", "تم الخصم", "تم خصم", "اتسحب", "اتسحبت",
         "بتتسحب", "فلوس معلق", "فلوسي معلق", "الفلوس معلق", "المبلغ معلق", "مبلغ معلق", "العمليه معلق",
         "عمليه معلق", "عمليات معلق", "التحويل معلق", "الرصيد معلق", "الفلوس بتعلق", "الفلوس اتعلقت",
         "تعليق المبلغ", "تعليق مبالغ", "تعليق الفلوس", "الفلوس لم تصل", "المبلغ لم يصل", "لم يصل المبلغ",
         "لم تصل الفلوس", "الفلوس موصلتش", "الفلوس ماوصلتش", "الفلوس موصلش", "الفلوس مبتوصلش", "فلوسي موصلتش",
         "المبلغ موصلش", "المبلغ ماوصلش", "الرصيد موصلش", "الرصيد ماوصلش", "الشحن موصلش", "التحويل موصلش",
         "التحويل ماوصلش", "للمستفيد", "مرجعتش",
         "مجاتش", "مجتش", "ترجع الفلوس",
         "ترجعلي", "يرجعولي", "رجوع الفلوس", "ترجيع", "استرداد", "استرجاع", "فشلت العمليه",
         "العمليه فشلت", "عمليه فاشله", "فشل التحويل", "التحويل فشل", "لم تتم", "لم يتم التحويل",
         "لم يتم السداد", "لم تسدد", "الفلوس راحت", "فلوسي راحت", "ضاعت",
         "بتنقص", "بينقص", "يسحب فلوس", "بيسحب فلوس", "يسحب فلوسك", "لم تظهر", "ولم تظهر", "يلغي المعامله", "بيلغي المعامله", "دفع مرتين", "تدفع مرتين", "اتدفع مرتين", "يجمدها", "مجمده", "عمليه تفشل", "العمليه بتفشل", "بياكلوها"],
        ["deducted", "deduct", "deducting", "didn't receive the money", "did not receive the money",
         "never received the money", "money never", "money was not received", "money hasn't arrived", "pending",
         "failed transaction", "transaction failed", "transfer failed", "failed transfer",
         "payment failed", "failed payment", "refund", "money back", "money is stuck", "money stuck",
         "lost my money", "charged twice", "double charged", "reversal", "reversed", "et5asam",
         "et5asamet", "double transaction", "took my money", "money disappeared", "not credited"],
    ),
    "login_verification": (
        "Sign-up, login, verification or waiting list",
        ["تسجيل", "اسجل", "سجلت", "الدخول", "دخول", "الكود", "كود التفعيل", "رمز",
         "رساله التفعيل", "التفعيل", "تفعيل الحساب", "رقم الهاتف", "رقم الموبايل", "الرقم المسجل",
         "غير مسجل", "الشريحه", "شريحه", "كلمه السر", "الباسورد", "باسورد", "كلمه المرور",
         "الرقم السري", "التحقق", "البطاقه الشخصيه", "البطاقه القوميه", "الرقم القومي", "سيلفي",
         "قايمه الانتظار", "قائمه الانتظار", "قايمه انتظار", "الويتنج",
         "ارسال الرساله", "ارسال رساله", "استقبال الرساله", "استقبال رساله", "الرساله لم", "رساله التحقق", "اسم المستخدم", "اليوزر", "غيرت الموبايل", "غيرت التليفون", "غيرت الهاتف", "غيرت موبايلي", "تليفون جديد", "الهاتف الجديد", "موبايل جديد", "الموبايل الجديد", "التليفون الجديد", "صوره البطاقه", "اصور البطاقه", "افعل الحساب", "افعل حسابي", "الترتيب", "ترتيبي", "دوري في", "لم تصلنا", "رسالتك لم تصل", "رسالتكم لم تصل"],
        ["login", "log in", "logging in", "sign up", "signup", "sign in", "signing", "register",
         "registration", "registering", "otp", "sms", "verification", "verify", "verified",
         "activation", "activate", "password", "passcode", "phone number", "national id", "id card",
         "selfie", "kyc", "waiting list", "waitlist", "sim", "fingerprint", "face id", "biometric", "varification", "verification code", "username", "user name", "my turn", "email verification", "new phone", "changed my phone", "new device", "changed phone"],
    ),
    "customer_service": (
        "Customer service unreachable or unhelpful",
        ["خدمه العملاء", "خدمه عملاء", "خدمه الععملاء", "كول سنتر", "الكول سنتر", "الخط الساخن",
         "الهوت لاين", "محدش بيرد", "محدش يرد", "محدش رد", "حد بيرد", "حد يرد", "مفيش رد",
         "لا يوجد رد", "لا احد يرد", "مبيردوش", "مش بيردو", "بيردوا", "الرد الالي", "الشكوي", "شكوي",
         "شكاوي", "الدعم الفني", "الشات", "واتساب", "الموظف", "موظف"],
        ["customer service", "customer support", "customer care", "support team", "support",
         "call center", "hotline", "no response", "no one answer", "no one answers", "nobody answers",
         "no reply", "no answer", "chat", "complaint", "complaints", "agent", "agents", "help line", "helpline"],
    ),
    "fees_interest": (
        "Fees, charges or interest",
        ["رسوم", "عموله", "مصاريف", "فوايد", "فوائد", "=ربا", "غرامه", "غرامات",
         "غالي", "غاليه", "الاسعار", "اسعار"],
        ["fee", "fees", "charges", "extra charge", "service charge", "commission", "interest", "interests",
         "expensive", "overpriced", "hidden", "penalty", "late fee"],
    ),
    "card": (
        "Card delivery, branches or ATM use",
        ["الكارت", "كارت", "الكرت", "كرت", "الفيزا", "فيزا", "ماكينه", "مكنه", "مكينه", "الصراف",
         "استلام البطاقه", "البطاقه لم", "البطاقه مش", "البطاقه ما", "بطاقه تيلدا", "بطاقه فوري",
         "البطاقه البنكيه", "مفيش فروع", "لا توجد فروع", "فروع في", "فرع في", "التسليم", "توصيل البطاقه", "استلم البطاقه", "استلام الكرت"],
        ["card", "cards", "atm", "atms", "visa", "mastercard", "meeza", "card delivery"],
    ),
    "security_device": (
        "Security block, unsupported phone or permissions",
        ["خيارات المطور", "وضع المطور", "اعدادات المطور", "=الامان", "الجهاز غير مدعوم", "غير متوافق",
         "جهازي غير مدعوم", "مش مدعوم علي", "غير مدعوم علي", "لا يدعم الجهاز", "لا يدعم جهاز",
         "لا يدعم موبايل", "لا يدعم تليفون", "مبيدعمش", "يدعم اندرويد", "هواوي", "هونر", "=روت", "جوجل بلاي",
         "خارج جوجل", "مش من جوجل", "الاذونات", "تطبيقات تانيه", "تطبيقات اخري", "برامج تانيه"],
        ["hooked", "rooted", "root", "jailbreak", "developer options", "developer mode", "debugging",
         "usb debugging", "accessibility", "security", "not supported", "unsupported", "huawei",
         "honor", "emulator", "permission", "permissions"],
    ),
    "abroad": (
        "Can't use it from abroad",
        ["خارج مصر", "بره مصر", "برا مصر", "من الخارج", "بالخارج", "في الخارج", "مسافر", "سافرت", "بسافر",
         "رومينج", "رقم دولي", "المغتربين", "مغترب", "السعوديه", "الكويت", "الامارات", "=قطر", "=دبي"],
        ["outside egypt", "outside of egypt", "abroad", "roaming", "travel", "traveling", "travelling",
         "international number", "expat", "expats", "saudi", "kuwait", "uae", "dubai", "qatar"],
    ),
    "rejected_limits": (
        "Application rejected or limit too low",
        ["اترفض", "مرفوض", "الرفض", "رفض طلبي", "رفضي", "رفضوا", "يترفض", "تم رفض", "غير مؤهل",
         "حد ائتماني", "الحد الائتماني", "حد اتماني", "الحد الاتماني", "الليميت", "ليميت", "الحد الاقصي", "حد التحويل", "بيرفضك", "رفضك", "بترفضو", "ترفضوه", "يتوافق عليك", "الموافقه علي"],
        ["rejected", "reject", "rejection", "declined", "not eligible", "credit limit", "limit",
         "limits", "approval"],
    ),
    "fraud_accusation": (
        "Accuses the company of fraud or theft",
        ["نصب", "نصاب", "حرامي", "حراميه", "سرقه", "سرقوا", "بيسرقوا", "سرقني", "احتيال", "كدابين",
         "كذابين", "استغلال", "ضحك علي", "تسريب البيانات", "بتسرب بيانات", "تسريب بيانات"],
        ["scam", "scams", "scammer", "scammers", "fraud", "fraudulent", "thief", "thieves", "steal",
         "stealing", "stole", "rip off", "ripoff", "liars", "nasabeen", "7aramya"],
    ),
    "missing_feature": (
        "Missing feature, bank or service",
        ["ياريت تضيفوا", "ياريت يضيفوا", "=تضيفوا", "=ضيفوا", "اضافه خاصيه", "مفيش خاصيه",
         "لا يوجد خيار", "مفيش خيار", "مفيش اختيار", "لا يوجد اختيار", "اتشالت", "تم ازاله", "شالوا",
         "ليه مفيش", "مش موجوده في التطبيق", "غير متوفره", "غير متاحه"],
        ["please add", "add option", "add the option", "no option to", "there's no option",
         "there is no option", "not listed", "please support", "should add", "missing feature"],
    ),
    "design_interface": (
        "Confusing design or interface",
        ["واجهه المستخدم", "الواجهه الجديده", "الواجهه القديمه", "الواجهه سييه", "شكل التطبيق",
         "شكل البرنامج", "التصميم", "الشكل الجديد", "الشكل القديم", "التطبيق معقد", "البرنامج معقد",
         "تطبيق معقد", "برنامج معقد", "صعب الاستخدام"],
        ["user interface", "new interface", "old interface", "interface is", "design", "the ui",
         "ui is", "ux", "complicated", "confusing", "user friendly", "not user-friendly",
         "hard to use", "difficult to use", "layout"],
    ),
}

TOPIC_LABELS = {k: v[0] for k, v in TOPICS.items()}


AR = "\u0600-\u06FF"


def _compile(arabic, latin):
    # A leading "=" marks a short Arabic keyword that must be a whole word ("=ربا" must not match "الكهربا").
    parts = [rf"(?<![{AR}])" + re.escape(k[1:]) + rf"(?![{AR}])" if k.startswith("=") else re.escape(k)
             for k in arabic]
    # Whole words for Latin keywords; allow an apostrophe-free variant ("doesnt", "cant").
    for k in latin:
        variants = {k, k.replace("'", "")}
        parts += [r"(?<![a-z])" + re.escape(v) + r"(?![a-z])" for v in variants]
    return re.compile("|".join(parts))


PATTERNS = {k: _compile(v[1], v[2]) for k, v in TOPICS.items()}


def match_topics(text):
    """List of topic ids found in one cleaned text."""
    if not isinstance(text, str) or not text:
        return []
    return [k for k, p in PATTERNS.items() if p.search(text)]


def add_topics(df, text_col="content_clean"):
    df = df.copy()
    found = df[text_col].fillna("").map(match_topics)
    for k in TOPICS:
        df[f"topic_{k}"] = found.map(lambda ts, k=k: k in ts)
    df["topics"] = found.map(lambda ts: ", ".join(ts))
    df["n_topics"] = found.map(len)
    return df


def matched_words(text, topic):
    """Which keywords triggered a topic (for checking the rules)."""
    return sorted(set(m.group(0) for m in PATTERNS[topic].finditer(text or "")))
