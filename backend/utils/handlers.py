"""
Crawler handlers shared by the CLI and FastAPI backend.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from typing import List

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from .translator import translate_text


def gen_slug(text: str) -> str:
    """Normalize Vietnamese text and generate a slug-friendly string."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text


def json_to_markdown(cat: str, json_data, output_path: str = "output.json") -> None:
    """Convert JSON article(s) into Markdown-ready structure and persist to disk."""
    if isinstance(json_data, dict):
        json_data = [json_data]

    result = []
    for article in json_data:
        title = article.get("title") or article.get("article_title", "No Title")
        img = article.get("img") or article.get("article_img_url", None)
        contents = article.get("contents", [])
        tags = article.get("tags", [])

        md_lines = []
        for paragraph in contents:
            md_lines.append(f"{paragraph}\n\n")

        news = {
            "article_title": title,
            "slug": gen_slug(title),
            "article_img_url": img,
            "article_img_alt": title,
            "contents": md_lines,
            "category": cat,
            "topics": tags,
        }
        result.append(news)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"File JSON có chứa Markdown đã được lưu: {output_path}")


def _translate_and_clean(text: str) -> str:
    translated = translate_text(text)
    return re.sub(r"^vi:\s*", "", translated, flags=re.MULTILINE)


def handle_techcrunch(urls: List[str], path: str) -> None:
    news = []
    for url in urls:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        article_img_url = (
            soup.find("div", class_="article-hero__first-section").find("img").get_attribute_list("src")[0]
        )
        article_title = soup.find("h1", class_="article-hero__title").get_text(strip=True)
        article_title = _translate_and_clean(article_title)

        main_content = soup.find("div", class_="entry-content")
        elements = main_content.find_all(["p", "figure"])
        content = []

        for el in elements:
            if el.name == "p":
                text = el.get_text(strip=True)
                if text:
                    translated = _translate_and_clean(f"en: {text}")
                    content.append(translated)

        tags = [tag.get_text() for tag in soup.find_all("a", {"rel": "tag"})]
        tags = [_translate_and_clean(tag) for tag in tags]

        content.append(f"\n\n **Nguồn:** [Techcrunch]({url})")

        news.append(
            {
                "img": article_img_url,
                "title": article_title,
                "contents": content,
                "tags": tags,
            }
        )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)


def handle_fintechnews(urls: List[str], path: str) -> None:
    news = []
    for url in urls:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.find("h1", class_="post-title").get_text(strip=True)
        title = _translate_and_clean(f"en: {title}")

        subtitle = soup.find("div", class_="sub-title").get_text(strip=True)
        subtitle = re.sub(r"^vi:\s*", "", subtitle, flags=re.MULTILINE)

        author = soup.find("a", {"rel": "author"}).get_text(strip=True)
        main_img = (
            soup.find("div", class_="single-featured").find("div", class_="featured").find("img").get_attribute_list("src")[0]
        )

        content = soup.find("div", class_="post-content cf entry-content content-spacious")
        elements = content.find_all(["p", "figure", "blockquote"], recursive=False)
        contents = [author + "\n\n", subtitle]

        for el in elements:
            if el.name == "p":
                text = el.get_text()
                if text:
                    translated = _translate_and_clean(f"en: {text}")
                    contents.append(translated)
            elif el.name == "figure":
                img = el.find("img").get_attribute_list("src")[0]
                alt = el.find("img").get_attribute_list("alt")[0]
                contents.append(f"![{alt}]({img})")
            elif el.name == "blockquote":
                quotes = [
                    _translate_and_clean(f"en: {p.get_text(strip=True)}") for p in el.find_all("p")
                ]
                for quote in quotes:
                    contents.append(f"*{quote}*")

        tags = [tag.get_text() for tag in soup.find_all("a", {"rel": "tag"})]

        contents.append(f"\n\n **Nguồn:** [Fintechnews]({url})")

        news.append(
            {
                "article_title": title,
                "slug": gen_slug(title),
                "article_img_url": main_img,
                "article_img_alt": title,
                "contents": contents,
                "category": "Coin",
                "topics": tags,
            }
        )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)


def handle_glossy(urls: List[str], path: str) -> None:
    news = []
    for url in urls:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.find("h1", class_="title").get_text(strip=True)
        title = _translate_and_clean(f"en: {title}")

        author = soup.find("div", class_="author").find("a").get_text(strip=True)
        main_img = soup.find("div", class_="img-wrapper").find("img").get_attribute_list("src")[0]

        content = soup.find("div", class_="content-block")
        elements = content.find_all("p")
        contents = [author + "\n"]

        for el in elements:
            if el.name == "p":
                text = el.get_text()
                if text:
                    translated = _translate_and_clean(f"en: {text}")
                    contents.append(translated)

        contents.append(f"\n\n **Nguồn:** [Glossy]({url})")

        tags = [tag.get_text(strip=True) for tag in soup.find_all("div", class_="eyebrow")]

        news.append(
            {
                "article_title": title,
                "slug": gen_slug(title),
                "article_img_url": main_img,
                "article_img_alt": title,
                "contents": contents,
                "category": "Beauty",
                "topics": tags,
            }
        )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)


def handle_robbreport(urls: List[str], path: str) -> None:
    news = []
    for url in urls:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        )
        driver = None
        try:
            driver = webdriver.Chrome(service=Service(), options=chrome_options)
            driver.get(url)
            time.sleep(5)

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            title = (
                soup.find("header", class_="post-header")
                .find("h1", class_="post-header__title")
                .get_text(strip=True)
            )
            title = _translate_and_clean(f"en: {title}")
            subtitle = (
                soup.find("header", class_="post-header")
                .find("h2", class_="post-header__dek")
                .get_text(strip=True)
            )
            author = (
                soup.find("div", class_="article-wrapper")
                .find("span", {"aria-label": "Author"})
                .find("span")
                .get_text(strip=True)
            )
            img_el = soup.find("div", class_="post__featured-image").find("img")
            img_alt = img_el.get_attribute_list("alt")[0]
            img_url = img_el.get_attribute_list("src")[0]
            contents = [f"_By {author}_\n", f"## {subtitle}\n\n"]

            for p in [p.get_text(strip=True) for p in soup.find("div", class_="post-content").find_all("p")]:
                contents.append(_translate_and_clean(f"en: {p}"))
            
            contents.append(f"\n\n **Nguồn:** [Robbreport]({url})")

            news.append(
                {
                    "article_title": title,
                    "slug": gen_slug(title),
                    "article_img_url": img_url,
                    "article_img_alt": img_alt,
                    "contents": contents,
                    "category": "Lifestyle",
                    "topics": ["Lifestyle"],
                    "source": url,
                }
            )
        except Exception:
            print("[INFO] Error happened!")
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass

    with open(path, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)


def handle_(urls: List[str], path:str) -> None:
    pass

__all__ = [
    "gen_slug",
    "json_to_markdown",
    "handle_techcrunch",
    "handle_fintechnews",
    "handle_glossy",
    "handle_robbreport",
]
