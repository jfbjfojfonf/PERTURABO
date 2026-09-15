"""Tests F06_DIRECTOR — mode caviar_bound (F00D commande, F06 exécute le reste).

Doctrine validée par l'opérateur :
- la partition caviar possède cuts, zooms, SFX, miroir/vitesse/crop,
  le rendu des panneaux et le duck audio ;
- F06 garde text_overlays, courbe d'énergie recalée, hiérarchie audio,
  outro fade/pas de CTA, compliance, anti-détection complémentaire ;
- hook : la partition gagne (panneau à ~0s => panel_at_zero) ;
- style blur sans manifeste => erreur, jamais de fallback silencieux ;
- mode legacy (sans caviar) : inchangé.
"""
import json
import sys
from pathlib import Path

import pytest

CODEBASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODEBASE))

import director  # noqa: E402

CAVIAR_V2 = (CODEBASE.parent.parent.parent.parent / "docs" / "data" / "caviar"
             / "caviar_manifest_voxc2_blur.json")

SEG = {"id": "A01", "source_url": "https://www.youtube.com/watch?v=cP8vli4kfhs",
       "start_sec": 153.9, "end_sec": 205.2, "duration_sec": 51.3,
       "signal_type": "platform_heat", "signal_intensity": 0.892}
TEXT = {"overlay_title": "She makes MORE than LeBron James?\nTop 0.1% OF earner speaks out",
        "overlay_lines": 2}
CTX = {"platform": "youtube_shorts", "market": "us_young_english", "angle_id": "A01"}


@pytest.fixture()
def caviar():
    return json.loads(CAVIAR_V2.read_text(encoding="utf-8"))


def _bound(caviar):
    return director.generate_montage_instructions(
        SEG, TEXT, CTX, caviar_manifest=caviar,
        caviar_manifest_path=str(CAVIAR_V2))


class TestCaviarBound:
    def test_mode_and_metadata(self, caviar):
        out = _bound(caviar)
        assert out["metadata"]["mode"] == "caviar_bound"
        assert out["metadata"]["version"] == "3.0.0-caviar-bound"
        assert out["metadata"]["style"] == "blur"

    def test_no_cuts_no_zooms_no_sfx(self, caviar):
        """F00D possède le geste : F06 n'émet AUCUN cut, zoom ni SFX."""
        out = _bound(caviar)
        assert out["body"]["cuts"] == []
        assert out["body"]["zooms"] == []
        assert out["body"]["audio"]["sfx_events"] == []

    def test_panels_extracted_with_ownership(self, caviar):
        out = _bound(caviar)
        panels = out["body"]["panels"]
        assert len(panels) == 2
        ids = [p["panel_id"] for p in panels]
        assert ids == ["BLUR-01", "BLUR-02"]
        for p in panels:
            assert p["owned_by"] == "caviar"
            assert p["crop_zoom"] == 1.3
            assert p["blur_radius_px"] == 18
            # doctrine trio : SFX seulement si flash d'entrée
            assert (p["sfx"] == "impact") == bool(p["entry_flash"])

    def test_audio_duck_at_caviar_climax(self, caviar):
        out = _bound(caviar)
        duck = out["body"]["audio_duck"]
        assert duck and duck[0]["at_sec"] == pytest.approx(28.216)
        assert duck[0]["duck_db"] == -12
        assert duck[0]["owned_by"] == "caviar"

    def test_energy_curve_anchored_to_climax(self, caviar):
        out = _bound(caviar)
        curve = out["body"]["energy_curve"]
        phases = [c["phase"] for c in curve if "phase" in c]
        assert phases == ["rise", "peak", "fall"]
        anchor = [c for c in curve if c.get("note") == "climax_caviar_at_sec"]
        assert anchor and anchor[0]["value"] == pytest.approx(28.216)

    def test_binding_traceability(self, caviar):
        out = _bound(caviar)
        b = out["caviar_binding"]
        assert b["bound"] is True
        assert b["run_id"] == "f00c_2026-09-14T134014.262908+0000"
        assert b["candidate_id"] == "voxc-2"
        assert len(b["manifest_sha256_16"]) == 16

    def test_f04_overlay_carried(self, caviar):
        out = _bound(caviar)
        title = out["body"]["text_overlays"]["main_title"]["text"]
        assert "LeBron James" in title

    def test_anti_detection_complementary_only(self, caviar):
        out = _bound(caviar)
        ad = out["anti_detection"]
        names = {t["name"] for t in ad["techniques"]}
        assert names == {"sfx_background_layer", "color_shift", "trim"}
        assert set(ad["owned_by_caviar"]) == {"mirror", "speed", "crop"}

    def test_outro_and_compliance(self, caviar):
        out = _bound(caviar)
        assert out["outro"]["type"] == "fade_to_black"
        assert "CTA" in out["outro"]["note"]
        assert out["compliance"]["disclosure"] == "#ad"

    def test_hook_partition_wins_when_panel_at_zero(self):
        """Panneau posé à ~0s => la philosophie « visage d'abord » s'efface."""
        caviar = json.loads(CAVIAR_V2.read_text(encoding="utf-8"))
        caviar["events"]["broll"][0]["start_sec"] = 0.0
        out = director.generate_montage_instructions(
            SEG, TEXT, CTX, caviar_manifest=caviar)
        assert out["hook"]["panel_at_zero"] is True
        assert "partition gagne" in out["hook"]["philosophy"]

    def test_hook_legacy_when_first_panel_late(self, caviar):
        out = _bound(caviar)
        assert out["hook"]["panel_at_zero"] is False
        assert "visage speaker" in out["hook"]["philosophy"]


class TestGuards:
    def test_blur_without_caviar_raises(self):
        """Style blur sans partition => erreur claire, pas de fallback."""
        with pytest.raises(ValueError, match="caviar_manifest"):
            director.generate_montage_instructions(
                SEG, TEXT, {"platform": "youtube_shorts", "style": "blur"})

    def test_legacy_mode_unchanged(self):
        """Sans caviar : comportement 2.0 intact (cuts, zooms, SFX)."""
        out = director.generate_montage_instructions(
            SEG, TEXT, CTX)
        assert "mode" not in out["metadata"]
        assert out["metadata"]["version"] == "2.0.0-viral"
        assert len(out["body"]["cuts"]) > 0
        assert len(out["body"]["zooms"]) > 0
        assert len(out["body"]["audio"]["sfx_events"]) == 4
        assert len(out["anti_detection"]["techniques"]) == 6
