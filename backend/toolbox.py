import os
import subprocess
import json
import asyncio
from typing import List, Dict, Optional
# from playwright.async_api import async_playwright # Dynamic import in method to avoid startup block if not installed

# PyWin32 for Event Logs
try:
    import win32evtlog
except ImportError:
    win32evtlog = None

class ToolBox:
    def __init__(self):
        print("[ToolBox] Initialized")

    async def google_search_and_download(self, query: str, download_folder: str = "downloads"):
        """
        Uses Playwright to search Google, click the first result, and attempt to download a file if present.
        (Simplified version: Just returns the first result URL for now to avoid complex navigation logic without specific targets)
        """
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            print(f"[ToolBox] Searching Google for: {query}")
            await page.goto(f"https://www.google.com/search?q={query}")
            
            # Simple selector for first result
            first_result = await page.wait_for_selector('h3')
            await first_result.click()
            
            await page.wait_for_load_state('domcontentloaded')
            title = await page.title()
            url = page.url
            
            print(f"[ToolBox] Found: {title} ({url})")
            await browser.close()
            return {"title": title, "url": url, "action": "navigated"}

    def execute_system_command(self, command: str):
        """
        Executes a shell command. 
        Safety Check: Blocks critical commands unless explicitly overridden (not implemented here for simplicity, relying on LLM to be smart).
        """
        risky_keywords = ["format", "del", "rm", "rd", "/s", "/q"]
        if any(keyword in command.lower() for keyword in risky_keywords):
            return {"error": "Safety Check Failed: Command contains risky keywords. User confirmation required."}
        
        print(f"[ToolBox] Executing: {command}")
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return {
                "stdout": result.stdout[:500], # Trucate for token limits
                "stderr": result.stderr[:500],
                "returncode": result.returncode
            }
        except Exception as e:
            return {"error": str(e)}

    def read_error_logs(self, limit: int = 10):
        """
        Reads the last N error events from Windows System log.
        """
        if not win32evtlog:
            return {"error": "pywin32 not installed"}

        server = 'localhost'
        log_type = 'System'
        hand = win32evtlog.OpenEventLog(server, log_type)
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        total = 0
        events_list = []
        
        while True:
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            if not events:
                break
            for event in events:
                if event.EventType == win32evtlog.EVENTLOG_ERROR_TYPE:
                    events_list.append({
                        "EventID": event.EventID,
                        "Source": event.SourceName,
                        "Time": str(event.TimeGenerated),
                        "Message": "Active adapter issue" if "adapter" in str(event.SourceName).lower() else "Generic System Error" # Placeholder as full message requires DLL lookup
                    })
                    total += 1
                    if total >= limit:
                        break
            if total >= limit:
                break
                
        win32evtlog.CloseEventLog(hand)
        return events_list

toolbox = ToolBox()
