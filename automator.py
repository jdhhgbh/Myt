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

    captured_m3u = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()

        # الاستماع لطلبات الاستجابة لالتقاط رابط M3U إذا صدر من الـ API مباشرة
        def handle_response(response):
            try:
                if "get.php" in response.url or "m3u" in response.url:
                    captured_m3u.append(response.url)
            except Exception:
                pass

        page.on("response", handle_response)

        print("1. فتح الصفحة الرئيسية للموقع الأول...")
        page.goto(site_a_url, wait_until="domcontentloaded")
        time.sleep(3)

        print("إضافة المنتج للسلة...")
        page.evaluate("""
            let btn = document.querySelector("a[href*='add-to-cart'], button[type='submit'], .add_to_cart_button");
            if (btn) btn.click();
        """)

        print("2. انتظار تحميل صفحة إدخال البيانات...")
        # انتظار حقل الإيميل بمرونة عبر JS تفادياً لـ Timeout
        page.wait_for_function("document.querySelector('input[type=\"email\"]') !== null", timeout=40000)
        time.sleep(2)

        print("3. تعبئة بيانات الحساب بواسطة JS المباشر...")
        page.evaluate(f"""
            let setVal = (selector, val) => {{
                let el = document.querySelector(selector);
                if (el) {{
                    el.value = val;
                    el.dispatchEvent(new Event('input', {{ 'bubbles': true }}));
                    el.dispatchEvent(new Event('change', {{ 'bubbles': true }}));
                }}
            }};
            setVal("input[type='email']", '{email_site_a}');
            setVal("input[type='password']", '{password_site_a}');
            setVal("input[name*='first_name']", '{first_name}');
            setVal("input[name*='last_name']", '{last_name}');
        """)
        time.sleep(2)

        print("4. إرسال الطلب وحجز التجربة...")
        page.evaluate("""
            let submitBtn = document.querySelector('#place_order') || document.querySelector('button.cfw-primary-btn');
            if (submitBtn) {{ submitBtn.click(); }}
            else {{
                let form = document.querySelector('form.checkout');
                if (form) form.submit();
            }}
        """)

        time.sleep(5)

        # الضغط المباشر الاحتياطي لإكمال الطلب
        page.evaluate("""
            let btn = document.querySelector('#place_order') || document.querySelector('button.cfw-primary-btn');
            if (btn && btn.offsetWidth > 0) btn.click();
        """)

        print("انتظار 25 ثانية لتوليد الرابط...")
        time.sleep(25)

        # استخراج رابط M3U
        m3u_url = ""
        if captured_m3u:
            m3u_url = captured_m3u[0]

        if not m3u_url:
            content = page.content()
            m3u_matches = re.findall(r'https?://[^\s"<>\']+(?:get\.php|m3u)[^\s"<>\']*', content, re.IGNORECASE)
            if m3u_matches:
                m3u_url = m3u_matches[0]

        if not m3u_url:
            links = page.locator("a[href*='get.php'], a[href*='m3u']").all()
            for link in links:
                href = link.get_attribute("href")
                if href:
                    m3u_url = href
                    break

        print(f"نتيجة الاستخراج: {m3u_url}")

        if not m3u_url:
            print("الرابط الحالي للصفحة:", page.url)
            raise Exception("تعذر العثور على رابط M3U. تحقق من إتمام الطلب.")

        # ==========================================
        # الانتقال إلى الموقع الثاني
        # ==========================================
        print("5. الانتقال إلى الموقع الثاني (MyTV BEST)...")
        page.goto(site_b_url, wait_until="domcontentloaded")
        time.sleep(3)

        express_btn = page.locator("text='Express Modification'").first
        express_btn.click()
        time.sleep(2)

        upload_new_btn = page.locator("text='Upload new playlist'").first
        upload_new_btn.click()
        time.sleep(2)

        print("6. تعبئة بيانات الشاشة ورابط M3U...")
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
