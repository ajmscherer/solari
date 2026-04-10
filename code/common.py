
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = BASE_DIR / "resources"
PROMPT_DIR = RESOURCES_DIR / "prompts"
CACHE_DIR = BASE_DIR / "cache"