import logging
import os
import requests
from models.campaign import Campaign

logger = logging.getLogger(__name__)

LINE_API_URL = "https://api.line.me/v2/bot/message/push"


def send_campaigns(campaigns: list[Campaign]) -> None:
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")

    if not token or not user_id:
        logger.error("LINE_CHANNEL_ACCESS_TOKEN or LINE_USER_ID is not set.")
        return

    for campaign in campaigns:
        try:
            _send_flex_message(token, user_id, campaign)
            logger.info("LINE notification sent: %s", campaign.title)
        except Exception as e:
            logger.error("Failed to send LINE notification for '%s': %s", campaign.title, e)


def _send_flex_message(token: str, user_id: str, campaign: Campaign) -> None:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    body = {
        "to": user_id,
        "messages": [
            {
                "type": "flex",
                "altText": f"新しいキャンペーン: {campaign.title}",
                "contents": _build_bubble(campaign),
            }
        ],
    }

    response = requests.post(LINE_API_URL, headers=headers, json=body, timeout=10)
    response.raise_for_status()


def _build_bubble(campaign: Campaign) -> dict:
    bubble: dict = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "action": {
                        "type": "uri",
                        "label": "キャンペーンに登録",
                        "uri": campaign.campaign_url,
                    },
                }
            ],
        },
    }

    contents = bubble["body"]["contents"]

    if campaign.thumbnail_url:
        bubble["hero"] = {
            "type": "image",
            "url": campaign.thumbnail_url,
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover",
        }

    contents.append({
        "type": "text",
        "text": campaign.title,
        "weight": "bold",
        "size": "md",
        "wrap": True,
    })

    if campaign.period:
        contents.append(_info_row("期間", campaign.period))

    if campaign.max_amount:
        contents.append(_info_row("上限", campaign.max_amount))

    # 達成条件サマリー（AI生成を優先、なければmeta descriptionにフォールバック）
    body_text = campaign.ai_summary or campaign.summary
    if body_text:
        contents.append({
            "type": "text",
            "text": body_text,
            "size": "sm",
            "color": "#333333",
            "wrap": True,
            "margin": "md",
        })

    return bubble


def _info_row(label: str, value: str) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "margin": "sm",
        "contents": [
            {"type": "text", "text": label, "size": "sm", "color": "#888888", "flex": 2},
            {"type": "text", "text": value, "size": "sm", "wrap": True, "flex": 5},
        ],
    }
