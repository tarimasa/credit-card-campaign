import logging
import time
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from models.campaign import Campaign

logger = logging.getLogger(__name__)

CAMPAIGN_LIST_URL = "https://www.smbc.co.jp/kojin/campaign/"
CAMPAIGN_PATH_PREFIX = "/kojin/olive/special/campaign/"
BASE_URL = "https://www.smbc.co.jp"
CARD_NAME = "OliveゴールドO"
REQUEST_INTERVAL = 5  # seconds — サーバー負荷軽減のため5秒待機

# CTAボタンのテキストパターン（優先順位順）
CTA_TEXT_PATTERNS = ["申込", "はじめる", "エントリー", "登録", "開設"]


def scrape() -> list[Campaign]:
    campaigns = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            logger.info("Navigating to campaign list: %s", CAMPAIGN_LIST_URL)
            page.goto(CAMPAIGN_LIST_URL, wait_until="networkidle", timeout=30000)

            # キャンペーンURLを収集（重複・UTMパラメータ除去）
            links = page.query_selector_all(f"a[href*='{CAMPAIGN_PATH_PREFIX}']")
            campaign_urls = []
            seen = set()
            for link in links:
                href = link.get_attribute("href")
                if not href:
                    continue
                if href.startswith("/"):
                    href = BASE_URL + href
                href = _clean_url(href)
                if href not in seen:
                    seen.add(href)
                    campaign_urls.append(href)

            logger.info("Found %d campaign links", len(campaign_urls))

            for url in campaign_urls:
                time.sleep(REQUEST_INTERVAL)
                try:
                    campaign = _scrape_campaign_page(page, url)
                    if campaign:
                        campaigns.append(campaign)
                except Exception as e:
                    logger.error("Failed to scrape campaign page %s: %s", url, e)
                    continue

            context.close()
            browser.close()

    except PlaywrightTimeoutError:
        logger.error("Timeout while loading page. Exiting.")
    except Exception as e:
        logger.error("Unexpected error during scraping: %s", e)

    logger.info("Scraped %d campaigns", len(campaigns))
    return campaigns


def _scrape_campaign_page(page, url: str) -> Campaign | None:
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)

        # タイトル： <title> タグから " ： 三井住友銀行" を除去
        title = page.title().replace(" ： 三井住友銀行", "").strip()

        # 概要： meta description
        meta_desc = page.query_selector("meta[name='description']")
        summary = meta_desc.get_attribute("content").strip() if meta_desc else None

        # サムネイル： OGP画像
        og_image = page.query_selector("meta[property='og:image']")
        thumbnail_url = og_image.get_attribute("content") if og_image else None

        # 登録URL： CTAボタンのリンク先を抽出
        registration_url = _extract_registration_url(page, url)

        # ページ本文テキスト（AI分析用、DBには保存しない）
        main_el = page.query_selector("main") or page.query_selector("article") or page.query_selector("body")
        page_text = main_el.inner_text().strip() if main_el else ""

        if not title:
            logger.debug("Skipping page with no title: %s", url)
            return None

        return Campaign(
            card_name=CARD_NAME,
            title=title,
            campaign_url=url,
            summary=summary,
            thumbnail_url=thumbnail_url,
            registration_url=registration_url,
            page_text=page_text,
        )

    except Exception as e:
        logger.error("Error scraping campaign page %s: %s", url, e)
        return None


def _extract_registration_url(page, fallback_url: str) -> str:
    """CTAボタンのリンクを抽出する。見つからない場合はキャンペーンURLを返す。"""
    all_links = page.query_selector_all("a[href]")
    for link in all_links:
        href = link.get_attribute("href") or ""
        text = link.inner_text().strip()
        if not href or href.startswith("#"):
            continue
        if any(pattern in text for pattern in CTA_TEXT_PATTERNS):
            if href.startswith("/"):
                href = BASE_URL + href
            return _clean_url(href)
    return fallback_url


def _clean_url(url: str) -> str:
    """UTMパラメータ・affiliateパラメータを除去"""
    parsed = urlparse(url)
    params = {
        k: v for k, v in parse_qs(parsed.query).items()
        if not k.startswith("utm_") and k != "aff"
    }
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
