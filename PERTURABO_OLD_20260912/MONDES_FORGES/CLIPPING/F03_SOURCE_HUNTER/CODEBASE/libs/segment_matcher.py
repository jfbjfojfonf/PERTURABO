"""
libs/segment_matcher.py — Match angle ↔ transcript des assets (F03_SOURCE_HUNTER)
=================================================================================

En mode auto, associe chaque angle (4 axes : angle_family, emotion_mode,
engagement_type, reframe_dim) aux segments du transcript des assets de la
campagne : score par banques de mots-clés (émotion + reframe), regroupement
en fenêtres contiguës, clamp durée plateforme via duration_guard, et choix
de l'asset porteur le plus fort par angle.

Le match auto est INDICATIF — l'IRON affine qualitativement en Phase 2
(le prompt de --prepare lui transmet transcript + angles bruts). Chaque
score est tracé dans la rationale (aucun chiffre inventé, hérésie "verdict
sans preuve").

Usage:
  from segment_matcher import SegmentMatcher
  matcher = SegmentMatcher(loader, guard)
  best = matcher.best_asset_for_angle(angle, assets, platform)
  segments = matcher.suggested_segments(angle, asset, platform)
"""

_EMOTION_KEYWORDS = {
    "tension": [
        "danger", "risque", "menace", "pression", "crise", "impossible",
        "worst", "risk", "danger", "pressure", "crisis", "close call",
    ],
    "joie": [
        "incroyable", "victoire", "genial", "super", "amazing", "awesome",
        "win", "victory", "incredible", "best day", "love it",
    ],
    "inspiration": [
        "discipline", "sacrifice", "reve", "perseverance", "travail",
        "discipline", "sacrifice", "dream", "grind", "never give up",
        "kept going", "built",
    ],
    "outrage": [
        "injuste", "scandale", "honte", "mensonge", "abuse", "manipulation",
        "unfair", "scandal", "shame", "lie", "abuse", "manipulated",
    ],
    "admiration": [
        "respect", "force", "hero", "legend", "masterpiece", "respect",
        "strength", "legendary", "genius", "goat",
    ],
}

_REFRAME_KEYWORDS = {
    "victime_vers_survivant": ["survivre", "victime", "survived", "victim", "overcame", "refused to lose"],
    "anonyme_vers_incroyable": ["personne ne connaissait", "unknown", "nobody knew", "nobody", "stranger", "quiet guy"],
    "banal_vers_suspect": ["apparemment normal", "seemed normal", "ordinary", "nobody suspected", "hidden"],
    "fait_vers_absurde": ["absurde", "ridicule", "absurd", "ridiculous", "unbelievable", "how is this real"],
    "echec_vers_lecon": ["j'ai echoue", "lecon", "failed", "lesson", "mistake", "learned", "went wrong"],
    "seul_vers_communaute": ["seul", "abandonne", "alone", "abandoned", "no one helped", "found people"],
    "cache_vers_revele": ["revele", "secret", "decouvert", "revealed", "secret", "discovered", "uncovered"],
    "ordinaire_vers_extraordinaire": ["simple employe", "ordinary", "normal guy", "nobody special", "average"],
}


def _hits(text: str, keywords: list[str]) -> list[str]:
    if not text:
        return []
    low = text.lower()
    return [k for k in keywords if k in low]


