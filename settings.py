"""
Minimal, explicit settings: simple variable declarations.
Strings are empty by default except `data_location` which defaults to "/data".
"""

# Paths
data_location = "/data"

archive = False

# Enable dynamic media extraction using headless browser (requires Playwright)
dynamic_media_extraction = True

default_timeout = 10  # Default timeout in seconds for network requests

parallel_connections = 10

user_agent = ""

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
openrouter_enabled = False
openrouter_api_key = ""
openrouter_model = ""
 # Exemples de modèles compatibles OpenRouter (mini/éco)
 # Renseignez `openrouter_model` avec l'un de ces slugs si vous activez la passerelle
openrouter_model_examples = [
    # OpenAI
    "openai/gpt-4o-mini",
    # Anthropic
    "anthropic/claude-3-haiku",
    # Google
    "google/gemini-1.5-flash",
    # Meta (Llama 3.x Instruct – 8B)
    "meta-llama/llama-3.1-8b-instruct",
    # Mistral
    "mistralai/mistral-small-latest",
    # Qwen (Alibaba)
    "qwen/qwen2.5-7b-instruct",
    # Cohere
    "cohere/command-r-mini",
]
openrouter_timeout = 15  # seconds
# Bounds to control costs/latency
openrouter_readable_max_chars = 12000
openrouter_max_calls_per_run = 500
