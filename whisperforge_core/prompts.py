"""User-scoped prompt and knowledge-base discovery.

Layout:
    prompts/<user>/
        profile.yaml        -- optional profile manifest
        prompts/*.md         -- prompt templates by name
        knowledge_base/*.md  -- voice/style context
        personas/*.md        -- user-defined persona directives
        custom_prompts/*.txt -- per-type overrides (e.g. wisdom_extraction.txt)

Paths are anchored via config.PROMPTS_DIR (project root / "prompts") so they
work regardless of cwd — important because FastAPI services run from /app
while streamlit runs from the project directory.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only in stripped installs
    yaml = None

from .config import DEFAULT_PROMPTS, PERSONAS, PROMPTS_DIR
from .logging import get_logger

logger = get_logger(__name__)

MANIFEST_NAME = "profile.yaml"
SUPPORTED_PROFILE_DEFAULTS = {
    "provider", "model", "kb_mode", "rag_mode", "article_length", "cleanup",
    "chapters", "agentic", "fact_check", "images", "auto_save_notion",
    "auto_export_markdown",
}


def list_users() -> List[str]:
    """Return sorted usernames found under prompts/. Creates the directory if
    missing. If there are no users yet, returns ['default_user']."""
    if not PROMPTS_DIR.exists():
        PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
        (PROMPTS_DIR / "default_user").mkdir(exist_ok=True)
        return ["default_user"]

    users = sorted(
        p.name for p in PROMPTS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )
    return users or ["default_user"]


def load_knowledge_base(user: str) -> Dict[str, str]:
    """Load every .txt/.md file under prompts/<user>/knowledge_base/ and return
    a dict of {TitleCased name: file contents}."""
    kb: Dict[str, str] = {}
    kb_path = PROMPTS_DIR / user / "knowledge_base"
    if not kb_path.exists():
        return kb
    for path in sorted(kb_path.iterdir()):
        if path.suffix.lower() not in {".txt", ".md"} or path.name.startswith("."):
            continue
        name = path.stem.replace("_", " ").title()
        try:
            kb[name] = path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("Failed to read kb file %s: %s", path, e)
    return kb


def load_user_prompts(user: str) -> Dict[str, str]:
    """Load prompt .md files directly under prompts/<user>/ into a dict keyed
    by filename stem (e.g. 'wisdom_extraction' -> template text)."""
    prompts: Dict[str, str] = {}
    user_dir = PROMPTS_DIR / user
    if not user_dir.exists():
        return prompts
    for path in sorted(user_dir.glob("*.md")):
        try:
            prompts[path.stem] = path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("Failed to read prompt %s: %s", path, e)
    # Overlay custom_prompts/*.txt — these win over the .md defaults.
    custom_dir = user_dir / "custom_prompts"
    if custom_dir.exists():
        for path in sorted(custom_dir.glob("*.txt")):
            try:
                prompts[path.stem] = path.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning("Failed to read custom prompt %s: %s", path, e)
    prompts.update(_manifest_prompts(user_dir, load_profile_manifest(user)))
    return prompts


def load_profile_manifest(user: str) -> Dict[str, Any]:
    """Load optional prompts/<user>/profile.yaml metadata.

    Existing profile directories do not need a manifest; missing or empty
    manifests resolve to {}.
    """
    manifest_path = PROMPTS_DIR / user / MANIFEST_NAME
    if not manifest_path.exists():
        return {}
    if yaml is None:
        logger.warning("PyYAML is not installed; ignoring %s", manifest_path)
        return {}
    try:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        logger.warning("Failed to parse profile manifest %s: %s", manifest_path, e)
        return {}
    if data is None:
        return {}
    if not isinstance(data, dict):
        logger.warning("Profile manifest %s must be a mapping", manifest_path)
        return {}
    return data


def load_profile(user: str) -> Dict[str, Any]:
    """Return the prompt-layer view of a profile, including manifest overlays."""
    manifest = load_profile_manifest(user)
    profile_os = load_profile_os(user, manifest=manifest)
    return {
        "user": user,
        "display_name": str(
            manifest.get("display_name") or manifest.get("name") or user
        ),
        "manifest": manifest,
        "profile_os": profile_os,
        "prompts": load_user_prompts(user),
        "knowledge_base": load_knowledge_base(user),
        "personas": list_personas(user),
    }


def load_profile_os(user: str, *, manifest: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return additive profile operating-system metadata.

    Missing fields resolve to empty values so existing profiles keep working.
    """
    manifest = manifest if manifest is not None else load_profile_manifest(user)
    return {
        "user": user,
        "display_name": str(manifest.get("display_name") or manifest.get("name") or user),
        "project": _mapping(manifest.get("project")),
        "defaults": _mapping(manifest.get("defaults")),
        "kb_packs": _kb_packs(manifest.get("kb_packs")),
        "style_rules": _string_list(manifest.get("style_rules")),
        "privacy": _mapping(manifest.get("privacy")),
        "handoff_targets": _string_list(manifest.get("handoff_targets")),
        "recipes": manifest.get("recipes") if isinstance(manifest.get("recipes"), dict) else {},
        "validation": validate_profile_manifest(user, manifest=manifest),
    }


