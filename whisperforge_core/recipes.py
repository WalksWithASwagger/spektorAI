"""Prompt recipe discovery and effective run settings.

Recipes are intentionally small manifests: they name the workflow, declare
expected inputs/stages/outputs, and provide optional defaults for the same
manual controls the Streamlit UI already exposes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

try:
    import yaml
except ImportError:  # pragma: no cover - only in stripped installs
    yaml = None

from .config import PROMPTS_DIR
from .logging import get_logger

logger = get_logger(__name__)

DEFAULT_RECIPES_PATH = Path(__file__).with_name("recipe_defaults.yaml")
MANIFEST_NAME = "profile.yaml"

_SETTING_KEYS = {
    "ai_provider",
    "ai_model",
    "rag_mode",
    "article_length",
    "cleanup_enabled",
    "chapters_enabled",
    "agentic_drafting",
    "fact_check_enabled",
    "images_enabled",
    "auto_save_notion",
    "auto_export_markdown",
}
_DEFAULT_TO_SESSION_KEY = {
    "provider": "ai_provider",
    "model": "ai_model",
    "kb_mode": "rag_mode",
    "rag_mode": "rag_mode",
    "article_length": "article_length",
    "cleanup": "cleanup_enabled",
    "chapters": "chapters_enabled",
    "agentic": "agentic_drafting",
    "fact_check": "fact_check_enabled",
    "images": "images_enabled",
    "auto_save_notion": "auto_save_notion",
    "auto_export_markdown": "auto_export_markdown",
}


@dataclass
class Recipe:
    id: str
    name: str
    description: str = ""
    inputs: list[str] = field(default_factory=list)
    stages: list[str] = field(default_factory=list)
    defaults: dict[str, Any] = field(default_factory=dict)
    output_sections: list[str] = field(default_factory=list)
    eval_checks: list[str] = field(default_factory=list)
    handoff_targets: list[str] = field(default_factory=list)
    source: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "inputs": list(self.inputs),
            "stages": list(self.stages),
            "defaults": dict(self.defaults),
            "output_sections": list(self.output_sections),
            "eval_checks": list(self.eval_checks),
            "handoff_targets": list(self.handoff_targets),
            "source": self.source,
        }


def list_recipes(user: str | None = None) -> dict[str, Recipe]:
    """Return default recipes overlaid by profile-level recipes."""
    recipes = _recipes_from_payload(_read_structured(DEFAULT_RECIPES_PATH), "default")
    if not user:
        return recipes

    user_dir = PROMPTS_DIR / user
    recipes.update(_recipes_from_dir(user_dir / "recipes"))
    recipes.update(_recipes_from_profile_manifest(user_dir))
    return recipes


def get_recipe(user: str | None, recipe_id: str | None) -> Recipe | None:
    if not recipe_id or recipe_id == "manual":
        return None
    return list_recipes(user).get(recipe_id)


def effective_settings(recipe: Recipe, current: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve a recipe against the current manual controls.

    The returned dict is safe to persist into run artifacts. It records the
    active controls after recipe defaults have been applied.
    """
    settings = {
        key: current.get(key)
        for key in _SETTING_KEYS
        if key in current and current.get(key) is not None
    }
    applied_defaults: dict[str, Any] = {}
    for key, value in recipe.defaults.items():
        session_key = _DEFAULT_TO_SESSION_KEY.get(key, key)
        if session_key not in _SETTING_KEYS:
            continue
        settings[session_key] = value
        applied_defaults[session_key] = value
    return {
        "recipe_id": recipe.id,
        "recipe_name": recipe.name,
        "source": recipe.source,
        "settings": settings,
        "applied_defaults": applied_defaults,
        "stages": list(recipe.stages),
        "output_sections": list(recipe.output_sections),
        "eval_checks": list(recipe.eval_checks),
        "handoff_targets": list(recipe.handoff_targets),
    }


def run_metadata(
    recipe_id: str | None,
    recipe: Mapping[str, Any] | None,
    effective: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not recipe_id or recipe_id == "manual":
        return None
    return {
        "recipe_id": recipe_id,
        "recipe": dict(recipe or {}),
        "effective_settings": dict(effective or {}),
    }


def _recipes_from_dir(path: Path) -> dict[str, Recipe]:
    if not path.exists():
        return {}
    loaded: dict[str, Recipe] = {}
    for recipe_path in sorted(path.iterdir()):
        if recipe_path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        payload = _read_structured(recipe_path)
        recipes = _recipes_from_payload(payload, f"profile:{recipe_path.name}", recipe_path.stem)
        loaded.update(recipes)
    return loaded


def _recipes_from_profile_manifest(user_dir: Path) -> dict[str, Recipe]:
    payload = _read_structured(user_dir / MANIFEST_NAME)
    raw = payload.get("recipes") if isinstance(payload, dict) else None
    return _recipes_from_payload({"recipes": raw}, "profile:profile.yaml")


def _recipes_from_payload(
    payload: Mapping[str, Any] | None,
    source: str,
    fallback_id: str | None = None,
) -> dict[str, Recipe]:
    if not isinstance(payload, Mapping):
        return {}
    if fallback_id and "recipes" not in payload:
        raw = payload
        items = [(fallback_id, raw)]
    else:
        raw = payload.get("recipes", payload)
        if isinstance(raw, Mapping):
            items = [(str(key), value) for key, value in raw.items()]
        elif isinstance(raw, list):
            items = [
                (item.get("id") if isinstance(item, Mapping) else None, item)
                for item in raw
            ]
        else:
            items = [(fallback_id, raw)] if fallback_id else []

    recipes: dict[str, Recipe] = {}
    for key, value in items:
        recipe = _normalize_recipe(key or fallback_id, value, source)
        if recipe:
            recipes[recipe.id] = recipe
    return recipes


def _normalize_recipe(recipe_id: str | None, raw: Any, source: str) -> Recipe | None:
    if not isinstance(raw, Mapping):
        return None
    rid = _slug(str(raw.get("id") or recipe_id or raw.get("name") or ""))
    if not rid:
        return None
    name = str(raw.get("name") or rid.replace("_", " ").title())
    defaults = raw.get("defaults") or {}
    if not isinstance(defaults, Mapping):
        defaults = {}
    return Recipe(
        id=rid,
        name=name,
        description=str(raw.get("description") or ""),
        inputs=_string_list(raw.get("inputs")),
        stages=_string_list(raw.get("stages")),
        defaults={str(k): v for k, v in defaults.items()},
        output_sections=_string_list(raw.get("output_sections")),
        eval_checks=_string_list(raw.get("eval_checks")),
        handoff_targets=_string_list(raw.get("handoff_targets")),
        source=source,
    )


def _read_structured(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Failed to read recipe manifest %s: %s", path, e)
        return {}
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse recipe manifest %s: %s", path, e)
            return {}
    else:
        if yaml is None:
            logger.warning("PyYAML is not installed; ignoring %s", path)
            return {}
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            logger.warning("Failed to parse recipe manifest %s: %s", path, e)
            return {}
    return data if isinstance(data, dict) else {}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _slug(value: str) -> str:
    value = value.strip().lower().replace("-", "_").replace(" ", "_")
    return re.sub(r"[^a-z0-9_]+", "", value).strip("_")
