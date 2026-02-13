from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import os
import json
import asyncio
import time

app = FastAPI()
templates = Jinja2Templates(directory="templates")
LOG_FILE = "traffic_log.jsonl"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/logs")
async def stream_logs():
    async def log_generator():
        # Start reading from the end of the file initially? 
        # Or just stream everything since startup.
        # For simplicity, let's stream logs as they come in.
        
        # Ensure file exists
        if not os.path.exists(LOG_FILE):
             with open(LOG_FILE, 'w') as f: f.write("")
        
        f = open(LOG_FILE, "r", encoding="utf-8")
        # Go to end of file to stream only NEW logs
        f.seek(0, os.SEEK_END)
        
        while True:
            line = f.readline()
            if line:
                yield f"data: {line}\n\n"
            else:
                await asyncio.sleep(0.1)

    return StreamingResponse(log_generator(), media_type="text/event-stream")

@app.get("/api/history")
async def get_history():
    """Returns the last 50 logs for initial load."""
    if not os.path.exists(LOG_FILE):
        return []
    
    logs = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        # Read all lines is risky if file is huge, but fine for local tool
        lines = f.readlines()
        for line in lines[-50:]: # Last 50 items
            try:
                logs.append(json.loads(line))
            except:
                pass
    return logs

if __name__ == "__main__":
    import uvicorn
    print("🚀 Viewer running at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
