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
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    res_domain = session.get("https://api.mail.tm/domains").json()
    domain = res_domain['hydra:member'][0]['domain']
    
    username = f"user_{generate_random_str()}"
    email = f"{username}@{domain}"
    password = f"P@ss_{generate_random_str(10)}"
    
    session.post("https://api.mail.tm/accounts", json={"address": email, "password": password})
    res_token = session.post("https://api.mail.tm/token", json={"address": email, "password": password}).json()
    token = res_token.get("token")
    
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session, email

def check_mailtm_inbox(session):
    try:
        res = session.get("https://api.mail.tm/messages").json()
        messages = res.get('hydra:member', [])
        for msg in messages:
            msg_id = msg['id']
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

        page = context.new_page()

        # 2. التوجه لموقع SaudiIPTV والتجربة المجانية
        print("2. جاري فتح موقع SaudiIPTV...")
        page.goto("https://saudiptv.com/checkout?plan=1m", wait_until="domcontentloaded", timeout=60000)

        # الضغط على زر Try Free Trial إن كان مظهراً
        if page.is_visible("text=Try Free Trial"):
            page.click("text=Try Free Trial")

        page.wait_for_selector("input[placeholder='John Doe'], input[name='name'], input[type='text']", timeout=15000)

        # تعبئة الاسم والإيميل
        print("3. إدخال بيانات طلب التجربة المجانية...")
        fake_name = f"User {generate_random_str(5)}"
        
        # محاولة تحديد الحقول بأكثر من طريقة لضمان الدقة
        try:
            page.fill("input[placeholder='John Doe']", fake_name)
        except Exception:
            page.fill("input[type='text']", fake_name)

        try:
            page.fill("input[placeholder='you@example.com']", temp_email)
        except Exception:
            page.fill("input[type='email']", temp_email)

        time.sleep(1)

        # الضغط على زر الحصول على التجربة
        print("4. تقديم الطلب...")
        page.click("button:has-text('Get Free Trial'), input[type='submit']")

        # 3. فحص البريد الوارد
        print("5. بانتظار وصول رسالة التفعيل إلى صندوق البريد...")
        mail_body = None
        start_time = time.time()
        timeout = 120  # دقيقتان

        while time.time() - start_time < timeout:
            mail_body = check_mailtm_inbox(mail_session)
            if mail_body:
                print("تمت استعادة رسالة التفعيل بنجاح!")
                break
            time.sleep(5)

        if not mail_body:
            raise Exception("انتهت المهلة ولم تظهر رسالة التفعيل في صندوق البريد.")

        # 4. استخراج رابط M3U
        print("6. استخراج رابط M3U...")
        m3u_match = re.search(r'https?://[^\s"<]+\?username=[^\s"<&]+&password=[^\s"<&]+[^\s"<]*', mail_body)
        if not m3u_match:
            m3u_match = re.search(r'https?://[^\s"<]+/get\.php\?[^\s"<]+', mail_body)

        if not m3u_match:
            raise Exception("تعذر العثور على رابط M3U داخل الرسالة.")

        m3u_url = m3u_match.group(0).replace("&amp;", "&")
        print(f"تم استخراج رابط M3U بنجاح: {m3u_url}")

        # 5. التوجه لموقع MyTV وتحديث الجهاز
        mytv_link = f"https://mytv.best/qr-code/?action=modification&cc=sa&utm_source=app&utm_medium=organic&utm_campaign=upload&tvid={DEVICE_ID}&lang=ar-SA"
        print("7. الانتقال إلى موقع MyTV...")
        page.goto(mytv_link, wait_until="domcontentloaded", timeout=60000)

        page.click("text=Express Modification")
        page.click("text=Upload new playlist")

        print("8. إدخال بيانات الجهاز والتحديث...")
        page.fill("input[type='email']", f"user_{int(time.time())}@gmail.com")
        page.select_option("select", label="M3U URL")
        page.fill("textarea", m3u_url)

        page.check("input[type='checkbox']")
        page.click("button:has-text('Upload')")

        print("9. جاري رفع القائمة للتلفزيون والتجاوز...")
        page.wait_for_selector("text=Skip", timeout=120000)
        page.click("text=Skip")

        page.wait_for_selector("text=Skip", timeout=30000)
        page.click("text=Skip")

        print("10. تم إكمال العملية بنجاح وتحديث التلفزيون!")
        browser.close()

if __name__ == "__main__":
    run()
