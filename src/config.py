from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
from pydantic_settings import BaseSettings, SettingsConfigDict  # pyright: ignore[reportMissingImports]

load_dotenv()

class Settings(BaseSettings):
    # Binance API credentials
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    
    # Trading parameters
    FUTURES_TESTNET: bool = True  # Start with testnet!
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Convert FUTURES_TESTNET string to bool if needed
        if isinstance(self.FUTURES_TESTNET, str):
            self.FUTURES_TESTNET = self.FUTURES_TESTNET.lower() in ("true", "1", "yes", "on")

settings = Settings()   