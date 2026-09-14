"""
libs/schema_validator.py — validation pack contre le schéma canonique
=====================================================================

Valide un production_pack contre `CONTRACTS/production_pack_schema.json`
(JSON Schema draft-07 — contrat d'interface avec OMNIS_WATCH).

Implémentation stdlib du sous-ensemble utilisé par les schémas canoniques :
  - type (y compris union ["string","null"])
  - required / properties (récursif)
  - additionalProperties: false (rejette les clés inconnues)
  - enum / const
  - minItems / maxItems / contains
  - minimum / maximum
  - minLength / maxLength

Renvoie une liste de {path, message}. Retour vide = pack conforme.
Le schéma est figé des deux côtés (PERTURABO ↔ OMNIS_WATCH) : toute
modification doit être coordonnée.
"""

import json
import os
import re


class SchemaValidator:
    def __init__(self, schema_path: str):
        with open(schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)

    # ------------------------------------------------------------------
    def validate(self, instance, root: str = "production_pack") -> list[str]:
        issues = []
        self._check(instance, self.schema, root, issues)
        return issues

    # ------------------------------------------------------------------
    def _check(self, value, schema: dict, path: str, issues: list[str]):
        if schema is None:
            return
        if "type" in schema and not self._matches_type(value, schema["type"]):
            issues.append(f"{path}: type {schema['type']} attendu, "
                          f"reçu {type(value).__name__}")
            return
        if "enum" in schema and value not in schema["enum"]:
            issues.append(f"{path}: valeur '{value}' hors enum {schema['enum']}")
        if "const" in schema and value != schema["const"]:
            issues.append(f"{path}: const '{schema['const']}' requis, "
                          f"reçu '{value}'")
        if isinstance(value, str):
            if "pattern" in schema:
                try:
                    if re.search(schema["pattern"], value) is None:
                        issues.append(f"{path}: ne matche pas le pattern "
                                      f"'{schema['pattern']}'")
                except re.error:
                    issues.append(f"{path}: pattern invalide "
                                  f"'{schema['pattern']}'")
            if "minLength" in schema and len(value) < schema["minLength"]:
                issues.append(f"{path}: minLength {schema['minLength']} violé "
                              f"({len(value)} chars)")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                issues.append(f"{path}: maxLength {schema['maxLength']} dépassé "
                              f"({len(value)} chars)")
        if isinstance(value, dict):
            if schema.get("additionalProperties") is False:
                allowed = set(schema.get("properties", {}).keys())
                for key in value:
                    if key not in allowed:
                        issues.append(f"{path}: propriété inconnue '{key}' "
                                      f"(additionalProperties: false)")
            for req in schema.get("required", []):
                if req not in value:
                    issues.append(f"{path}: propriété requise manquante '{req}'")
            for prop, prop_schema in schema.get("properties", {}).items():
                if prop in value:
                    self._check(value[prop], prop_schema,
                                f"{path}.{prop}", issues)
        elif isinstance(value, list):
            items_schema = schema.get("items")
            if items_schema is not None:
                for i, item in enumerate(value):
                    self._check(item, items_schema, f"{path}[{i}]", issues)
            if "minItems" in schema and len(value) < schema["minItems"]:
                issues.append(f"{path}: minItems {schema['minItems']} requis, "
                              f"reçu {len(value)}")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                issues.append(f"{path}: maxItems {schema['maxItems']} dépassé, "
                              f"reçu {len(value)}")
            if "contains" in schema:
                contains = schema["contains"]
                ok = any(item == contains.get("const")
                         for item in value) if "const" in contains else False
                if not ok:
                    issues.append(f"{path}: contains '{contains.get('const')}' "
                                  f"requis dans la liste")
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                issues.append(f"{path}: minimum {schema['minimum']} violé "
                              f"({value})")
            if "maximum" in schema and value > schema["maximum"]:
                issues.append(f"{path}: maximum {schema['maximum']} violé "
                              f"({value})")

    def _matches_type(self, value, type_spec) -> bool:
        types = type_spec if isinstance(type_spec, list) else [type_spec]
        for t in types:
            if t == "object" and isinstance(value, dict):
                return True
            if t == "array" and isinstance(value, list):
                return True
            if t == "string" and isinstance(value, str):
                return True
            if t == "boolean" and isinstance(value, bool):
                return True
            if t == "integer" and isinstance(value, int) and not isinstance(value, bool):
                return True
            if t == "number" and isinstance(value, (int, float)) \
                    and not isinstance(value, bool):
                return True
            if t == "null" and value is None:
                return True
        return False
