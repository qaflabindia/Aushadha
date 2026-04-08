import logging
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from src.llm import translate_text
from src.shared.env_utils import get_value_from_env
from openai import OpenAI

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audio", tags=["audio"])

class TranslationRequest(BaseModel):
    text: str
    target_lang: str
    source_lang: str = "en"

class SpeakRequest(BaseModel):
    text: str
    lang: str = "en-US"
    voice: str = "alloy"

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), language: str = None):
    """
    Transcribe audio file using OpenAI Whisper.
    Optional language hint (e.g. 'hi', 'ta') can be provided.
    """
    try:
        api_key = get_value_from_env("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

        client = OpenAI(api_key=api_key)
        
        import tempfile
        filename = file.filename if file.filename else "audio.webm"
        
        # Use NamedTemporaryFile to avoid race conditions and handle cleanup automatically
        with tempfile.NamedTemporaryFile(delete=True, suffix=os.path.splitext(filename)[1]) as temp_audio:
            temp_audio.write(await file.read())
            temp_audio.flush()
            
            with open(temp_audio.name, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    language=language if language and language != "en" else None
                )
            return {"text": transcript.text}

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/translate")
async def translate_audio_text(req: TranslationRequest):
    """
    Translate text for multi-lingual TTS support.
    """
    try:
        translated = await translate_text(req.text, req.target_lang, req.source_lang)
        return {"translatedText": translated}
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/speak")
async def text_to_speech(req: SpeakRequest):
    """
    Generate audio from text using OpenAI TTS (fallback for browser).
    """
    try:
        api_key = get_value_from_env("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

        client = OpenAI(api_key=api_key)
        
        # Mapping BCP-47 to some common voices if needed, or just let user pass it
        # Defaulting to alloy
        response = client.audio.speech.create(
            model="tts-1",
            voice=req.voice,
            input=req.text
        )
        
        # Stream the audio response
        import io
        from fastapi.responses import StreamingResponse
        
        audio_stream = io.BytesIO(response.content)
        return StreamingResponse(audio_stream, media_type="audio/mpeg")
        
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
