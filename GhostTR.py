# استيراد المكتبات اللازمة
import json
import requests
import time
import os
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from flask import Flask, request, render_template_string

# تهيئة تطبيق فلاسك
app = Flask(__name__)

# ==========================================
# دوال التتبع والبحث (منطق السكربت الأصلي)
# ==========================================

def track_ip(ip):
    """دالة لجلب معلومات عنوان IP"""
    try:
        req_api = requests.get(f"http://ipwho.is/{ip}", timeout=5)
        data = req_api.json()
        if not data.get("success", True): # التحقق مما إذا كان الـ IP صالحاً
            return {"error": "عنوان IP غير صالح أو لم يتم العثور عليه."}
        
        return {
            "عنوان IP": data.get("ip"),
            "النوع": data.get("type"),
            "الدولة": f"{data.get('country')} {data.get('flag', {}).get('emoji', '')}",
            "المدينة": data.get("city"),
            "القارة": data.get("continent"),
            "خط العرض": data.get("latitude"),
            "خط الطول": data.get("longitude"),
            "مورد الخدمة (ISP)": data.get("connection", {}).get("isp"),
            "المنظمة (ORG)": data.get("connection", {}).get("org"),
            "رابط الخريطة": f"https://www.google.com/maps/@{data.get('latitude')},{data.get('longitude')},8z"
        }
    except Exception as e:
        return {"error": str(e)}

def track_phone(phone_number):
    """دالة لجلب معلومات رقم الهاتف"""
    try:
        parsed_number = phonenumbers.parse(phone_number, "ID")
        is_valid = phonenumbers.is_valid_number(parsed_number)
        
        if not is_valid:
            return {"error": "رقم الهاتف غير صالح."}

        timezone1 = timezone.time_zones_for_number(parsed_number)
        timezoneF = ', '.join(timezone1)
        
        return {
            "الموقع": geocoder.description_for_number(parsed_number, "ar") or geocoder.description_for_number(parsed_number, "en"),
            "مزود الخدمة": carrier.name_for_number(parsed_number, "ar") or carrier.name_for_number(parsed_number, "en"),
            "المنطقة الزمنية": timezoneF,
            "الصيغة الدولية": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "رمز الدولة": str(parsed_number.country_code),
            "الرقم المحلي": str(parsed_number.national_number)
        }
    except Exception as e:
        return {"error": f"صيغة غير صحيحة، تأكد من إضافة رمز الدولة (مثل +62...): {str(e)}"}

def track_username(username):
    """دالة للبحث عن اسم المستخدم في مواقع التواصل (محدود لتسريع الاستجابة)"""
    results = {}
    social_media = [
        {"url": "https://www.facebook.com/{}", "name": "Facebook"},
        {"url": "https://www.twitter.com/{}", "name": "Twitter"},
        {"url": "https://www.instagram.com/{}", "name": "Instagram"},
        {"url": "https://www.github.com/{}", "name": "GitHub"},
        {"url": "https://www.youtube.com/@{}", "name": "Youtube"},
        {"url": "https://www.tiktok.com/@{}", "name": "TikTok"}
    ]
    
    for site in social_media:
        url = site['url'].format(username)
        try:
            # استخدام مهلة زمنية قصيرة لتجنب تعليق الخادم
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                results[site['name']] = url
        except:
            pass
            
    if not results:
        return {"error": "لم يتم العثور على حسابات نشطة أو تعذر الوصول للمواقع."}
    return results


