from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Supabase — handles both relational data and pgvector memory
    supabase_url: str
    supabase_service_role_key: str

    # Communication
    sendgrid_api_key: str
    sendgrid_from_email: str = "recruit@hiremind.ai"

    # Google Calendar
    google_calendar_credentials_path: str = "config/google_credentials.json"
    google_calendar_id: str = "primary"

    # LinkedIn (leave blank to skip outreach)
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_access_token: str = ""

    # App
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
