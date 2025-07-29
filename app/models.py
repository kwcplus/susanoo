"""Model."""

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings."""

    susanoo_url: str

    vonage_application_id: str
    vonage_private_key: str
    vonage_number: str

    dynamodb_table_name: str
    dynamodb_host: str | None = None
    dynamodb_region: str


class CallParams(BaseModel):
    """CallParams."""

    to: str = Field(
        default=...,
        max_length=120,
        description="カンマ区切りの電話番号 Ex. 090-XXXX-YYYY,8180XXXXYYYY",
    )
    text: str = Field(default=..., max_length=660, description="メッセージ本文")
    loop: int = Field(default=3, ge=1, le=10, description="繰り返し回数")
    round_robin: bool = Field(
        default=True,
        description="true: ランダムな順番で架電(ラウンドロビン), false: 順番に架電",
    )