def profile_summary(user: str) -> str:
    profile = load_profile_os(user)
    validation = profile["validation"]
    lines = [
        f"Profile: {profile['display_name']}",
        f"Project: {profile['project'].get('name') or 'not set'}",
        f"Defaults: {_csv(profile['defaults'].keys())}",
        f"KB packs: {_csv(pack['name'] for pack in profile['kb_packs'])}",
        f"Handoff targets: {_csv(profile['handoff_targets'])}",
        f"Privacy: {_csv(profile['privacy'].values())}",
        f"Validation: {len(validation)} issue(s)",
    ]
    return "\n".join(lines)


def validate_profile_manifest(
    user: str,
    *,
    manifest: Dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    manifest = manifest if manifest is not None else load_profile_manifest(user)
    user_dir = PROMPTS_DIR / user
    issues: list[dict[str, str]] = []
    for key in _mapping(manifest.get("defaults")):
        if key not in SUPPORTED_PROFILE_DEFAULTS:
            issues.append(_issue("unsupported_default", f"defaults.{key}", f"Unsupported profile default `{key}`."))
    recipes = manifest.get("recipes")
    if isinstance(recipes, dict):
        for recipe_id, recipe in recipes.items():
            defaults = _mapping(recipe.get("defaults") if isinstance(recipe, dict) else None)
            for key in defaults:
                if key not in SUPPORTED_PROFILE_DEFAULTS:
                    issues.append(_issue("unsupported_default", f"recipes.{recipe_id}.defaults.{key}", f"Unsupported recipe default `{key}`."))
    for label, rel_path in _referenced_files(manifest):
        if not (user_dir / rel_path).exists():
            issues.append(_issue("missing_file", label, f"Referenced file `{rel_path}` is missing."))
    return issues


def list_personas(user: str | None = None) -> Dict[str, str]:
    """Return built-in personas plus optional user-defined persona directives."""
    personas = dict(PERSONAS)
    if not user:
        return personas

    user_dir = PROMPTS_DIR / user
    personas_dir = user_dir / "personas"
    if personas_dir.exists():
        for path in sorted(personas_dir.glob("*.md")):
            try:
                personas[path.stem] = path.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning("Failed to read persona %s: %s", path, e)

    personas.update(_manifest_personas(user_dir, load_profile_manifest(user)))
    return personas


def _manifest_prompts(user_dir: Path, manifest: Dict[str, Any]) -> Dict[str, str]:
    raw_prompts = manifest.get("prompts", {})
    if not isinstance(raw_prompts, dict):
        return {}
    loaded: Dict[str, str] = {}
    for key, value in raw_prompts.items():
        text = _manifest_text(user_dir, value)
        if text is not None:
            loaded[str(key)] = text
    return loaded


def _manifest_personas(user_dir: Path, manifest: Dict[str, Any]) -> Dict[str, str]:
    raw_personas = manifest.get("personas", {})
    loaded: Dict[str, str] = {}
    if isinstance(raw_personas, dict):
        items = raw_personas.items()
    elif isinstance(raw_personas, list):
        items = (
            (item.get("name"), item)
            for item in raw_personas
            if isinstance(item, dict) and item.get("name")
        )
    else:
        return loaded

    for name, value in items:
        text = _manifest_text(user_dir, value)
        if text is not None:
            loaded[str(name)] = text
    return loaded


def _manifest_text(user_dir: Path, value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    for key in ("content", "directive", "prompt", "template"):
        text = value.get(key)
        if isinstance(text, str):
            return text
    file_value = value.get("file") or value.get("path")
    if not isinstance(file_value, str):
        return None
    path = user_dir / file_value
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Failed to read manifest file %s: %s", path, e)
        return None


def _referenced_files(manifest: Dict[str, Any]) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for group in ("prompts", "personas"):
        raw = manifest.get(group)
        if isinstance(raw, dict):
            for key, value in raw.items():
                if isinstance(value, dict):
                    rel = value.get("file") or value.get("path")
                    if isinstance(rel, str):
                        refs.append((f"{group}.{key}", rel))
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    rel = item.get("file") or item.get("path")
                    name = item.get("name") or rel or group
                    if isinstance(rel, str):
                        refs.append((f"{group}.{name}", rel))
    for pack in _kb_packs(manifest.get("kb_packs")):
        for rel in pack["files"]:
            refs.append((f"kb_packs.{pack['name']}", rel))
    return refs


def _kb_packs(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, list):
        items = ((item.get("name"), item) for item in value if isinstance(item, dict))
    else:
        return []
    packs = []
    for name, raw in items:
        if not isinstance(raw, dict):
            continue
        files = _string_list(raw.get("files") or raw.get("paths") or raw.get("file") or raw.get("path"))
        packs.append({
            "name": str(name or raw.get("name") or "kb_pack"),
            "description": str(raw.get("description") or ""),
            "files": files,
        })
    return packs


def _mapping(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _issue(kind: str, path: str, message: str) -> dict[str, str]:
    return {"kind": kind, "path": path, "message": message}


def _csv(values) -> str:
    items = [str(value) for value in values if str(value)]
    return ", ".join(items) if items else "none"


def load_all_users() -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """Discover every user and their prompt set. Returns (users, {user: prompts})."""
    users = list_users()
    all_prompts = {user: load_user_prompts(user) for user in users}
    return users, all_prompts


def get_prompt(user: str, content_type: str, users_prompts: Dict[str, Dict[str, str]]) -> str:
    """Return the prompt text for (user, content_type), falling back to DEFAULT_PROMPTS."""
    user_prompts = users_prompts.get(user, {}) if isinstance(users_prompts, dict) else {}
    if not isinstance(user_prompts, dict):
        return DEFAULT_PROMPTS.get(content_type, "")
    return user_prompts.get(content_type, DEFAULT_PROMPTS.get(content_type, ""))


def save_custom_prompt(user: str, content_type: str, content: str) -> bool:
    """Persist a per-user override to prompts/<user>/custom_prompts/<type>.txt."""
    target_dir = PROMPTS_DIR / user / "custom_prompts"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{content_type}.txt"
    try:
        target.write_text(content, encoding="utf-8")
        return True
    except OSError as e:
        logger.error("Failed to save custom prompt %s: %s", target, e)
        return False


def list_knowledge_base_files(user: str) -> List[Path]:
    """Return a list of paths for all kb files for a user (absolute Paths)."""
    kb_path = PROMPTS_DIR / user / "knowledge_base"
    if not kb_path.exists():
        return []
    return sorted(
        p for p in kb_path.iterdir()
        if p.suffix.lower() in {".txt", ".md"} and not p.name.startswith(".")
    )
