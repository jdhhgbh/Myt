import os
import re
import time
import requests
from playwright.sync_api import sync_playwright

DEVICE_ID = os.environ.get("MYTV_DEVICE_ID", "d2ae-801d-d2f7-94d5-9398")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def get_1secmail_account():
    """إنشاء بريد مؤقت جديد عبر API"""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # استخدام نطاق موثوق
    res = session.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1", timeout=15).json()
    email = res[0]
    login, domain = email.split("@")
    return session, email, login, domain

def wait_for_m3u_1secmail(session, login, domain, timeout=120):
    """انتظار وصول الرسالة وقراءة رابط M3U"""
    start_time = time.time()
    print("بانتظار وصول البريد من Greatest IPTV...")
    
    while time.time() - start_time < timeout:
        try:
            res = session.get(f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}", timeout=15).json()
            if res:
                msg_id = res[0]['id']
                msg_detail = session.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}", timeout=15).json()
                body = msg_detail.get('textBody') or msg_detail.get('body') or ""
                
                # استخراج رابط m3u
                m3u_match = re.search(r'https?://[^\s"<]+\?username=[^\s"<&]+&password=[^\s"<&]+[^\s"<]*', body)
                if not m3u_match:
                    m3u_match = re.search(r'https?://[^\s"<]+/get\.php\?[^\s"<]+', body)
                
                if m3u_match:
                    return m3u_match.group(0).replace("&amp;", "&")
        except Exception as e:
            print(f"تنبيه مؤقت عند فحص البريد: {e}")
            
        time.sleep(5)
        
    raise Exception("انتهت المهلة ولم يصل رابط M3U.")

def run():
    # 1. إنشاء البريد المؤقت
    session, email, login, domain = get_1secmail_account()
    print(f"1. تم إنشاء البريد المؤقت بنجاح: {email}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
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
        m3u_url = wait_for_m3u_1secmail(session, login, domain)
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
