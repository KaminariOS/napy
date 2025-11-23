"""Configuration models for napy."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TelegramConfig(BaseModel):
    """Telegram bot configuration."""
    api_key: str | None = Field(default=None, description="Telegram bot API key")
    chat_id: str | None = Field(default=None, description="Telegram chat ID to send messages to")


class EmailConfig(BaseModel):
    """Email notification configuration."""
    smtp_host: str | None = Field(default=None, description="SMTP host")
    smtp_port: int | None = Field(default=None, description="SMTP port")
    smtp_user: str | None = Field(default=None, description="SMTP user")
    smtp_pass: str | None = Field(default=None, description="SMTP password / secret")
    sender: str | None = Field(default=None, description="From address")
    recipient: str | None = Field(default=None, description="To address")


class AppConfig(BaseModel):
    """Main application configuration."""
    username: str = Field(
        default="world",
        description="Name used in greetings and other user-facing messages.",
    )
    retries: int = Field(default=3, ge=0, le=10, description="Number of retry attempts.")
    enable_notifications: bool = Field(default=False, description="Toggle notifications.")
    shell: str | None = Field(default=None, description="Shell to use for command execution")
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)

