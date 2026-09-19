"""
MODAL/transcribe.py — Service de transcription GPU pour F00B_VOX (l'Oreille Absolue)
======================================================================================
Endpoint OpenAI-compatible `/audio/transcriptions` consomme par
`auto_detector.PremiumTranscriber`.

Contrat d'entree (multipart/form-data, envoye par f00b_vox) :
  - file                    : audio (.m4a AAC)
  - model                   : ignore (modele fixe au deploy via WHISPER_MODEL)
  - language                : ex. "en"
  - response_format         : ignore (on renvoie TOUJOURS du word-level)
  - timestamp_granularities[]: ignore
  - offset                  : OPTIONNEL (mode matrice). Offset GLOBAL en secondes
                              du debut du segment audio dans la VOD. Les timestamps
                              des mots renvoyes sont alors deja globaux (local+offset).
                              Absent (ou 0) => comportement historique inchange :
                              timestamps locaux, le client les relocalise lui-meme.

Contrat de sortie (JSON) — format "Case 1" que VOX prefere pour le scoring :
  {"words": [{"word": "...", "start": 1.23, "end": 1.45}, ...], "text": "..."}

AUCUN secret dans ce fichier. Le token Modal se configure hors repo :
  modal token set --token-id <id> --token-secret <secret>

Deploy :
  modal deploy transcribe.py
L'URL est affichee par Modal ; la copier dans f00b_secrets.json -> base_url.
"""

import os

import modal
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

MODEL_NAME = os.environ.get("WHISPER_MODEL", "medium")
GPU_TYPE = os.environ.get("WHISPER_GPU", "T4").strip()

# Modal : "cpu" n'est PAS un type de GPU valide — il faut omettre gpu= pour tourner
# sur CPU. Le device reel (cuda vs cpu) est auto-detecte dans _device().
_GPU_KWARGS = (
    {} if GPU_TYPE.lower() in ("", "cpu", "none", "auto") else {"gpu": GPU_TYPE}
)

def _device():
    # GPU toujours present via @app.function(gpu=GPU) ; fallback CPU par securite.
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def _download_model():
    # Telecharge le modele au BUILD de l'image (cache, pas au cold start).
    from faster_whisper import WhisperModel
    WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")


image = (
    modal.Image.from_registry("nvidia/cuda:12.4.0-runtime-ubuntu22.04", add_python="3.11")
    .pip_install(
        "faster-whisper==1.1.1",
        "fastapi==0.115.0",
        "uvicorn[standard]==0.30.6",
        "python-multipart==0.0.20",
        "requests==2.32.3",
    )
    .run_function(_download_model, timeout=900)
)

app = modal.App("perturabo-whisper")

web_app = FastAPI(title="PERTURABO Whisper (F00B_VOX)")

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _device_name, _compute = _device()
        _model = WhisperModel(MODEL_NAME, device=_device_name, compute_type=_compute)
    return _model


@app.function(image=image, scaledown_window=120, **_GPU_KWARGS)
@modal.asgi_app()
def fastapi_app():
    return web_app


@web_app.get("/")
def health():
    return {"ok": True, "model": MODEL_NAME, "gpu": GPU_TYPE or "cpu", "offset_mode": True}


@web_app.post("/audio/transcriptions")
async def transcribe(request: Request):
    form = await request.form()
    upload = form.get("file")
    if upload is None:
        return JSONResponse({"error": "champ 'file' manquant"}, status_code=400)

    data = await upload.read()
    language = form.get("language") or None

    # Mode matrice : offset global du segment dans la VOD ("0"/absent => 0.0).
    try:
        offset = float(form.get("offset") or 0.0)
    except (TypeError, ValueError):
        offset = 0.0
    if offset < 0:
        offset = 0.0

    import tempfile

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        model = _get_model()
        segments, info = model.transcribe(
            tmp_path,
            language=language or None,
            word_timestamps=True,
            beam_size=5,
            vad_filter=True,
        )

        words = []
        for seg in segments:
            for w in getattr(seg, "words", None) or []:
                words.append(
                    {
                        "word": w.word,
                        "start": round(w.start + offset, 3),
                        "end": round(w.end + offset, 3),
                    }
                )

        text = " ".join(w["word"] for w in words).strip()
        return {
            "words": words,
            "text": text,
            "language": getattr(info, "language", language),
        }
    except Exception as e:
        import traceback
        return JSONResponse(
            {"error": str(e), "trace": traceback.format_exc()},
            status_code=500,
        )
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
