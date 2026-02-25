from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LinkedInSettings(BaseSettings):
    """Configuration values required by the LinkedIn agent."""

    li_client_id: str = ""
    li_client_secret: str = ""
    li_redirect_uri: str = "http://localhost:8000/agents/linkedin/callback"
    li_scopes: list[str] = Field(
        default_factory=lambda: ["openid", "profile", "email", "w_member_social"]
    )
    li_api_posts: str = "https://api.linkedin.com/rest/posts"
    li_api_userinfo: str = "https://www.linkedin.com/oauth/v2/userinfo"
    li_oauth_authorize: str = "https://www.linkedin.com/oauth/v2/authorization"
    li_oauth_token: str = "https://www.linkedin.com/oauth/v2/accessToken"
    li_db_path: str = "linkedin_agent.db"
    li_daily_post_limit: int = 50

    model_config = SettingsConfigDict(
        env_prefix="LI_",
        env_file=".env",
        case_sensitive=False,
    )


linkedin_settings = LinkedInSettings()
