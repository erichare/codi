"""Typed, environment-driven configuration for codi."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PersonalityName = Literal["codi", "wooloo"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Bot tokens (at least one must be set at runtime).
    codi_bot_token: SecretStr | None = None
    wooloo_bot_token: SecretStr | None = None

    # CODI personality
    crypto_api_base_url: str = "https://crypto-predictions-production-6b02.up.railway.app"
    codi_command_prefix: str = "!"

    # Wooloo personality
    pokemon_api_base_url: str = "https://pokeapi.co/api/v2"
    wooloo_command_prefix: str = "!"
    wooloo_default_mode: Literal["ai", "uplift"] = "uplift"

    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # HTTP client
    http_timeout_seconds: float = Field(default=20.0, ge=1.0, le=300.0)

    def configured_personalities(self) -> list[tuple[PersonalityName, SecretStr]]:
        """Return (personality, token) pairs that have a token set."""
        pairs: list[tuple[PersonalityName, SecretStr]] = []
        if self.codi_bot_token is not None and self.codi_bot_token.get_secret_value():
            pairs.append(("codi", self.codi_bot_token))
        if self.wooloo_bot_token is not None and self.wooloo_bot_token.get_secret_value():
            pairs.append(("wooloo", self.wooloo_bot_token))
        return pairs
