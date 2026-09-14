# transcripts_in — Source opérateur (priorité absolue)

L'opérateur dépose ici un transcript **complet de la vidéo** (pas par clip) :
le système découpe automatiquement chaque candidat dans la fenêtre de son clip.

## Convention de nommage (obligatoire)

```
{video_id}.fr.srt   {video_id}.fr.vtt   {video_id}.fr.txt
{video_id}.en.srt   {video_id}.en.vtt   {video_id}.en.txt
```

`{video_id}` = l'identifiant YouTube dans l'URL.
Exemple pour `https://www.youtube.com/watch?v=cP8vli4kfhs` :

```
cP8vli4kfhs.fr.srt   ← piste française
cP8vli4kfhs.en.srt   ← piste anglaise
```

## Priorités

1. **Fichiers ici** (opérateur) — toujours utilisés en premier, jamais rate-limités.
2. Cache d'un téléchargement YouTube antérieur.
3. Sous-titres YouTube (yt-dlp).
4. Filet Whisper local (si installé) — dernier recours.

## Formats acceptés

- **SRT** et **VTT** : horodatage exact, recommandé.
- **TXT brut** : une ligne = ~3 secondes (précision approximative, suffisant pour lecture).

Une seule langue suffit — l'autre restera « indisponible » avec un message propre.
