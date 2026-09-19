import os
import re
import time
import requests
from playwright.sync_api import sync_playwright

DEVICE_ID = os.environ.get("MYTV_DEVICE_ID", "d2ae-801d-d2f7-94d5-9398")

def get_temp_email():
    """جلب إيميل مؤقت مجاني عبر API 1secmail"""
    res = requests.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1")
    email = res.json()[0]
    login, domain = email.split("@")
    return email, login, domain

def wait_for_m3u_link(login, domain, timeout=120):
    """انتظار وصول بريد التفعيل وقراءة رابط M3U"""
    start_time = time.time()
    print("بانتظار وصول بريد التفعيل...")
    while time.time() - start_time < timeout:
        res = requests.get(f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}").json()
        if res:
            msg_id = res[0]['id']
            msg_detail = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}").json()
            body = msg_detail.get('textBody') or msg_detail.get('body') or ""
            
            # البحث عن رابط m3u داخل نص الرسالة
            m3u_match = re.search(r'https?://[^\s"<]+\?username=[^\s"<&]+&password=[^\s"<&]+&type=m3u_plus&output=ts', body)
            if not m3u_match:
                m3u_match = re.search(r'https?://[^\s"<]+/get\.php\?[^\s"<]+', body)
            
            if m3u_match:
                return m3u_match.group(0)
        time.sleep(5)
    raise Exception("انتهت المهلة ولم يصل رابط M3U إلى البريد المؤقت.")

def run():
    email, login, domain = get_temp_email()
    print(f"تم إنشاء البريد المؤقت: {email}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15")
        page = context.new_page()

        # الخطوة 1 و 2: طلب التجربة المجانية من Greatest IPTV
        print("1. جاري فتح موقع Greatest IPTV...")
        page.goto("https://www.greatestiptv.com/home/", wait_until="domcontentloaded")
        page.click("text=Try 36 hours free")
        
        page.wait_for_selector("input[type='email']", timeout=15000)
        page.fill("input[type='email']", email)
        page.click("text=ACTIVATE YOUR FREE TRIAL")
        print("2. تم تقديم طلب التفعيل، بانتظار البريد...")

        # الخطوة 3 و 4: الحصول على رابط M3U من البريد
        m3u_url = wait_for_m3u_link(login, domain)
        print(f"3. تم استخراج رابط M3U بنجاح: {m3u_url}")

        # الخطوة 5 و 6: التوجه لموقع MyTV
        mytv_link = f"https://mytv.best/qr-code/?action=modification&cc=sa&utm_source=app&utm_medium=organic&utm_campaign=upload&tvid={DEVICE_ID}&lang=ar-SA"
        print("4. الانتقال إلى موقع MyTV...")
        page.goto(mytv_link, wait_until="domcontentloaded")
        
        page.click("text=Express Modification")
        page.click("text=Upload new playlist")

        # الخطوة 7: تعبئة بيانات الجهاز ورابط القناة
        print("5. إدخال بيانات الجهاز والتحديث...")
        page.fill("input[name='device_id']", DEVICE_ID) if page.locator("input[name='device_id']").count() > 0 else None
        
        # تعبئة البريد العشوائي والرابط
        page.fill("input[type='email']", f"user_{int(time.time())}@gmail.com")
        
        # اختيار M3U URL وإدخال الرابط
        page.select_option("select", label="M3U URL") if page.locator("select").count() > 0 else None
        page.fill("textarea, input[name='m3u_url'], input[placeholder*='http']", m3u_url)
        
        # الموافقة على الشروط
        page.check("input[type='checkbox']")
        
        # الخطوة 8: الضغط على Upload والانتظار
        print("6. جاري رفع القائمة (قد يستغرق العملية حتى دقيقتين)...")
        page.click("button:has-text('Upload'), input[value='Upload']")
        
        # التجاوز (Skip) للصفحتين التاليتين
        page.wait_for_selector("text=Skip", timeout=120000)
        page.click("text=Skip")
        
        page.wait_for_selector("text=Skip", timeout=30000)
        page.click("text=Skip")

        print("7. تم إكمال العملية بنجاح وتحديث التلفزيون!")
        browser.close()

if __name__ == "__main__":
    run()
