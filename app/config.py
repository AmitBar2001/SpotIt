from pydantic import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"  # default to development
    log_level: str = "INFO"  # default log level
    oci_config_path: str = "app/.oci/config"  # default OCI config path
    storage_namespace: str = "frjafxpufafn"
    storage_bucket_name: str = "mp3files"
    yt_dlp_proxy: str | None = None  # default no proxy
    yt_dlp_cookies_file_path: str = (
        "yt_dlp_cookies.txt"  # default cookies file path at project root directory
    )
    spotify_client_id: str
    spotify_client_secret: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
