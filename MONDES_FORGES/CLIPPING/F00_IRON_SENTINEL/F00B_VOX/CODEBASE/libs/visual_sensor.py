"""
visual_sensor.py — Capteur visuel (visage speaker / cut) — P4
=============================================================
Règle pur_directive : « Hook = visage speaker, pas de B-roll ».
Ce capteur confirme la présence d'un visage + détecte les cuts
(un montage qui respire). Sans modèle externe lourd ni clé :
  - visage  : OpenCV Haar cascade (frontal face), frames échantillonnées.
  - cut     : ffmpeg scene detection (seuil scene>0.3).

Dégradation gracieuse : sans cv2 / sans vidéo / sans ffmpeg → None.
Gratuit. Aucun secret.
"""

import os
import subprocess

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


def _grab_frames(video_path, s, e, n=4, tmp_dir=None):
    """Extrait n frames PNG de la fenêtre via ffmpeg. Retourne liste cv2 (BGR) ou []."""
    if cv2 is None or not video_path or not os.path.exists(video_path):
        return []
    import tempfile
    td = tmp_dir or tempfile.mkdtemp(prefix="vox_vis_")
    dur = max(float(e) - float(s), 0.5)
    fps = max(n / dur, 1.0)
    pat = os.path.join(td, "f_%02d.png")
    cmd = ["ffmpeg", "-ss", f"{float(s):.2f}", "-t", f"{dur:.2f}",
           "-i", video_path, "-vf", f"fps={fps:.3f}",
           "-frames:v", str(n), pat, "-y"]
    try:
        subprocess.run(cmd, capture_output=True, timeout=90, check=True)
    except Exception:
        return []
    frames = []
    for i in range(1, n + 1):
        fp = os.path.join(td, f"f_{i:02d}.png")
        if os.path.exists(fp):
            img = cv2.imread(fp)
            if img is not None:
                frames.append(img)
    return frames


def face_score(video_path, s, e, n=4):
    """0..1 : fraction des frames avec au moins un visage détecté."""
    frames = _grab_frames(video_path, s, e, n=n)
    if not frames:
        return None
    casc = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    clf = cv2.CascadeClassifier(casc)
    hits = 0
    for fr in frames:
        gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        faces = clf.detectMultiScale(gray, 1.1, 5)
        if len(faces) > 0:
            hits += 1
    return round(hits / len(frames), 3)


def cut_score(video_path, s, e):
    """0..1 : densité de cuts (1 cut / 2s = max)."""
    if not video_path or not os.path.exists(video_path):
        return None
    dur = max(float(e) - float(s), 0.5)
    cmd = ["ffmpeg", "-ss", f"{float(s):.2f}", "-t", f"{dur:.2f}",
           "-i", video_path, "-vf", "select='gt(scene,0.3)',showinfo",
           "-f", "null", "-"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    except Exception:
        return None
    cuts = (p.stderr or "").count("[Parsed_showinfo")
    return round(min(1.0, cuts / max(1.0, dur / 2.0)), 3)
