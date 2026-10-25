from pathlib import Path

DATASET_COMMIT = "85f70fb891f2471eda8a7a773479106b0d3bf88f"
DATASET_URL = (
    f"https://raw.githubusercontent.com/Allan-Cao/lol-voice-lines/{DATASET_COMMIT}/voice_lines.csv"
)
DATASET_SHA256 = "a183f3a540bdee0299bdf58b732520a8f0acfc3baee10654c658048708a230b8"
EXPECTED_ROWS = 32_392
EXPECTED_CHAMPIONS = 163
EXPECTED_SPOKEN = 31_240
EXPECTED_ACTIONS = 1_152
COLLECTION_NAME = "voice_lines_v1"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DATA_DIR = Path(".data")
CACHE_DIR = Path(".cache")
