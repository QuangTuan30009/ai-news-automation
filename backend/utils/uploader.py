"""
Wrapper around the original upload.py script to keep automation logic reusable.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import markdown
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException, UnexpectedAlertPresentException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT.parents[1]
PROJECT_ROOT = BACKEND_ROOT.parents[2]

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_ROOT / ".env")
    load_dotenv()
except ImportError:
    pass


def log(level: str, message: str) -> None:
    levels = {
        "INFO": "\033[94m[INFO]\033[0m",
        "SUCCESS": "\033[92m[SUCCESS]\033[0m",
        "WARNING": "\033[93m[WARNING]\033[0m",
        "ERROR": "\033[91m[ERROR]\033[0m",
    }
    print(f"{levels.get(level, '[INFO]')} {message}")


def _read_posts(file_path: Path) -> List[Dict[str, Any]]:
    with file_path.open("r", encoding="utf-8") as stream:
        posts = json.load(stream)
    log("INFO", f"Đã nạp {len(posts)} bài viết từ file {file_path}")
    return posts


def _init_driver() -> webdriver.Chrome:
    chrome_options = Options()
    selenium_profile = PROJECT_ROOT / "SeleniumProfile"
    os.makedirs(selenium_profile, exist_ok=True)
    chrome_options.add_argument(f"--user-data-dir={selenium_profile}")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("detach", True)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    headless = os.environ.get("SELENIUM_HEADLESS", "1") != "0"
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(), options=chrome_options)
    return driver


def _dismiss_alert(driver: webdriver.Chrome) -> None:
    try:
        alert = driver.switch_to.alert
        log("INFO", f"Đóng alert tồn đọng: {alert.text}")
        alert.accept()
        time.sleep(1)
    except Exception:
        pass


def _safe_get(driver: webdriver.Chrome, url: str) -> None:
    _dismiss_alert(driver)
    try:
        driver.get(url)
    except UnexpectedAlertPresentException:
        _dismiss_alert(driver)
        driver.get(url)


def upload_articles(file_path: str) -> Dict[str, Any]:
    """
    Execute Selenium automation to publish articles to the target CMS.
    Returns a summary dictionary with success/error counts.
    """

    path = Path(file_path)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file JSON: {path}")

    posts = _read_posts(path)
    success_count = 0
    error_count = 0

    cms_base_url = os.environ.get("CMS_BASE_URL", "https://your-cms-domain.com").rstrip("/")
    admin_news_url = f"{cms_base_url}/admin/news"
    login_url = f"{cms_base_url}/login"

    driver = _init_driver()
    try:
        _safe_get(driver, admin_news_url)
        time.sleep(3)

        current_url = driver.current_url
        if current_url.startswith(login_url) or "/login" in current_url:
            username = os.environ.get("CMS_ADMIN_EMAIL")
            password = os.environ.get("CMS_ADMIN_PASSWORD")
            if not username or not password:
                log("ERROR", "Chưa cấu hình CMS_ADMIN_EMAIL hoặc CMS_ADMIN_PASSWORD trong file .env")
                raise ValueError("Vui lòng thiết lập biến môi trường CMS_ADMIN_EMAIL và CMS_ADMIN_PASSWORD trong .env.")

            btn = driver.find_element(By.XPATH, "//span[text()='Đăng nhập bằng email']/parent::button")
            time.sleep(2)
            btn.click()

            username_input = driver.find_element(By.XPATH, "//input[@placeholder='Nhập email']")
            username_input.send_keys(username)
            time.sleep(2)

            button = driver.find_element(By.XPATH, "//button[normalize-space()='Tiếp tục']")
            button.click()
            time.sleep(5)

            password_input = driver.find_element(By.XPATH, "//input[@placeholder='Nhập mật khẩu']")
            password_input.send_keys(password)
            time.sleep(2)

            submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Đăng nhập')]")
            submit_btn.click()
            time.sleep(2)

        for i, post in enumerate(posts, start=1):
            log("INFO", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            log("INFO", f"Đang đăng: [{i}/{len(posts)}]")

            _safe_get(driver, admin_news_url)
            time.sleep(3)

            try:
                btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Tạo bài viết mới')]"))
                )
                btn.click()
                time.sleep(3)
            except Exception as exc:  # noqa: BLE001
                log("ERROR", f"Không tìm thấy nút 'Tạo bài viết mới': {exc}")
                error_count += 1
                continue

            try:
                log("INFO", "Điền tiêu đề, slug và tóm tắt...")

                title_input = driver.find_element(By.NAME, "title")
                title_input.clear()
                title_input.send_keys(post["article_title"])
                time.sleep(0.5)

                slug_input = driver.find_element(By.NAME, "slug")
                slug_input.clear()
                slug_input.send_keys(post["slug"])
                time.sleep(0.5)

                log("SUCCESS", "Đã điền thông tin cơ bản")

            except Exception as exc:  # noqa: BLE001
                log("ERROR", f"Lỗi khi điền thông tin cơ bản: {exc}")
                error_count += 1
                continue

            try:
                log("INFO", "Upload ảnh đại diện...")
                upload_input = driver.find_element(By.XPATH, "//button[contains(text(), 'URL')]")
                upload_input.click()
                time.sleep(1)
                url_input = driver.find_element(By.XPATH, "//input[@id = 'image-url' and @placeholder = 'https://example.com/image.jpg']")
                url_input.click()
                time.sleep(0.5)
                url_input.send_keys("afdsfsd")
                time.sleep(2)

                url_input = driver.find_element(By.XPATH, "//input[@id = 'image-url-edit']")
                url_input.clear()
                url_input.send_keys(post["article_img_url"])

                alt_image = driver.find_element(By.XPATH, "//input[@id='image-alt' and @placeholder = 'Mô tả chi tiết nội dung hình ảnh']")
                alt_image.click()
                alt_image.send_keys(post["article_img_alt"])
                log("SUCCESS", "Upload ảnh thành công!")

                time.sleep(2)
            except Exception as exc:  # noqa: BLE001
                log("WARNING", f"Không upload được ảnh: {exc}")

            try:
                log("INFO", "Nhập nội dung bài viết...")
                contents_btn = driver.find_element(By.XPATH, "//div[contains(@class, 'tiptap ProseMirror')]")
                contents_btn.click()
                time.sleep(3)
                markdown_text = "\n\n".join(post["contents"])
                html_raw = markdown.markdown(markdown_text, extensions=["extra", "sane_lists", "nl2br"])
                soup = BeautifulSoup(html_raw, "html.parser")

                def is_inline_only(p_tag):
                    allowed = {"img"}
                    for child in p_tag.contents:
                        if isinstance(child, str) and child.strip():
                            return False
                        if hasattr(child, "name") and child.name not in allowed:
                            return False
                    return True

                for p in soup.find_all("p"):
                    if is_inline_only(p):
                        p.unwrap()

                html_content = str(soup)
                driver.execute_script(
                    """
                const el = document.querySelector('.tiptap.ProseMirror');
                el.innerHTML = arguments[0];
                el.dispatchEvent(new Event('input', { bubbles: true }));
                """,
                    html_content,
                )

                time.sleep(1)
                log("SUCCESS", "Đã nhập nội dung bài viết")
            except Exception as exc:  # noqa: BLE001
                log("ERROR", f"Lỗi khi nhập nội dung: {exc}")
                error_count += 1
                continue

            try:
                log("INFO", f"Nhập chuyên mục: {post.get('category', 'N/A')}...")
                category_input = driver.find_element(By.XPATH, "//button[@type='button' and @role='combobox']")
                actions = ActionChains(driver)
                actions.click_and_hold(category_input).perform()
                time.sleep(0.05)
                while True:
                    cate = driver.find_element(By.XPATH, "//input[@placeholder = 'Nhập chuyên mục khác...']").get_attribute("value")
                    if cate == post["category"]:
                        break
                    actions.send_keys(Keys.ENTER).perform()
                    time.sleep(0.05)

                    actions.send_keys(Keys.ARROW_DOWN).perform()
                    time.sleep(0.05)

                    actions.send_keys(Keys.ENTER).perform()
                    time.sleep(0.05)

                log("SUCCESS", "Đã nhập chuyên mục")
            except Exception as exc:  # noqa: BLE001
                log("WARNING", f"Không tìm thấy trường chuyên mục: {exc}")

            try:
                log("INFO", "Thêm các topics...")
                for topic in post.get("topics", []):
                    topic_input = driver.find_element(By.XPATH, "//input[@placeholder='Thêm topic tùy chỉnh']")
                    topic_input.click()
                    topic_input.send_keys(topic)
                    topic_input.send_keys(Keys.ENTER)
                    log("INFO", f"  ➕ Topic: {topic}")
                    time.sleep(0.5)
            except Exception as exc:  # noqa: BLE001
                log("WARNING", f"Không thêm được topic: {exc}")

            time.sleep(2)

            try:
                log("INFO", "Đang xuất bản bài viết...")
                publish_btn = driver.find_element(
                    By.XPATH, "//button[contains(text(),'Xuất bản') and not(@title='Xuất bản bài viết')]"
                )
                publish_btn.click()
                time.sleep(5)

                try:
                    alert = Alert(driver)
                    print("🔔 Thông báo:", alert.text)

                    if alert.text == "Có lỗi xảy ra khi tạo bài viết. Vui lòng thử lại.":
                        log("ERROR", "Có lỗi khi đăng bài")
                        error_count += 1
                    else:
                        log("SUCCESS", "Đã xác nhận thông báo xuất bản")
                        success_count += 1
                    alert.accept()
                except NoAlertPresentException:
                    pass

            except Exception as exc:  # noqa: BLE001
                log("ERROR", f"Lỗi khi xuất bản: {exc}")
                error_count += 1

            time.sleep(3)
            _dismiss_alert(driver)

        log("INFO", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log("SUCCESS", "🎉 Hoàn tất đăng bài!")
        log("INFO", "📈 Thống kê:")
        log("SUCCESS", f"   ✅ Thành công: {success_count}/{len(posts)}")
        log("ERROR", f"   ❌ Thất bại: {error_count}/{len(posts)}")
        time.sleep(10)

    finally:
        try:
            driver.quit()
        except Exception:  # noqa: BLE001
            pass

    return {
        "total": len(posts),
        "success": success_count,
        "failed": error_count,
        "file_path": str(path),
    }


__all__ = ["upload_articles"]
