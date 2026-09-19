import os
import re
import random
import string
import time
from playwright.sync_api import sync_playwright

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_strong_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

def run():
    site_a_url = "https://xcodesiptv.com/i18/"
    site_b_url = "https://mytv.best/qr-code/?action=modification&cc=sa&utm_source=app&utm_medium=organic&utm_campaign=upload&tvid=d2ae-801d-d2f7-94d5-9398&lang=ar-SA"

    email_site_a = f"{generate_random_string()}@outlook.sa"
    password_site_a = generate_strong_password()
    first_name = generate_random_string(6).capitalize()
    last_name = generate_random_string(6).capitalize()
    email_site_b = f"{generate_random_string()}@gmail.com"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()

        print("1. فتح الموقع الأول وحجز التجربة المجانية...")
        page.goto(site_a_url, wait_until="domcontentloaded")
        time.sleep(3)

        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(1)

        add_to_cart_btn = page.locator("a:has-text('Add to Cart'), button:has-text('Add to Cart')").first
        add_to_cart_btn.click()
        print("تم الضغط على Add to Cart...")

        # انتظار تحميل عناصر نموذج Checkout
        page.wait_for_selector("#place_order, button[type='submit']", timeout=60000)
        time.sleep(2)

        print("2. تعبئة بيانات الحساب...")
        # تعبئة الإيميل والباسورد والأشخاص
        page.locator("input[type='email']").first.fill(email_site_a)
        
        pass_input = page.locator("input[type='password']").first
        if pass_input.is_visible():
            pass_input.fill(password_site_a)

        if page.locator("input[name*='first_name']").is_visible():
            page.locator("input[name*='first_name']").first.fill(first_name)
        if page.locator("input[name*='last_name']").is_visible():
            page.locator("input[name*='last_name']").first.fill(last_name)

        if page.locator("select[name*='country']").is_visible():
            page.locator("select[name*='country']").first.select_option(label="Albania")

        time.sleep(2)

        print("3. الضغط على زر Review Order / Complete Order...")
        # استهداف زر place_order بناءً على معرف id المباشر المعروض في السجل
        place_order_btn = page.locator("#place_order")
        
        # الضغط المرة الأولى (Review Order)
        place_order_btn.click(force=True)
        print("تم الضغط على الخطوة الأولى، انتظار تحديث النموذج...")
        time.sleep(4)

        # إذا ما زال الزر موجوداً ومطلوب الضغط عليه مرة ثانية للتأكيد (Complete Order)
        if place_order_btn.is_visible():
            print("الضغط على Complete Order لتأكيد الطلب النهائي...")
            place_order_btn.click(force=True)

        print("انتظار 30 ثانية لمعالجة الطلب واستخراج الرابط...")
        time.sleep(30)

        # استخراج رابط M3U
        content = page.content()
        m3u_matches = re.findall(r'https?://[^\s"<>\']+\.php\?[^\s"<>\']+', content)
        
        m3u_url = ""
        for url in m3u_matches:
            if "m3u" in url or "username=" in url:
                m3u_url = url
                break

        if not m3u_url:
            m3u_locator = page.locator("text=/http:\/\/.*get\.php.*/")
            if m3u_locator.count() > 0:
                m3u_url = m3u_locator.first.inner_text().strip()

        print(f"تم استخراج الرابط بنجاح: {m3u_url}")

        if not m3u_url:
            raise Exception("تعذر العثور على رابط M3U.")

        # ==========================================
        # الانتقال إلى الموقع الثاني
        # ==========================================
        print("4. الانتقال إلى الموقع الثاني (MyTV BEST)...")
        page.goto(site_b_url, wait_until="domcontentloaded")
        time.sleep(3)

        express_btn = page.locator("text='Express Modification'").first
        express_btn.click()
        time.sleep(2)

        upload_new_btn = page.locator("text='Upload new playlist'").first
        upload_new_btn.click()
        time.sleep(2)

        print("5. تعبئة بيانات الشاشة ورابط M3U...")
        page.locator("input[type='email']").first.fill(email_site_b)

        select_source = page.locator("select").first
        if select_source.is_visible():
            select_source.select_option(label="M3U URL")

        m3u_input = page.locator("input[placeholder*='M3U'], input[name*='m3u'], textarea").first
        m3u_input.fill(m3u_url)

        checkbox = page.locator("input[type='checkbox']").first
        if not checkbox.is_checked():
            checkbox.check()

        upload_submit_btn = page.locator("button:has-text('Upload')").first
        upload_submit_btn.click()
        print("تم إرسال القنوات، جاري معالجة صفحات القروبات...")
        time.sleep(5)

        for i in range(2):
            skip_btn = page.locator("text='Skip', button:has-text('Skip'), a:has-text('Skip')").first
            if skip_btn.is_visible():
                skip_btn.click()
                print(f"تم الضغط على Skip رقم {i+1}")
                time.sleep(3)

        print("تمت العملية بنجاح بالكامل!")
        browser.close()

if __name__ == "__main__":
    run()