# ==========================================
# واجهة المستخدم (HTML + Tailwind CSS)
# ==========================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GhostTR - لوحة التحكم</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
        body { font-family: 'Tajawal', sans-serif; background-color: #0f172a; color: #e2e8f0; }
        .glitch-text { text-shadow: 2px 0 #ff00c1, -2px 0 #00fff9; }
    </style>
</head>
<body class="min-h-screen flex flex-col p-4 md:p-8">

    <header class="text-center mb-10">
        <h1 class="text-4xl md:text-6xl font-bold mb-2 glitch-text text-white">GhostTR Panel</h1>
        <p class="text-green-400 text-sm md:text-base">Code By HUNX04 - Modified for Render/Flask</p>
    </header>

    <main class="flex-grow max-w-4xl w-full mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
        
        <!-- لوحة الإدخال -->
        <div class="bg-slate-800 p-6 rounded-xl shadow-2xl border border-slate-700">
            <h2 class="text-2xl font-bold mb-6 text-indigo-400 border-b border-slate-700 pb-2">أدوات التتبع</h2>
            
            <!-- أداة IP -->
            <form method="POST" class="mb-6">
                <input type="hidden" name="action" value="ip">
                <label class="block text-sm mb-2 text-slate-300">تتبع عنوان IP:</label>
                <div class="flex gap-2">
                    <input type="text" name="target" required placeholder="مثال: 8.8.8.8" class="w-full bg-slate-900 border border-slate-600 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500">
                    <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition">بحث</button>
                </div>
            </form>

            <!-- أداة رقم الهاتف -->
            <form method="POST" class="mb-6">
                <input type="hidden" name="action" value="phone">
                <label class="block text-sm mb-2 text-slate-300">تتبع رقم هاتف (مع رمز الدولة):</label>
                <div class="flex gap-2">
                    <input type="text" name="target" required placeholder="مثال: +213xxxxxxxxx" class="w-full bg-slate-900 border border-slate-600 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500">
                    <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition">بحث</button>
                </div>
            </form>

            <!-- أداة اسم المستخدم -->
            <form method="POST" class="mb-2">
                <input type="hidden" name="action" value="username">
                <label class="block text-sm mb-2 text-slate-300">تتبع اسم المستخدم:</label>
                <div class="flex gap-2">
                    <input type="text" name="target" required placeholder="مثال: jdoe123" class="w-full bg-slate-900 border border-slate-600 rounded-lg p-2 text-white focus:outline-none focus:border-indigo-500">
                    <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition">بحث</button>
                </div>
            </form>
        </div>

        <!-- لوحة النتائج -->
        <div class="bg-slate-900 p-6 rounded-xl shadow-2xl border border-slate-700 overflow-y-auto max-h-[500px]">
            <h2 class="text-2xl font-bold mb-6 text-emerald-400 border-b border-slate-700 pb-2">النتائج</h2>
            
            {% if result %}
                {% if result.error %}
                    <div class="bg-red-900/50 border border-red-500 text-red-200 p-4 rounded-lg">
                        {{ result.error }}
                    </div>
                {% else %}
                    <ul class="space-y-3">
                        {% for key, value in result.items() %}
                            <li class="bg-slate-800 p-3 rounded border border-slate-700 flex flex-col">
                                <span class="text-indigo-400 text-sm font-bold mb-1">{{ key }}:</span>
                                {% if 'http' in str(value) %}
                                    <a href="{{ value }}" target="_blank" class="text-emerald-400 hover:underline break-all">{{ value }}</a>
                                {% else %}
                                    <span class="text-white">{{ value }}</span>
                                {% endif %}
                            </li>
                        {% endfor %}
                    </ul>
                {% endif %}
            {% else %}
                <div class="text-slate-500 text-center mt-20 flex flex-col items-center">
                    <svg class="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                    <p>قم بتنفيذ عملية بحث لعرض النتائج هنا.</p>
                </div>
            {% endif %}
        </div>

    </main>
</body>
</html>
"""

# ==========================================
# مسارات فلاسك (Routes)
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        action = request.form.get('action')
        target = request.form.get('target', '').strip()
        
        if action == 'ip' and target:
            result = track_ip(target)
        elif action == 'phone' and target:
            result = track_phone(target)
        elif action == 'username' and target:
            result = track_username(target)
            
    return render_template_string(HTML_TEMPLATE, result=result, str=str)

# ==========================================
# تشغيل الخادم (متوافق مع Render)
# ==========================================

if __name__ == '__main__':
    # الحصول على المنفذ من متغيرات البيئة الخاصة بـ Render، والافتراضي 5000
    port = int(os.environ.get("PORT", 5000))
    # تشغيل الخادم على جميع الواجهات 0.0.0.0 ليتمكن Render من الوصول إليه
    app.run(host='0.0.0.0', port=port, debug=False)
