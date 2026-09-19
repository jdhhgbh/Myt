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

    # بيانات عشوائية للموقع الأول
    email_site_a = f"{generate_random_string()}@outlook.sa"
    password_site_a = generate_strong_password()
    first_name = generate_random_string(6).capitalize()
    last_name = generate_random_string(6).capitalize()

    # بيانات عشوائية للموقع الثاني
    email_site_b = f"{generate_random_string()}@gmail.com"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("==========================================")
        print("الخطوة 1: فتح الموقع الأول وحجز التجربة المجانية...")
        print("==========================================")
        page.goto(site_a_url, wait_until="networkidle")

        # التمرير لأسفل والضغط على Add to Cart للتجربة المجانية
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(2)

        # اختيار زر Add to Cart
        add_to_cart_btn = page.locator("a:has-text('Add to Cart'), button:has-text('Add to Cart')").first
        add_to_cart_btn.click()
        print("تم إضافة التجربة المجانية للسلة.")

        # انتظار تحميل صفحة البيانات
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        print("الخطوة 2: تعبئة البيانات في الموقع الأول...")
        # تعبئة الإيميل وكلمة السر
        page.fill("input[type='email']", email_site_a)
        page.fill("input[type='password']", password_site_a)

        # تعبئة الاسم والأسم الاخير والدولة
        if page.locator("input[name*='first_name']").is_visible():
            page.fill("input[name*='first_name']", first_name)
        if page.locator("input[name*='last_name']").is_visible():
            page.fill("input[name*='last_name']", last_name)

        # اختيار الدولة (Albania أو أي دولة متوفرة)
        if page.locator("select[name*='country']").is_visible():
            page.select_option("select[name*='country']", label="Albania")

        print("تم تعبئة البيانات، جاري الضغط على Review Order...")
        review_btn = page.locator("button:has-text('Review order'), input[value='Review order'], button:has-text('Complete')").first
        review_btn.click()

        # انتظار تحميل صفحة المراجعة
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        print("الخطوة 3: تأكيد الطلب إتمام الشراء...")
        complete_btn = page.locator("button:has-text('Complete Order'), input[value='Complete Order']").first
        complete_btn.click()

        print("انتظار 30 ثانية لاكتمل الطلب واستخراج الرابط...")
        time.sleep(30)
        page.wait_for_load_state("networkidle")

        # استخراج رابط M3U
        content = page.content()
        m3u_matches = re.findall(r'https?://[^\s"<>\']+\.php\?[^\s"<>\']+', content)
        
        m3u_url = ""
        for url in m3u_matches:
            if "m3u" in url or "username=" in url:
                m3u_url = url
                break

        if not m3u_url:
            # محاولة استخراج الرابط من العناصر مباشرة
            m3u_locator = page.locator("text=/http:\/\/.*get\.php.*/")
            if m3u_locator.count() > 0:
                m3u_url = m3u_locator.first.inner_text().strip()

        print(f"تم استخراج رابط القنوات بنجاح: {m3u_url}")

        if not m3u_url:
            raise Exception("لم يتم العثور على رابط M3U، يرجى التحقق من استجابة الموقع.")

        # ==========================================
        # الانتقال إلى الموقع الثاني
        # ==========================================
        print("==========================================")
        print("الخطوة 4: الانتقال إلى الموقع الثاني (MyTV BEST)...")
        print("==========================================")
        page.goto(site_b_url, wait_until="networkidle")

        # الضغط على Express Modification
        express_btn = page.locator("text='Express Modification'").first
        express_btn.click()
        time.sleep(2)

        # الضغط على Upload new playlist
        upload_new_btn = page.locator("text='Upload new playlist'").first
        upload_new_btn.click()
        time.sleep(2)

        print("الخطوة 5: تعبئة بيانات الشاشة ورابط M3U...")
        # تعبئة الإيميل
        page.fill("input[type='email']", email_site_b)

        # اختيار مصدر القائمة M3U URL
        select_source = page.locator("select").first
        if select_source.is_visible():
            select_source.select_option(label="M3U URL")

        # تعبئة رابط M3U
        m3u_input = page.locator("input[placeholder*='M3U'], input[name*='m3u'], textarea").first
        m3u_input.fill(m3u_url)

        # تحديد التشييك على الشروط I have read and agree
        checkbox = page.locator("input[type='checkbox']").first
        if not checkbox.is_checked():
            checkbox.check()

        # الضغط على Upload
        upload_submit_btn = page.locator("button:has-text('Upload')").first
        upload_submit_btn.click()
        print("تم إرسال القنوات، جاري معالجة صفحات القروبات...")
        time.sleep(5)

        # التعامل مع صفحتين القروبات وتجاوزها بالضغط على Skip
        for i in range(2):
            skip_btn = page.locator("text='Skip', button:has-text('Skip'), a:has-text('Skip')").first
            if skip_btn.is_visible():
                skip_btn.click()
                print(f"تم الضغط على Skip رقم {i+1}")
                time.sleep(3)

        print("==========================================")
        print("تمت العملية بنجاح بالكامل وتحديث القنوات على التلفزيون!")
        print("==========================================")

        browser.close()

if __name__ == "__main__":
    run()
