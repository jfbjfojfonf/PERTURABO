"""
libs/readings_validator.py — cohérence des saisies du Warsmith (F06)
===================================================================

Vérifie que chaque saisie manuelle du Warsmith est cohérente avant de
l'enregistrer dans submission_log.json :

  - --post   : pack existe, account non vide, pas déjà posté
  - --views  : entiers >= 0, views_24h >= views_1h (monotonie)
  - --payout : float >= 0

F06 logge ; il ne corrige jamais les saisies. Une saisie incohérente
est refusée avec la liste des raisons.
"""


class ReadingsValidator:
    def validate_post(self, args, pack: dict, log: dict) -> list[str]:
        issues = []
        if not pack:
            issues.append("pack introuvable")
        if not getattr(args, "account", "") or not str(args.account).strip():
            issues.append("account (slug) requis")
        if log.get("campaign_status") != "ongoing":
            issues.append(f"campagne {log.get('campaign_status')} — pas de nouveau post")
        for entry in log.get("packs", []):
            if entry.get("angle_id") == args.angle and entry.get("posted_at"):
                issues.append(f"{args.angle} déjà posté à {entry['posted_at']}")
                break
        return issues

    def validate_views(self, args, entry: dict) -> list[str]:
        issues = []
        try:
            v1h = int(args.v1h)
            v24h = int(args.v24h)
        except (TypeError, ValueError):
            return ["--1h et --24h doivent être des entiers"]
        if v1h < 0 or v24h < 0:
            issues.append("les vues ne peuvent pas être négatives")
        if v24h < v1h:
            issues.append(f"views_24h ({v24h}) < views_1h ({v1h}) — incohérent "
                          f"(les vues ne diminuent pas)")
        if entry.get("views_1h") is not None:
            issues.append("vues déjà enregistrées pour cet angle — saisie refusée")
        return issues

    def validate_payout(self, args, entry: dict) -> list[str]:
        issues = []
        try:
            amount = float(args.amount)
        except (TypeError, ValueError):
            return ["--amount doit être un nombre (float)"]
        if amount < 0:
            issues.append("le payout ne peut pas être négatif")
        if entry.get("payout_observed") is not None:
            issues.append("payout déjà enregistré pour cet angle — saisie refusée")
        return issues
