import random
import string
from playwright.sync_api import sync_playwright

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def run():
    # توليد بريد إلكتروني مع تغيير النص بعد علامة الزائد
    base_prefix = "zwri"
    domain = "outlook.sa"
    random_suffix = generate_random_string(8)
    email = f"{base_prefix}+{random_suffix}@{domain}"
    full_name = "User " + generate_random_string(5)

    print(f"Executing trial request with Email: {email}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # الانتقال إلى رابط الصفحة
        page.goto("https://saudiptv.com/checkout?plan=1m")

        # الضغط على زر التجربة المجانية إذا كان متوفرًا لتشغيل النموذج
        try:
            page.click("text=Try Free Trial", timeout=5000)
        except Exception:
            pass

        # تعبئة اسم المستخدم والبريد الإلكتروني
        page.fill("input[placeholder='John Doe']", full_name)
        page.fill("input[placeholder='you@example.com']", email)

        # الضغط على زر Get Free Trial لتأكيد الطلب
        page.click("button:has-text('Get Free Trial'), input[value='Get Free Trial']")

        page.wait_for_timeout(5000)
        print("Request submitted successfully.")
        browser.close()

if __name__ == "__main__":
    run()
