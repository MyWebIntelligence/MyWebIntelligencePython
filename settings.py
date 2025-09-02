import os

# Allow overriding data location via env var for local/dev flows
# Defaults to "/data" (Docker convention). Set MWI_DATA_LOCATION to use a custom path.
data_location = os.environ.get("MWI_DATA_LOCATION", "/data")

archive = False

# Enable dynamic media extraction using headless browser (requires Playwright)
dynamic_media_extraction = True

default_timeout = 10 # Default timeout in seconds for network requests

parallel_connections = 10

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"

heuristics = {
    "facebook.com": r"([a-z0-9\-_]+\.facebook\.com/(?!(?:permalink.php)|(?:notes))[a-zA-Z0-9\.\-_]+)/?\??",
    "twitter.com": r"([a-z0-9\-_]*\.?twitter\.com/(?!(?:hashtag)|(?:search)|(?:home)|(?:share))[a-zA-Z0-9\.\-_]+)",
    "linkedin.com": r"([a-z0-9\-_]+\.linkedin\.com/[a-zA-Z0-9\.\-_]+)/?\??",
    "slideshare.net": r"([a-z0-9\-_]+\.slideshare\.com/[a-zA-Z0-9\.\-_]+)/?\??",
    "instagram.com": r"([a-z0-9\-_]+\.instagram\.com/[a-zA-Z0-9\.\-_]+)/?\??",
    "youtube.com": r"([a-z0-9\-_]+\.youtube\.com/(?!watch)[a-zA-Z0-9\.\-_]+)/?\??",
    "vimeo.com": r"([a-z0-9\-_]+\.vimeo\.com/[a-zA-Z0-9\.\-_]+)/?\??",
    "dailymotion.com": r"([a-z0-9\-_]+\.dailymotion\.com/(?!video)[a-zA-Z0-9\.\-_]+)/?\??",
    "pinterest.com": r"([a-z0-9\-_]+\.pinterest\.com/(?!pin)[a-zA-Z0-9\.\-_]+)/?\??",
    "pinterest.fr": r"([a-z0-9\-_]+\.pinterest\.fr/[a-zA-Z0-9\.\-_]+)/?\??",
}

# Media Analysis Settings
media_analysis = True
media_min_width = 200
media_min_height = 200
media_max_file_size = 10 * 1024 * 1024  # 10MB
media_download_timeout = 30
media_max_retries = 2
media_analyze_content = False
media_extract_colors = True
media_extract_exif = True
media_n_dominant_colors = 5

# OpenRouter relevance gate (disabled by default)
# These can be overridden via environment variables for safe deployments.
openrouter_enabled = os.environ.get("MWI_OPENROUTER_ENABLED", "false").lower() in ("1", "true", "yes")
openrouter_api_key = os.environ.get("MWI_OPENROUTER_API_KEY", None)
openrouter_model = os.environ.get("MWI_OPENROUTER_MODEL", None)
openrouter_timeout = int(os.environ.get("MWI_OPENROUTER_TIMEOUT", "15"))  # seconds
# Bounds to control costs/latency
openrouter_readable_max_chars = int(os.environ.get("MWI_OPENROUTER_READABLE_MAX_CHARS", "12000"))
openrouter_max_calls_per_run = int(os.environ.get("MWI_OPENROUTER_MAX_CALLS_PER_RUN", "500"))
