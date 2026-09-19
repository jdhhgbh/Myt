import os
import re
import time
import random
import string
import requests
from playwright.sync_api import sync_playwright

DEVICE_ID = os.environ.get("MYTV_DEVICE_ID", "d2ae-801d-d2f7-94d5-9398")

def generate_random_str(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def create_mailtm_account():
    """إنشاء حساب بريد حقيقي ونظيف عبر Mail.tm API"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # 1. جلب الدومين المتاح
    res_domain = session.get("https://api.mail.tm/domains").json()
    domain = res_domain['hydra:member'][0]['domain']
    
    # 2. إنشاء اسم بريد وكلمة سر
    username = f"user_{generate_random_str()}"
    email = f"{username}@{domain}"
    password = f"P@ss_{generate_random_str(10)}"
    
    # 3. تسجيل الحساب
    session.post("https://api.mail.tm/accounts", json={"address": email, "password": password})
    
    # 4. جلب التوكن (Token)
    res_token = session.post("https://api.mail.tm/token", json={"address": email, "password": password}).json()
    token = res_token.get("token")
    
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session, email

def check_mailtm_inbox(session):
    """فحص الرسائل الواردة من Mail.tm"""
    try:
        res = session.get("https://api.mail.tm/messages").json()
        messages = res.get('hydra:member', [])
        for msg in messages:
            msg_id = msg['id']
            # جلب تفاصيل الرسالة
            msg_detail = session.get(f"https://api.mail.tm/messages/{msg_id}").json()
            body = msg_detail.get('html', [''])[0] if isinstance(msg_detail.get('html'), list) else msg_detail.get('html', '')
            if not body:
                body = msg_detail.get('text', '')
            return body
    except Exception as e:
        print(f"تنبيه أثناء فحص البريد: {e}")
    return None

def run():
    print("1. جاري إنشاء بريد إلكتروني نظيف عبر Mail.tm...")
    mail_session, temp_email = create_mailtm_account()
    print(f"تم الحصول على البريد: {temp_email}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )

        # 2. فتح موقع Greatest IPTV والتسجيل
        page_iptv = context.new_page()
        print("2. جاري فتح موقع Greatest IPTV...")
        page_iptv.goto("https://www.greatestiptv.com/home/", wait_until="domcontentloaded", timeout=60000)

        page_iptv.click("text=Try 36 hours free")

        page_iptv.wait_for_selector("input[type='email']", timeout=20000)
        page_iptv.fill("input[type='email']", temp_email)
        page_iptv.click("text=ACTIVATE YOUR FREE TRIAL")
        print("3. تم تقديم طلب التفعيل، بانتظار وصول البريد...")

        # 3. فحص وصول البريد عبر API
        print("4. فحص البريد الوارد...")
        mail_body = None
        start_time = time.time()
        timeout = 180  # 3 دقائق

        while time.time() - start_time < timeout:
            mail_body = check_mailtm_inbox(mail_session)
            if mail_body:
                print("تمت استعادة رسالة التفعيل بنجاح!")
                break
            time.sleep(6)

        if not mail_body:
            raise Exception("انتهت المهلة ولم تظهر رسالة التفعيل في صندوق البريد.")

        # 4. استخراج رابط M3U
        print("5. استخراج رابط M3U...")
        m3u_match = re.search(r'https?://[^\s"<]+\?username=[^\s"<&]+&password=[^\s"<&]+[^\s"<]*', mail_body)
        if not m3u_match:
            m3u_match = re.search(r'https?://[^\s"<]+/get\.php\?[^\s"<]+', mail_body)

        if not m3u_match:
            raise Exception("تعذر العثور على رابط M3U داخل الرسالة.")

        m3u_url = m3u_match.group(0).replace("&amp;", "&")
        print(f"تم استخراج رابط M3U بنجاح: {m3u_url}")

        # 5. التوجه لموقع MyTV وتحديث التلفزيون
        page_tv = context.new_page()
        mytv_link = f"https://mytv.best/qr-code/?action=modification&cc=sa&utm_source=app&utm_medium=organic&utm_campaign=upload&tvid={DEVICE_ID}&lang=ar-SA"
        print("6. الانتقال إلى موقع MyTV...")
        page_tv.goto(mytv_link, wait_until="domcontentloaded", timeout=60000)

        page_tv.click("text=Express Modification")
        page_tv.click("text=Upload new playlist")

        # تعبئة البيانات
        print("7. إدخال بيانات الجهاز والتحديث...")
        page_tv.fill("input[type='email']", f"user_{int(time.time())}@gmail.com")

        page_tv.select_option("select", label="M3U URL")
        page_tv.fill("textarea", m3u_url)

        page_tv.check("input[type='checkbox']")
        page_tv.click("button:has-text('Upload')")

        # التجاوز (Skip)
        print("8. جاري رفع القائمة للتلفزيون والتجاوز...")
        page_tv.wait_for_selector("text=Skip", timeout=120000)
        page_tv.click("text=Skip")

        page_tv.wait_for_selector("text=Skip", timeout=30000)
        page_tv.click("text=Skip")

        print("9. تم إكمال العملية بنجاح وتحديث التلفزيون!")
        browser.close()

if __name__ == "__main__":
    run()
