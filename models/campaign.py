from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Campaign:
    card_name: str
    title: str
    campaign_url: str
    summary: Optional[str] = None
    max_amount: Optional[str] = None
    period: Optional[str] = None
    conditions: Optional[str] = None
    thumbnail_url: Optional[str] = None
    registration_url: Optional[str] = None
    # AI分析結果
    eligible: Optional[bool] = None         # 既存Oliveユーザーが参加可能か
    eligibility_reason: Optional[str] = None # 参加可否の理由
    ai_summary: Optional[str] = None         # AI生成の達成条件サマリー
    notified: bool = False
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # スクレイピング時のみ使用（DBには保存しない）
    page_text: Optional[str] = field(default=None, repr=False)
