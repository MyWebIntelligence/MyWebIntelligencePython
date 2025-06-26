data_location = "data/"

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
