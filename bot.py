import os
import re
import time
import requests
from playwright.sync_api import sync_playwright

DEVICE_ID = os.environ.get("MYTV_DEVICE_ID", "d2ae-801d-d2f7-94d5-9398")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def create_mailtm_account():
    """إنشاء حساب بريد مؤقت مع إعادة المحاولة في حال فشل الاتصال"""
    for attempt in range(5):
        try:
            session = requests.Session()
            session.headers.update(HEADERS)
            
            # 1. جلب النطاقات المتاحة
            res = session.get("https://api.mail.tm/domains", timeout=15).json()
            domain = res['hydra:member'][0]['domain']
            
            # 2. إنشاء بيانات عشوائية
            username = f"user_{int(time.time())}_{attempt}"
            email = f"{username}@{domain}"
            password = "PassWord123!"
            
            # 3. تسجيل الحساب
            session.post("https://api.mail.tm/accounts", json={"address": email, "password": password}, timeout=15)
            
            # 4. جلب رمز التوثيق
            token_res = session.post("https://api.mail.tm/token", json={"address": email, "password": password}, timeout=15).json()
            token = token_res['token']
            
            return email, token
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
            print(f"محاولة {attempt + 1} فشلت بسبب انقطاع الاتصال: {e}. جاري إعادة المحاولة...")
            time.sleep(5)
            
    raise Exception("تعذر الاتصال بمركز البريد المؤقت بعد 5 محاولات.")

def wait_for_m3u_mailtm(token, timeout=120):
    """انتظار وصول البريد واستخراج رابط M3U"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        **HEADERS
    })
    
    start_time = time.time()
    print("بانتظار وصول البريد...")
    
    while time.time() - start_time < timeout:
        try:
            res = session.get("https://api.mail.tm/messages", timeout=15).json()
            messages = res.get('hydra:member', [])
            
            if messages:
                msg_id = messages[0]['id']
                msg_detail = session.get(f"https://api.mail.tm/messages/{msg_id}", timeout=15).json()
                body = msg_detail.get('text') or msg_detail.get('html') or ""
                
                # استخراج رابط M3U
                m3u_match = re.search(r'https?://[^\s"<]+\?username=[^\s"<&]+&password=[^\s"<&]+&type=m3u_plus&output=ts', body)
                if not m3u_match:
                    m3u_match = re.search(r'http://gr8iptv\.com/get\.php\?[^\s"<]+', body)
                    
                if m3u_match:
                    return m3u_match.group(0).replace("&amp;", "&")
        except Exception as e:
            print(f"تحذير مؤقت أثناء فحص البريد: {e}")
            
        time.sleep(5)
        
    raise Exception("انتهت المهلة ولم يصل رابط M3U.")

def run():
    # 1. إنشاء البريد المؤقت
    email, token = create_mailtm_account()
    print(f"1. تم إنشاء البريد المؤقت بنجاح: {email}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()

        # 2. التسجيل في موقع Greatest IPTV
        print("2. جاري فتح موقع Greatest IPTV...")
        page.goto("https://www.greatestiptv.com/home/", wait_until="domcontentloaded", timeout=60000)
        
        page.click("text=Try 36 hours free")
        
        page.wait_for_selector("input[type='email']", timeout=20000)
        page.fill("input[type='email']", email)
        page.click("text=ACTIVATE YOUR FREE TRIAL")
        print("3. تم تقديم طلب التفعيل، بانتظار وصول البريد...")

        # 3. قراءة البريد وجلب الرابط
        m3u_url = wait_for_m3u_mailtm(token)
        print(f"4. تم استخراج رابط M3U بنجاح: {m3u_url}")

        # 4. التوجه لموقع MyTV وتحديث التلفزيون
        mytv_link = f"https://mytv.best/qr-code/?action=modification&cc=sa&utm_source=app&utm_medium=organic&utm_campaign=upload&tvid={DEVICE_ID}&lang=ar-SA"
        print("5. الانتقال إلى موقع MyTV...")
        page.goto(mytv_link, wait_until="domcontentloaded", timeout=60000)
        
        page.click("text=Express Modification")
        page.click("text=Upload new playlist")

        # تعبئة البيانات
        print("6. إدخال بيانات الجهاز والتحديث...")
        page.fill("input[type='email']", f"user_{int(time.time())}@gmail.com")
        
        # اختيار M3U URL وإدخال الرابط
        page.select_option("select", label="M3U URL")
        page.fill("textarea", m3u_url)
        
        # الموافقة والرفع
        page.check("input[type='checkbox']")
        page.click("button:has-text('Upload')")
        
        # التجاوز (Skip)
        print("7. جاري رفع القائمة للتلفزيون والتجاوز...")
        page.wait_for_selector("text=Skip", timeout=120000)
        page.click("text=Skip")
        
        page.wait_for_selector("text=Skip", timeout=30000)
        page.click("text=Skip")

        print("8. تم إكمال العملية بنجاح وتحديث التلفزيون!")
        browser.close()

if __name__ == "__main__":
    run()
