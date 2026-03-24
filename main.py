import logging
import sys
from dotenv import load_dotenv

load_dotenv()

from db.database import init_db, save_campaign, get_unnotified_campaigns, mark_as_notified, update_analysis
from scraper.olive_gold import scrape
from notifier.line_notify import send_campaigns
from analyzer.campaign_analyzer import analyze

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("=== Credit Card Campaign Tracker 開始 ===")

    # 1. DB初期化
    init_db()

    # 2. スクレイピング
    campaigns = scrape()
    if not campaigns:
        logger.warning("キャンペーンが取得できませんでした。終了します。")
        return

    # 3. DBに保存（page_textはURLでマップしておく）
    page_text_map = {c.campaign_url: c.page_text for c in campaigns}
    for campaign in campaigns:
        save_campaign(campaign)

    # 4. 未通知キャンペーンを取得
    unnotified = get_unnotified_campaigns()
    logger.info("未通知キャンペーン数: %d", len(unnotified))

    if not unnotified:
        logger.info("通知対象なし。終了します。")
        return

    # 5. AI分析（未分析のキャンペーンのみ）
    for campaign in unnotified:
        if campaign.eligible is None:
            campaign.page_text = page_text_map.get(campaign.campaign_url)
            analysis = analyze(campaign)
            campaign.eligible = analysis.eligible
            campaign.eligibility_reason = analysis.eligibility_reason
            campaign.ai_summary = analysis.conditions_summary
            if campaign.id is not None:
                update_analysis(campaign.id, analysis.eligible, analysis.eligibility_reason, analysis.conditions_summary)

    # 6. 参加可能なキャンペーンのみ通知
    eligible = [c for c in unnotified if c.eligible]
    skipped = [c for c in unnotified if not c.eligible]

    logger.info("参加可能: %d件 / 対象外: %d件", len(eligible), len(skipped))
    for c in skipped:
        logger.info("  スキップ: %s (%s)", c.title[:40], c.eligibility_reason)

    if eligible:
        send_campaigns(eligible)

    # 7. 通知済みフラグを更新（eligible・非eligible問わず全件）
    for campaign in unnotified:
        if campaign.id is not None:
            mark_as_notified(campaign.id)

    logger.info("=== 処理完了 ===")


if __name__ == "__main__":
    main()
