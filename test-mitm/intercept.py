from mitmproxy import http
import os

# Configuration
LOG_FILE = "traffic_log.txt"
BLOCK_DOMAINS = [
    "google-analytics",
    "doubleclick",
    "facebook.com",
    "googletagmanager",
    "bing.com",
    "adservice"
]

def response(flow: http.HTTPFlow) -> None:
    url = flow.request.pretty_url
    
    # Filtering Logic:
    # 1. Ignore commonly blocked domains
    if any(domain in url for domain in BLOCK_DOMAINS):
        return

    # 2. Ignore any response that is NOT text or JSON
    content_type = flow.response.headers.get("Content-Type", "")
    if not ("text" in content_type or "json" in content_type):
        return

    # Action:
    # Append the URL and the first 500 characters of the response content to a local file
    content_snippet = flow.response.get_text()[:500] if flow.response.content else "[No Content]"
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"--- INTERCEPTED: {url} ---\n")
        f.write(f"{content_snippet}\n\n")

    # Print a distinct message to the console
    print(f"[INTERCEPTED]: {url}")
