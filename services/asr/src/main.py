import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from .ring_buffer import RingBuffer
from .vad import VADGater
from .transcriber import Transcriber

app = FastAPI(title="asr")

vad_gater = VADGater()
transcriber = Transcriber()

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "asr"}

@app.websocket("/transcribe")
async def transcribe_ws(websocket: WebSocket):
    await websocket.accept()
    
    # Wait for handshake gracefully, ignoring premature binary frames
    encounter_id = None
    while encounter_id is None:
        try:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                return
            if "text" in msg:
                handshake_text = msg["text"]
                try:
                    handshake = json.loads(handshake_text)
                    encounter_id = handshake["encounter_id"]
                except (json.JSONDecodeError, KeyError):
                    await websocket.close(code=1008, reason="Invalid handshake")
                    return
            elif "bytes" in msg:
                # Ignore early audio frames arriving before handshake
                pass
        except WebSocketDisconnect:
            return

    # 30 seconds of 16kHz mono 16-bit PCM = 30 * 16000 * 2 bytes = 960000 bytes
    ring_buffer = RingBuffer(maxlen=960000)
    
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            
            if "bytes" in message:
                data = message["bytes"]
                
                # Simple VAD check per chunk. If speech, we buffer it.
                is_speech = vad_gater.is_speech(data)
                
                if is_speech:
                    ring_buffer.append(data)
                    audio_to_transcribe = ring_buffer.get_all()
                    events = transcriber.transcribe(audio_to_transcribe, is_final=False)
                    for event in events:
                        await websocket.send_text(event.model_dump_json())
                        
            elif "text" in message:
                try:
                    msg = json.loads(message["text"])
                    if msg.get("t") == "stop":
                        audio_to_transcribe = ring_buffer.get_all()
                        events = transcriber.transcribe(audio_to_transcribe, is_final=True)
                        for event in events:
                            await websocket.send_text(event.model_dump_json())
                        break
                except Exception:
                    pass
                    
    except WebSocketDisconnect:
        pass
    finally:
        ring_buffer.clear()
