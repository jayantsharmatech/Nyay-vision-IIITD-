from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_secret_arn: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_fallback_models: str = "gpt-4.1"
    database_path: str = "data/nyay_vision.db"
    dynamodb_table: str = ""
    dynamodb_jobs_table: str = ""
    aws_region: str = ""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
if not settings.openai_api_key and settings.openai_secret_arn:
    import boto3
    settings.openai_api_key = boto3.client("secretsmanager").get_secret_value(
        SecretId=settings.openai_secret_arn
    )["SecretString"]
