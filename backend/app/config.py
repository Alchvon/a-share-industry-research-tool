from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("STOCK_CHAIN_DATA_DIR", BASE_DIR / "data"))
DB_PATH = Path(os.getenv("STOCK_CHAIN_DB_PATH", DATA_DIR / "stock_chain.db"))

DEFAULT_PROVIDER_TIMEOUT_SECONDS = float(os.getenv("STOCK_CHAIN_PROVIDER_TIMEOUT", "8"))
CACHE_TTL_SECONDS = int(os.getenv("STOCK_CHAIN_CACHE_TTL_SECONDS", "3600"))


TUSHARE_TOKEN = os.getenv("STOCK_CHAIN_TUSHARE_TOKEN", "")


# Optional machine-local default AI provider. Never put the key in source control.
DEFAULT_LLM_ENDPOINT = os.getenv("STOCK_CHAIN_DEFAULT_LLM_ENDPOINT", "https://api.siliconflow.cn/v1")
DEFAULT_LLM_API_KEY = os.getenv("STOCK_CHAIN_DEFAULT_LLM_API_KEY", "")
DEFAULT_LLM_MODEL = os.getenv("STOCK_CHAIN_DEFAULT_LLM_MODEL", "deepseek-ai/DeepSeek-V3")
