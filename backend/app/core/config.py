import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} 必须是整数") from exc


def _get_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    """应用配置（从环境变量读取）。"""

    APP_NAME: str = os.getenv("APP_NAME", "Outbound-Guard API")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = _get_bool("DEBUG", True)
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = _get_int("PORT", 8000)

    CORS_ORIGINS: list[str] = _get_list(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    GLM_API_KEY: str = os.getenv("GLM_API_KEY", "")
    GLM_BASE_URL: str = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    GLM_MODEL: str = os.getenv("GLM_MODEL", "glm-4-flash")
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "").strip().lower()
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    MONITORING_ENABLED: bool = _get_bool("MONITORING_ENABLED", False)
    MONITORING_INTERVAL_SECONDS: int = _get_int("MONITORING_INTERVAL_SECONDS", 21600)
    PUBLIC_DATA_API_KEY: str = os.getenv("PUBLIC_DATA_API_KEY", "")

    IFLYTEK_API_PASSWORD: str = os.getenv("IFLYTEK_API_PASSWORD", "")
    IFLYTEK_BASE_URL: str = os.getenv("IFLYTEK_BASE_URL", "https://spark-api-open.xf-yun.com/x2")
    IFLYTEK_MODEL: str = os.getenv("IFLYTEK_MODEL", "spark-x")
    ASSISTANT_KNOWLEDGE_DIR: str = os.getenv("ASSISTANT_KNOWLEDGE_DIR", "data/assistant_knowledge")
    ASSISTANT_MAX_FILE_MB: int = _get_int("ASSISTANT_MAX_FILE_MB", 10)

    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    REPORT_DIR: str = os.getenv("REPORT_DIR", "reports")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    RULES_DIR: str = os.getenv("RULES_DIR", "rules")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/outbound_guard.sqlite3")
    SUPERADMIN_USERNAME: str = os.getenv("SUPERADMIN_USERNAME", "superadmin")
    SUPERADMIN_PASSWORD: str = os.getenv("SUPERADMIN_PASSWORD", "")

    AUDIT_TIMEOUT_SECONDS: int = _get_int("AUDIT_TIMEOUT_SECONDS", 60)
    MAX_IMAGE_SIZE_MB: int = _get_int("MAX_IMAGE_SIZE_MB", 5)

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.strip().lower() == "production"

    def validate(self) -> None:
        """启动时校验配置；开发环境允许在未配置模型时启动。"""

        errors: list[str] = []
        if not self.APP_NAME:
            errors.append("APP_NAME 未设置")
        if not self.APP_VERSION:
            errors.append("APP_VERSION 未设置")
        if not self.CORS_ORIGINS:
            errors.append("CORS_ORIGINS 至少需要配置一个来源")
        if self.PORT <= 0 or self.PORT > 65535:
            errors.append("PORT 必须在 1-65535 之间")
        if self.AUDIT_TIMEOUT_SECONDS <= 0:
            errors.append("AUDIT_TIMEOUT_SECONDS 必须大于 0")
        if self.MAX_IMAGE_SIZE_MB <= 0:
            errors.append("MAX_IMAGE_SIZE_MB 必须大于 0")
        if not self.SUPERADMIN_PASSWORD:
            errors.append("必须通过 SUPERADMIN_PASSWORD 配置超级管理员密码")
        if self.ASSISTANT_MAX_FILE_MB <= 0:
            errors.append("ASSISTANT_MAX_FILE_MB 必须大于 0")
        if self.MODEL_PROVIDER and self.MODEL_PROVIDER not in {"glm", "deepseek", "iflytek", "openai-compatible"}:
            errors.append("MODEL_PROVIDER 不是支持的模型提供方")
        if self.MODEL_PROVIDER and not self.model_api_key:
            errors.append("选定的模型提供方尚未配置 API Key")
        if self.MONITORING_INTERVAL_SECONDS < 3600:
            errors.append("MONITORING_INTERVAL_SECONDS 不能小于 3600 秒")

        required_dirs = {
            "UPLOAD_DIR": self.UPLOAD_DIR,
            "REPORT_DIR": self.REPORT_DIR,
            "DATA_DIR": self.DATA_DIR,
            "RULES_DIR": self.RULES_DIR,
        }
        for name, value in required_dirs.items():
            if not value:
                errors.append(f"{name} 未设置")

        if self.is_production and not self.model_api_key:
            errors.append("生产环境必须配置 GLM_API_KEY、DEEPSEEK_API_KEY、IFLYTEK_API_PASSWORD 或 LLM_API_KEY")

        if errors:
            raise RuntimeError("配置校验失败:\n" + "\n".join(f"  - {error}" for error in errors))

    def ensure_dirs(self) -> None:
        """确保存储目录存在。"""

        for directory in [
            self.UPLOAD_DIR,
            self.REPORT_DIR,
            self.DATA_DIR,
            self.RULES_DIR,
            self.ASSISTANT_KNOWLEDGE_DIR,
        ]:
            Path(directory).mkdir(parents=True, exist_ok=True)

    @property
    def database_path(self) -> Path:
        return Path(self.DATABASE_PATH)

    @property
    def iflytek_base_url(self) -> str:
        return self.IFLYTEK_BASE_URL.rstrip("/")

    @property
    def model_provider(self) -> str:
        if self.MODEL_PROVIDER:
            return self.MODEL_PROVIDER
        if self.GLM_API_KEY:
            return "glm"
        if self.IFLYTEK_API_PASSWORD:
            return "iflytek"
        if self.LLM_API_KEY:
            return "openai-compatible"
        if self.DEEPSEEK_API_KEY:
            return "deepseek"
        return "unconfigured"

    @property
    def model_api_key(self) -> str:
        return {"glm": self.GLM_API_KEY, "deepseek": self.DEEPSEEK_API_KEY, "iflytek": self.IFLYTEK_API_PASSWORD, "openai-compatible": self.LLM_API_KEY}.get(self.model_provider, "")

    @property
    def model_base_url(self) -> str:
        return {"glm": self.GLM_BASE_URL, "deepseek": self.DEEPSEEK_BASE_URL, "iflytek": self.IFLYTEK_BASE_URL, "openai-compatible": self.LLM_BASE_URL}.get(self.model_provider, self.LLM_BASE_URL).rstrip("/")

    @property
    def model_name(self) -> str:
        return {"glm": self.GLM_MODEL, "deepseek": self.DEEPSEEK_MODEL, "iflytek": self.IFLYTEK_MODEL, "openai-compatible": self.LLM_MODEL}.get(self.model_provider, self.LLM_MODEL)

    def model_config(self, provider: str) -> tuple[str, str, str]:
        configurations = {
            "glm": (self.GLM_API_KEY, self.GLM_BASE_URL, self.GLM_MODEL),
            "deepseek": (self.DEEPSEEK_API_KEY, self.DEEPSEEK_BASE_URL, self.DEEPSEEK_MODEL),
            "iflytek": (self.IFLYTEK_API_PASSWORD, self.IFLYTEK_BASE_URL, self.IFLYTEK_MODEL),
            "openai-compatible": (self.LLM_API_KEY, self.LLM_BASE_URL, self.LLM_MODEL),
        }
        return configurations.get(provider, ("", "", ""))

    @property
    def public_data_providers(self) -> list[str]:
        providers = ["deepseek", "glm"] if self.DEEPSEEK_API_KEY else [self.model_provider]
        return [provider for provider in providers if self.model_config(provider)[0]]


settings = Settings()
