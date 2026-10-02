from pathlib import Path
from uuid import uuid4

import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ADEX VOICE API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    text: str
    voice: str

    @field_validator("text", "voice")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field must not be empty.")
        return value


@app.get("/voices")
async def get_voices() -> list[dict[str, str]]:
    try:
        voices = await edge_tts.list_voices()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to retrieve voices.") from exc

    return [
        {
            "shortName": voice["ShortName"],
            "friendlyName": voice["FriendlyName"],
            "gender": voice["Gender"],
            "locale": voice["Locale"],
            "language": voice["Locale"].split("-")[0],
        }
        for voice in voices
    ]


@app.post("/generate")
async def generate_audio(request: GenerateRequest) -> FileResponse:
    output_path = OUTPUT_DIR / f"{uuid4()}.mp3"
    try:
        communicator = edge_tts.Communicate(request.text, request.voice)
        await communicator.save(str(output_path))
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        raise HTTPException(status_code=502, detail="Unable to generate audio.") from exc

    return FileResponse(
        path=output_path,
        media_type="audio/mpeg",
        filename="adex_voice.mp3",
    )