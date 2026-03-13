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

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe audio file using OpenAI Whisper.
    """
    try:
        api_key = get_value_from_env("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

        client = OpenAI(api_key=api_key)
        
        # Save temporary file with original extension if possible
        filename = file.filename if file.filename else "audio.webm"
        temp_file_path = f"/tmp/{filename}"
        
        with open(temp_file_path, "wb") as f:
            f.write(await file.read())

        try:
            with open(temp_file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
            return {"text": transcript.text}
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

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
