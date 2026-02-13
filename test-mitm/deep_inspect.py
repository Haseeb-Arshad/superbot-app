from mitmproxy import http, websocket
import json
import logging

# Set mitmproxy's own logging to ERROR only to keep the console clean
# logging.getLogger("mitmproxy").setLevel(logging.ERROR)

print("\n" + "="*50)
print("🚀 DEBUG MODE: DEEP INSPECTOR IS RUNNING")
print("I will show EVERY site you visit to check connectivity.")
print("Listening for traffic on http://127.0.0.1:8080")
print("Targeting: chatgpt.com, openai.com, claude.ai, google.com, example.com")
print("="*50 + "\n")

TARGETS = ["chatgpt.com", "openai.com", "claude.ai", "google.com", "example.com"]

def is_target(flow):
    return any(t in flow.request.pretty_host for t in TARGETS)

def extract_text(data):
    """Recursively search for text-like content in a JSON object."""
    if isinstance(data, str):
        if len(data) > 2 and not data.startswith("{"):
            return data
    elif isinstance(data, dict):
        for k, v in data.items():
            # Common fields in AI chat APIs
            if k in ["content", "parts", "text", "body", "input", "query", "prompt", "message"]:
                res = extract_text(v)
                if res: return res
            else:
                res = extract_text(v)
                if res: return res
    elif isinstance(data, list):
        for item in data:
            res = extract_text(item)
            if res: return res
    return None

def request(flow: http.HTTPFlow):
    # DEBUG: Show everything briefly to confirm the proxy is receiving data
    print(f"[CONNECTING]: {flow.request.pretty_url[:70]}...")

    if not is_target(flow):
        return

    if flow.request.method == "POST":
        content_type = flow.request.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                data = json.loads(flow.request.text)
                # Ignore noisy presence/heartbeat messages
                if data.get("type") in ["presence", "heartbeat"]:
                    return

                print(f"\n[>> OUTGOING HTTP POST] {flow.request.pretty_url}")
                found_text = extract_text(data)
                if found_text:
                    print(f"Found Content: {found_text[:1000]}")
                else:
                    print(f"Raw Data: {json.dumps(data, indent=2)[:500]}...")
            except:
                pass

def response(flow: http.HTTPFlow):
    if not is_target(flow):
        return
        
    content_type = flow.response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        try:
            data = json.loads(flow.response.text)
            if data.get("type") in ["presence", "heartbeat"]:
                return

            print(f"\n[<< INCOMING HTTP RESPONSE] {flow.request.pretty_url}")
            found_text = extract_text(data)
            if found_text:
                print(f"Found Content: {found_text[:1000]}")
            else:
                # Often responses are lists of objects
                print(f"Summary: {str(data)[:200]}...")
        except:
            pass

def websocket_message(flow: http.HTTPFlow):
    if not is_target(flow):
        return

    message = flow.websocket.messages[-1]
    direction = ">> OUTGOING WS" if message.from_client else "<< INCOMING WS"
    content = message.content
    
    try:
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        json_data = json.loads(content)
        
        # Filter out noisy presence updates
        if isinstance(json_data, dict) and json_data.get("type") in ["presence", "heartbeat"]:
            return

        print(f"\n[{direction}] {flow.request.pretty_host}")
        
        # Deep extract for ChatGPT's complex WS envelopes
        text = extract_text(json_data)
        if text:
            print(f"Message: {text}")
        else:
            print(f"JSON Structure: {json.dumps(json_data, indent=2)[:500]}...")
            
    except:
        # If not JSON, print if it looks like meaningful text
        if len(content) > 5:
            print(f"\n[{direction}] {flow.request.pretty_host}")
            print(f"Raw: {content}")
