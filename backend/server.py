import os
import time
import queue
import threading
import numpy as np
import pyaudio
import webrtcvad_wheels as webrtcvad
import soundcard as sc
from faster_whisper import WhisperModel
from fastapi import FastAPI, WebSocket, Request, BackgroundTasks, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json

# Memory Manager
from memory_manager import MemoryManager
# ToolBox
from toolbox import ToolBox

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Config & State ---
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
VAD_AGGRESSIVENESS = 3 # 0-3

audio_queue = queue.Queue() # Items: (audio_data_float32, source_type)
result_queue = queue.Queue()

running = True
memory_manager = None # Initialized in startup
toolbox = None # Initialized in startup

# --- Data Models ---
class BrowserData(BaseModel):
    url: str
    title: str
    content: str

class ExternalCommand(BaseModel):
    command: str

# --- Audio Threads ---

def user_voice_thread():
    """
    Captures microphone input, applies VAD, and pushes speech segments to queue.
    """
    print("[User Voice] Thread Started")
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    pa = pyaudio.PyAudio()
    
    try:
        stream = pa.open(format=pyaudio.paInt16,
                         channels=1,
                         rate=SAMPLE_RATE,
                         input=True,
                         frames_per_buffer=FRAME_SIZE)
    except Exception as e:
        print(f"[User Voice] Error opening stream: {e}")
        return

    print("[User Voice] Listening...")
    
    buffer = []
    triggered = False
    
    while running:
        try:
            pcm_data = stream.read(FRAME_SIZE, exception_on_overflow=False)
            is_speech = vad.is_speech(pcm_data, SAMPLE_RATE)

            if is_speech:
                if not triggered:
                    triggered = True
                    # print("[User Voice] Speech Detected")
                buffer.append(pcm_data)
            else:
                if triggered:
                    if len(buffer) > 10: # Min duration check (approx 300ms)
                        # Convert buffer to numpy float32
                        full_audio = b''.join(buffer)
                        audio_np = np.frombuffer(full_audio, dtype=np.int16).astype(np.float32) / 32768.0
                        audio_queue.put((audio_np, "user"))
                        print(f"[User Voice] Segment queued: {len(audio_np)/SAMPLE_RATE:.2f}s")
                    
                    buffer = []
                    triggered = False
        except Exception as e:
            print(f"[User Voice] Error: {e}")
            break

    stream.stop_stream()
    stream.close()
    pa.terminate()

def system_audio_thread():
    """
    Captures system loopback audio using soundcard.
    """
    print("[System Audio] Thread Started")
    
    try:
        loopback_mic = sc.default_microphone() # Fallback
        mics = sc.all_microphones(include_loopback=True)
        for mic in mics:
            if 'loopback' in mic.name.lower() or 'stereo mix' in mic.name.lower():
                loopback_mic = mic
                break
        
        print(f"[System Audio] Using device: {loopback_mic.name}")

        with loopback_mic.recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
             while running:
                # Record in chunks
                data = mic.record(numframes=SAMPLE_RATE * 5) # Record 5 second chunks for testing
                # data is shape (frames, channels), float32
                
                # Simple energy-based VAD for system audio
                energy = np.mean(data**2)
                if energy > 0.001: # Threshold needed
                    audio_queue.put((data.flatten(), "system"))
                    print(f"[System Audio] Segment queued: {len(data)/SAMPLE_RATE:.2f}s")
                
    except Exception as e:
         print(f"[System Audio] Error: {e}")

def transcription_thread():
    """
    Consumes audio segments and runs Whisper.
    """
    global memory_manager
    print("[Transcription] Thread Started")
    
    # Load Model
    try:
        # Use 'tiny' or 'base' for speed on CPU if no GPU
        model = WhisperModel("tiny", device="cpu", compute_type="int8") 
        print("[Transcription] Model Loaded")
    except Exception as e:
        print(f"[Transcription] Failed to load model: {e}")
        return

    while running:
        try:
            audio_data, source = audio_queue.get()
            
            segments, info = model.transcribe(audio_data, beam_size=5)
            
            full_text = ""
            for segment in segments:
                full_text += segment.text + " "
            
            full_text = full_text.strip()
            if full_text:
                print(f"[{source.upper()}] Transcribed: {full_text}")
                
                if source == "system":
                    # Store to Stream Context (Memory)
                    if memory_manager:
                        memory_manager.add_memory(full_text, source="system")
                elif source == "user":
                    # Query Brain (RAG + LLM)
                    if memory_manager:
                        # Check for Agent Commands here (Simplistic regex/keyword check for now)
                        if "fix my wifi" in full_text.lower():
                            print("[Agent] Triggering WiFi Fix Sequence...")
                            # In real app: call LLM with tools. Here: direct call for demo.
                            if toolbox:
                                logs = toolbox.read_error_logs()
                                print(f"[Agent] Analyzed Logs: {logs}")
                                res = toolbox.execute_system_command("ipconfig /flushdns")
                                print(f"[Agent] Action Result: {res}")

                        response = memory_manager.query_brain(full_text)
                        print(f"[OMNI-BOT Response]: {response}")
                
        except Exception as e:
            print(f"[Transcription] Error: {e}")

# --- API Endpoints ---

@app.on_event("startup")
def startup_event():
    global memory_manager, toolbox
    memory_manager = MemoryManager()
    toolbox = ToolBox()
    
    # Start threads
    t1 = threading.Thread(target=user_voice_thread, daemon=True)
    t2 = threading.Thread(target=system_audio_thread, daemon=True)
    t3 = threading.Thread(target=transcription_thread, daemon=True)
    t1.start()
    t2.start()
    t3.start()

@app.get("/")
def read_root():
    return {"status": "Super-Bot Backend Running"}

@app.get("/test")
def test_connection():
    return {"message": "Hello Electron"}

@app.post("/ingest-browser")
async def ingest_browser(data: BrowserData, background_tasks: BackgroundTasks):
    """
    Endpoint for Chrome Extension to send browser history.
    """
    global memory_manager
    if memory_manager:
        memory_manager.add_memory(
            text=f"User visited {data.title} ({data.url}). Content: {data.content[:500]}...",
            source="browser",
            metadata={"url": data.url, "title": data.title}
        )
    return {"status": "ingested"}

@app.post("/api/external-command")
async def external_command(cmd: ExternalCommand, x_api_key: str = Header(None)):
    """
    External API endpoint to trigger bot actions.
    Requires X-API-Key header matching env var.
    """
    expected_key = os.environ.get("EXTERNAL_API_KEY")
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    print(f"[External API] Command received: {cmd.command}")
    
    # Process command (simplified)
    # Ideally reuse the same logic as User Voice -> LLM -> Tools
    if toolbox:
       # Placeholder for direct execution vs LLM processing
       return {"status": "Received", "command": cmd.command}
    
    return {"status": "Processing"}

@app.websocket("/ws/live-stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Broadcast status (mocked for now)
            # In real app, threads would push state updates to a queue that this loop consumes
            await websocket.send_json({"state": "Listening", "timestamp": time.time()})
            await asyncio.sleep(1)
    except Exception as e:
        print(f"[WebSocket] Disconnected: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
