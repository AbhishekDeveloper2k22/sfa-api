from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API configurations
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FastAPI Project"
    
    # CORS configurations
    CORS_ORIGINS: list = [
        "http://localhost.tiangolo.com",
        "https://qt.cyberads.io",
        "https://localhost.tiangolo.com",
        "http://localhost",
        "http://localhost:3000",
    ]
    
    # Logging configurations
    LOG_LEVEL: str = "INFO"

    # Database 1 configurations
    DB1_USERNAME: str
    DB1_PASSWORD: str
    DB1_HOST: str
    DB1_AUTH_SOURCE: str
    DB1_NAME: str

    # JWT configurations
    JWT_SECRET: str
    
    # AI/ML configurations
    GEMINI_API_KEY: str
    MODEL_PROVIDER: str = "hf"  # Model provider: gemini, hf (HuggingFace), local
    HUGGINGFACE_API_KEY: str = ""  # HuggingFace API key (required if MODEL_PROVIDER=hf)
    HUGGINGFACE_MODEL: str = ""  # HuggingFace model name

    DEEPSEEK_API_KEY: str

    # Domain configuration
    DOMAIN: str

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 