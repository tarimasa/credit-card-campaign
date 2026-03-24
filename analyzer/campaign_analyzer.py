import logging
from pydantic import BaseModel
import anthropic
from models.campaign import Campaign

logger = logging.getLogger(__name__)

client = anthropic.Anthropic()


class CampaignAnalysis(BaseModel):
    eligible: bool
    eligibility_reason: str
    conditions_summary: str


SYSTEM_PROMPT = """あなたは三井住友銀行のOliveアカウント保有者のキャンペーン判定AIです。
ユーザーはすでにOliveアカウント（OliveゴールドO）を持っている既存ユーザーです。

キャンペーンページの内容を分析し、以下のJSON形式で回答してください。

■ eligible（参加可否）
- 新規口座開設・新規入会・初めてのOlive申込が「必須条件」 → false
- 既存ユーザーも参加できる（入金・決済・エントリーなど行動すれば参加可能）→ true
- 「新規・既存問わず」「どなたでも」などの記述があれば → true

■ eligibility_reason
参加できる/できない理由を1文で端的に

■ conditions_summary
具体的に何をすればいくらもらえるかを2〜3文で明記すること。以下を必ず含める：
- エントリーが必要かどうか
- 達成すべき行動（入金額・回数・サービス利用など具体的な数字）
- 獲得できる特典（金額・ポイント数など）
- 期限（記載がある場合）

抽象的な説明（「キャンペーンに参加してポイントを獲得しよう」など）は禁止。
数字・条件・期限を盛り込んだ具体的なサマリーにすること。"""


def analyze(campaign: Campaign) -> CampaignAnalysis:
    page_text = campaign.page_text or campaign.summary or ""
    # 長すぎる場合は先頭8000文字に絞る
    page_text = page_text[:8000]

    try:
        response = client.messages.parse(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"キャンペーンタイトル: {campaign.title}\n\nページ内容:\n{page_text}",
            }],
            output_format=CampaignAnalysis,
        )
        result = response.parsed_output
        logger.info(
            "Analysis: '%s' eligible=%s | %s",
            campaign.title[:40], result.eligible, result.eligibility_reason
        )
        return result

    except Exception as e:
        logger.error("Analysis failed for '%s': %s", campaign.title, e)
        # エラー時は通知する（見逃しを防ぐ）
        return CampaignAnalysis(
            eligible=True,
            eligibility_reason="分析エラーのため通知",
            conditions_summary=campaign.summary or "詳細はキャンペーンページをご確認ください。",
        )
