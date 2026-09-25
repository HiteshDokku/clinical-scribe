import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from .ring_buffer import RingBuffer
from .vad import VADGater
from .transcriber import Transcriber
from .diarizer import OnlineDiarizer

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

    from .vad_segmenter import VadSegmenter
    import time
    
    vad_segmenter = VadSegmenter()
    session_start_time = time.time()
    
    utterance_start_ms = 0
    total_audio_bytes = 0
    BYTES_PER_MS = 32 # 16kHz 16-bit mono
    
    last_partial_time = time.time()
    
    partial_task = None
    
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            
            if "bytes" in message:
                data = message["bytes"]
                
                was_active = vad_segmenter.is_utterance_active
                is_active, partial_buffer, final_audio = vad_segmenter.process_chunk(data)
                
                # Update total bytes to compute timestamps
                current_ms = total_audio_bytes // BYTES_PER_MS
                total_audio_bytes += len(data)
                
                if is_active and not was_active:
                    # newly started utterance
                    utterance_start_ms = current_ms
                
                if final_audio is not None:
                    # Utterance finished
                    utterance_end_ms = current_ms
                    
                    if partial_task is not None and not partial_task.done():
                        partial_task.cancel()
                    
                    if utterance_end_ms > utterance_start_ms:
                        # Transcription without diarization
                        events = await asyncio.to_thread(
                            transcriber.transcribe,
                            final_audio,
                            True, # is_final
                            None, # speaker
                            0.0   # speaker_confidence
                        )
                        for event in events:
                            if event.start_ms is None or event.end_ms is None:
                                event.start_ms = utterance_start_ms
                                event.end_ms = utterance_end_ms
                            else:
                                # Relativize Whisper timestamps to the utterance start
                                event.start_ms += utterance_start_ms
                                event.end_ms += utterance_start_ms
                                
                            if event.end_ms <= event.start_ms:
                                print(f"BUG: Ignored invalid segment with end_ms ({event.end_ms}) <= start_ms ({event.start_ms})")
                                continue
                                
                            await websocket.send_text(event.model_dump_json())
                    else:
                        print(f"BUG: Invalid utterance timestamps: end_ms ({utterance_end_ms}) <= start_ms ({utterance_start_ms})")
                            
                elif partial_buffer is not None:
                    # Ongoing utterance
                    now = time.time()
                    if now - last_partial_time > 1.0:
                        if partial_task is None or partial_task.done():
                            last_partial_time = now
                            
                            async def run_and_send_partial(buf, start, curr):
                                try:
                                    evs = await asyncio.to_thread(
                                        transcriber.transcribe,
                                        buf,
                                        False, # is_final
                                        None,  # speaker
                                        0.0    # speaker_confidence
                                    )
                                    for e in evs:
                                        e.start_ms = start
                                        e.end_ms = curr
                                        await websocket.send_text(e.model_dump_json())
                                except asyncio.CancelledError:
                                    pass
                                except Exception as e:
                                    print(f"Error in partial transcription: {e}")
                                    
                            partial_task = asyncio.create_task(run_and_send_partial(partial_buffer, utterance_start_ms, current_ms))
                        
            elif "text" in message:
                try:
                    msg = json.loads(message["text"])
                    if msg.get("t") == "stop":
                        try:
                            if partial_task is not None and not partial_task.done():
                                partial_task.cancel()
                                
                            final_audio = vad_segmenter.force_flush()
                            if final_audio is not None:
                                current_ms = total_audio_bytes // BYTES_PER_MS
                                utterance_end_ms = current_ms
                                if utterance_end_ms > utterance_start_ms:
                                    events = await asyncio.to_thread(
                                        transcriber.transcribe,
                                        final_audio,
                                        True,
                                        None,
                                        0.0
                                    )
                                    for event in events:
                                        if event.start_ms is None or event.end_ms is None:
                                            event.start_ms = utterance_start_ms
                                            event.end_ms = utterance_end_ms
                                        else:
                                            event.start_ms += utterance_start_ms
                                            event.end_ms += utterance_start_ms
                                            
                                        if event.end_ms <= event.start_ms:
                                            print(f"BUG: Ignored invalid segment with end_ms ({event.end_ms}) <= start_ms ({event.start_ms})")
                                            continue
                                        await websocket.send_text(event.model_dump_json())
                        except Exception as e:
                            print(f"Error during final transcribe: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            try:
                                await websocket.send_text(json.dumps({"t": "done"}))
                            except Exception:
                                pass
                            break
                except Exception as e:
                    print(f"Error parsing message: {e}")
                    pass
    except WebSocketDisconnect:
        pass
