import os
import re
import time
from playwright.sync_api import sync_playwright

DEVICE_ID = os.environ.get("MYTV_DEVICE_ID", "d2ae-801d-d2f7-94d5-9398")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        # 1. فتح موقع البريد المؤقت وتوليد الإيميل
        page_mail = context.new_page()
        print("1. جاري فتح موقع البريد المؤقت...")
        page_mail.goto("https://temp-mail.org/ar/", wait_until="domcontentloaded", timeout=60000)
        
        # الانتظار حتى يظهر الإيميل
        page_mail.wait_for_selector("#mail", timeout=40000)
        time.sleep(3)
        temp_email = page_mail.input_value("#mail")
        print(f"تم الحصول على البريد المؤقت: {temp_email}")

        # 2. فتح موقع Greatest IPTV والتسجيل
        page_iptv = context.new_page()
        print("2. جاري فتح موقع Greatest IPTV...")
        page_iptv.goto("https://www.greatestiptv.com/home/", wait_until="domcontentloaded", timeout=60000)
        
        page_iptv.click("text=Try 36 hours free")
        
        page_iptv.wait_for_selector("input[type='email']", timeout=20000)
        page_iptv.fill("input[type='email']", temp_email)
        page_iptv.click("text=ACTIVATE YOUR FREE TRIAL")
        print("3. تم تقديم طلب التفعيل، بانتظار وصول البريد...")

        # 3. العودة لتبويب البريد المؤقت وانتظار وصول الرسالة مع تحديث الصفحة
        page_mail.bring_to_front()
        print("4. بانتظار وصول رسالة التفعيل وحث الصفحة على التحديث...")
        
        mail_found = False
        start_time = time.time()
        timeout = 150 # انتظار لمدة دقيقتين ونصف

        while time.time() - start_time < timeout:
            # التحقق مما إذا ظهرت الرسالة
            for selector in ["text=Greatest TV", "text=Greatest IPTV", "text=Your Free Trial is Ready", "text=noreply@greatestiptv.com"]:
                if page_mail.locator(selector).is_visible():
                    page_mail.click(selector)
                    mail_found = True
                    break
            
            if mail_found:
                break
                
            # إن لم تظهر، انتظر قليلاً ثم قم بإعادة تنشيط/تحميل الصفحة
            time.sleep(8)
            page_mail.reload(wait_until="domcontentloaded")

        if not mail_found:
            raise Exception("انتهت المهلة ولم تظهر رسالة التفعيل في صندوق البريد.")

        # قراءة محتوى الرسالة واستخراج الرابط
        print("5. قراءة الرسالة واستخراج رابط M3U...")
        time.sleep(3)
        content = page_mail.content()
        
        m3u_match = re.search(r'https?://[^\s"<]+\?username=[^\s"<&]+&password=[^\s"<&]+[^\s"<]*', content)
        if not m3u_match:
            m3u_match = re.search(r'https?://[^\s"<]+/get\.php\?[^\s"<]+', content)
            
        if not m3u_match:
            raise Exception("تعذر العثور على رابط M3U داخل الرسالة.")
            
        m3u_url = m3u_match.group(0).replace("&amp;", "&")
        print(f"تم استخراج رابط M3U بنجاح: {m3u_url}")

        # 4. التوجه لموقع MyTV وتحديث التلفزيون
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
