"""
audio_sensor.py — Capteur audio (rire / applaudissement / activité) — P4
=========================================================================
Hérésie zéro : on n'analyse JAMAIS toute la VOD avec un modèle lourd.
On reçoit une fenêtre (start,end) et on calcule, depuis la piste audio
DÉJÀ téléchargée (stream copy), des features légères (énergie RMS + zero
crossing rate + modulation). Détection HEURISTIQUE (documentée comme telle),
sans modèle externe ni clé.

Dégradation gracieuse : sans numpy / sans ffmpeg / fichier absent → None.
Aucun secret. Gratuit.
"""

import subprocess

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

SR = 16000


def _read_raw(audio_path, s, e, sr=SR):
    """Extrait la fenêtre [s,e) en PCM mono s16le via ffmpeg, sans ré-encoder fort."""
    if np is None or not audio_path or not os.path.exists(audio_path):
        return None
    dur = max(float(e) - float(s), 1.0)
    cmd = [
        "ffmpeg", "-ss", f"{float(s):.2f}", "-t", f"{dur:.2f}",
        "-i", audio_path, "-vn", "-ac", "1", "-ar", str(sr),
        "-f", "s16le", "-",
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=120)
    except Exception:
        return None
    if p.returncode != 0 or not p.stdout:
        return None
    data = np.frombuffer(p.stdout, dtype="<i2").astype(np.float32) / 32768.0
    if data.size < sr * 0.5:
        return None
    return data, sr


def _rms_env(data, sr, frame=0.02):
    fl = int(sr * frame)
    n = len(data) // fl
    if n == 0:
        return np.array([], dtype=np.float32)
    seg = data[: n * fl].reshape(n, fl)
    return np.sqrt(np.mean(seg ** 2, axis=1))


def _zcr(data):
    if data.size < 2:
        return 0.0
    return float(np.mean(np.abs(np.diff(np.sign(data))) > 0))


def laugh_score(audio_path, s, e):
    """0..1 : probabilité heuristique de rire (bursts périodiques + énergie + ZCR)."""
    got = _read_raw(audio_path, s, e)
    if got is None:
        return None
    data, sr = got
    env = _rms_env(data, sr)
    if env.size < 3:
        return 0.0
    mean = float(np.mean(env))
    peak = float(np.max(env))
    if peak < 0.02:
        return 0.0
    thr = max(mean * 1.5, 0.03)
    above = env > thr
    bursts = int(np.sum(np.diff(above.astype(np.int8)) == 1))
    z = _zcr(data)
    score = (0.4 * min(1.0, bursts / 8.0)
             + 0.3 * min(1.0, z / 0.25)
             + 0.3 * min(1.0, mean / 0.4))
    return round(min(1.0, max(0.0, score)), 3)


def applause_score(audio_path, s, e):
    """0..1 : probabilité d'applaudissement (bruit large bande dense, peu de silence)."""
    got = _read_raw(audio_path, s, e)
    if got is None:
        return None
    data, sr = got
    env = _rms_env(data, sr)
    if env.size < 3:
        return 0.0
    mean = float(np.mean(env))
    z = _zcr(data)
    silence_frac = float(np.mean(env < 0.01))
    score = (0.5 * min(1.0, z / 0.30)
             + 0.3 * min(1.0, mean / 0.25)
             + 0.2 * (1.0 - silence_frac))
    return round(min(1.0, max(0.0, score)), 3)
