"""User-scoped prompt and knowledge-base discovery.

Layout:
    prompts/<user>/
        prompts/*.md         -- prompt templates by name
        knowledge_base/*.md  -- voice/style context
        custom_prompts/*.txt -- per-type overrides (e.g. wisdom_extraction.txt)

Paths are anchored via config.PROMPTS_DIR (project root / "prompts") so they
work regardless of cwd — important because FastAPI services run from /app
while streamlit runs from the project directory.
"""

from pathlib import Path
from typing import Dict, List, Tuple

from .config import DEFAULT_PROMPTS, PROMPTS_DIR
from .logging import get_logger

logger = get_logger(__name__)


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
    return prompts


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