class SegmentMatcher:
    def __init__(self, loader, guard):
        self.loader = loader
        self.guard = guard

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    def _score_segments(self, angle: dict, segments: list[dict]) -> list[dict]:
        """Score chaque segment du transcript selon les banques de l'angle."""
        emotion = angle.get("emotion_mode", "")
        reframe = angle.get("reframe_dim", "")
        bank = list(_EMOTION_KEYWORDS.get(emotion, []))
        bank += list(_REFRAME_KEYWORDS.get(reframe, []))
        if not bank:
            return []

        scored = []
        for seg in segments:
            text = seg.get("text", "").strip()
            if not text:
                continue
            hits = _hits(text, bank)
            if hits:
                scored.append({
                    "start": float(seg.get("start", 0)),
                    "duration": float(seg.get("duration", 0)),
                    "text": text,
                    "score": len(hits),
                    "hits": hits[:5],
                })
        return scored

    def _best_windows(self, scored: list[dict], segments: list[dict],
                      lo: int, hi: int, top: int = 3) -> list[dict]:
        """Fenêtres contiguës dans [lo, hi] secondes, les plus scorées.

        `scored` = segments ayant des hits (sparse), `segments` = transcript
        complet. Si la meilleure fenêtre scorée est plus courte que lo
        (ex: un punch de 6s sur un minimum de 15s), on l'étend avec les
        segments suivants du transcript (score non requis) jusqu'à
        atteindre lo — la coupe reste une directive, l'IRON affine.
        """
        windows = []
        n = len(scored)
        for i in range(n):
            start = scored[i]["start"]
            best = {
                "start": start,
                "end": start + scored[i]["duration"],
                "score": scored[i]["score"],
                "text": scored[i]["text"],
            }
            acc = best["score"]
            text = best["text"]
            end = best["end"]
            j = i
            while j + 1 < n:
                nxt = scored[j + 1]
                nxt_end = nxt["start"] + nxt["duration"]
                if nxt_end - start > hi:
                    break
                acc += nxt["score"]
                text = text + " " + nxt["text"]
                end = nxt_end
                if acc > best["score"]:
                    best = {"start": start, "end": end, "score": acc, "text": text}
                j += 1

            # Extension sur le transcript complet pour atteindre lo
            if best["end"] - best["start"] < lo:
                ext_text = best["text"]
                ext_end = best["end"]
                for seg in segments:
                    if seg["start"] + seg["duration"] <= ext_end:
                        continue
                    nxt_end = seg["start"] + seg["duration"]
                    if nxt_end - start > hi:
                        break
                    ext_text = ext_text + " " + seg["text"]
                    ext_end = nxt_end
                    if ext_end - start >= lo:
                        break
                if lo <= ext_end - start <= hi:
                    best = {"start": start, "end": ext_end, "score": best["score"],
                            "text": ext_text}

            if lo <= best["end"] - best["start"] <= hi:
                windows.append(best)

        windows.sort(key=lambda w: w["score"], reverse=True)

        # Dédoublonnage : on écarte les fenêtres qui chevauchent une fenêtre retenue
        kept = []
        for w in windows:
            if any(not (w["end"] <= k["start"] or w["start"] >= k["end"]) for k in kept):
                continue
            kept.append(w)
            if len(kept) >= top:
                break
        return kept

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    def asset_windows(self, angle: dict, asset: dict, platform: str) -> list[dict]:
        """Fenêtres suggérées pour cet angle sur cet asset (clamp plateforme)."""
        segments = self.loader.segments_for_asset(asset)
        scored = self._score_segments(angle, segments)
        if not scored:
            return []
        lo, hi = self.guard.bounds(platform)
        return self._best_windows(scored, segments, lo, hi)

    def best_asset_for_angle(self, angle: dict, assets: list[dict], platform: str) -> dict:
        """Meilleur asset porteur de l'angle (score fenêtres, strict assets)."""
        best_asset = None
        best_score = 0
        for asset in assets:
            windows = self.asset_windows(angle, asset, platform)
            total = sum(w["score"] for w in windows)
            if total > best_score:
                best_score = total
                best_asset = asset

        if best_asset is not None:
            return best_asset

        # Fallback tracé : transcripts indisponibles -> premier asset "long"
        for asset in assets:
            if asset.get("duration_sec") and float(asset.get("duration_sec")) >= 300:
                return asset
        return assets[0] if assets else {}

    def suggested_segments(self, angle: dict, asset: dict, platform: str,
                           top: int = 3) -> list[dict]:
        """Segments suggérés [start, end, duration, rationale, snippet]."""
        windows = self.asset_windows(angle, asset, platform)[:top]
        emotion = angle.get("emotion_mode", "")
        reframe = angle.get("reframe_dim", "")
        segments = []
        for w in windows:
            start = round(w["start"], 1)
            end = round(w["end"], 1)
            snippet = " ".join(w["text"].split())[:240]
            segments.append({
                "start_sec": start,
                "end_sec": end,
                "duration_sec": round(end - start, 1),
                "rationale": f"Fenetre {w['score']} hit(s) banques '{emotion}' + '{reframe}'",
                "extracted_text_snippet": snippet,
            })
        return segments
