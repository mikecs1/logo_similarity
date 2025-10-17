from pathlib import Path


class Config:
    """Configuration settings for logo extraction and clustering."""

    # Network settings
    TIMEOUT = 8                 # per-request total timeout (seconds)
    MAX_RETRIES = 1             
    RETRY_DELAY = 0.5           
    BATCH_SIZE = 100            #
    MAX_CONCURRENT = 20        
    HASH_CHUNK_SIZE = 200

    # Hamming distance
    EXACT_MATCH_THRESHOLD = 0
    NEAR_DUPLICATE_THRESHOLD = 5
    SIMILAR_THRESHOLD = 10

    NORMALIZE_SIZE = 64
    MIN_IMAGE_SIZE = 16

    OUTPUT_DIR = "output"
    DATA_DIR = "data"
    CACHE_DIR = "data/cache"
    LOGO_DIR = "data/logos"
    LOG_DIR = "logs"

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36",
    ]

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        for p in [self.OUTPUT_DIR, self.DATA_DIR, self.CACHE_DIR, self.LOGO_DIR, self.LOG_DIR]:
            Path(p).mkdir(parents=True, exist_ok=True)
