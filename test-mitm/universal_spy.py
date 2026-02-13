from mitmproxy import http, websocket
from datetime import datetime
import json
import logging

# Configuration
LOG_FILE = "traffic_log.jsonl"

# Set mitmproxy's own logging to ERROR only to keep the console clean
logging.getLogger("mitmproxy").setLevel(logging.ERROR)

print("\n" + "="*50)
print("🚀 UNIVERSAL SPY IS RUNNING")
print("Logging organized traffic to console and file...")
print("="*50 + "\n")

# Helper: Log to file as JSON Line
def log_to_file(data_dict):
    data_dict["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(data_dict) + "\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")

# Helper: Check if content is text-based
def is_text_content(headers):
    content_type = headers.get("Content-Type", "").lower()
    return any(t in content_type for t in ["text", "json", "xml", "javascript", "urlencoded"])

# Helper: Pretty print content (JSON or Text)
def format_content(content):
    try:
        # Try to parse and pretty-print JSON
        json_obj = json.loads(content)
        return json.dumps(json_obj, indent=2)
    except:
        # Return raw text if not JSON
        return content

# ----------------------------------------------------------------------
# HTTP HANDLERS
# ----------------------------------------------------------------------
def request(flow: http.HTTPFlow):
    if not is_text_content(flow.request.headers) or not flow.request.content:
        return

    try:
        content = flow.request.text
        if not content: return

        pretty_body = format_content(content)
        
        # Console Output
        print(f"\n{'='*20} [>>> OUTGOING REQUEST] {'='*20}")
        print(f"URL: {flow.request.method} {flow.request.pretty_url}")
        print(f"Type: {flow.request.headers.get('Content-Type', 'unknown')}")
        print("-" * 60)
        print(f"{pretty_body[:2000]}") # Show more chars but truncate nicely
        if len(pretty_body) > 2000: print(f"\n... [Truncated {len(pretty_body)-2000} chars]")
        print("="*60)

        # File Log
        log_to_file({
            "type": "HTTP_REQ",
            "method": flow.request.method,
            "url": flow.request.pretty_url,
            "content_type": flow.request.headers.get('Content-Type', 'unknown'),
            "body": pretty_body
        })

    except:
        pass

def response(flow: http.HTTPFlow):
    if not is_text_content(flow.response.headers) or not flow.response.content:
        return

    try:
        content = flow.response.text
        if not content: return

        pretty_body = format_content(content)
        
        # Console Output
        print(f"\n{'='*20} [<<< INCOMING RESPONSE] {'='*20}")
        print(f"URL: {flow.response.status_code} {flow.request.pretty_url}")
        print(f"Type: {flow.response.headers.get('Content-Type', 'unknown')}")
        print("-" * 60)
        print(f"{pretty_body[:2000]}")
        if len(pretty_body) > 2000: print(f"\n... [Truncated {len(pretty_body)-2000} chars]")
        print("="*60)

        # File Log
        log_to_file({
            "type": "HTTP_RES",
            "status": flow.response.status_code,
            "url": flow.request.pretty_url,
            "content_type": flow.response.headers.get('Content-Type', 'unknown'),
            "body": pretty_body
        })
        
    except:
        pass

# ----------------------------------------------------------------------
# WEBSOCKET HANDLER
# ----------------------------------------------------------------------
def websocket_message(flow: http.HTTPFlow):
    try:
        message = flow.websocket.messages[-1]
        content = message.content
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        pretty_body = format_content(content)
        direction = "WS_OUT" if message.from_client else "WS_IN" # Machine readable code
        display_dir = ">> WS SENT" if message.from_client else "<< WS RECV"
        
        # Console Output
        print(f"\n[{display_dir}] {flow.request.pretty_host}")
        print(f"{pretty_body[:1000]}")
        if len(pretty_body) > 1000: print("...")

        # File Log
        log_to_file({
            "type": direction,
            "url": flow.request.pretty_url,
            "body": pretty_body
        })
            
    except:
        pass
