"""Knowledge-base inventory and conservative health checks."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import PROMPTS_DIR

_CHARS_PER_TOKEN = 4
_OVERSIZED_CHARS = 25_000
_STALE_DAYS = 180
_PRIVATE_MARKERS = ("private", "secret", "credential", "token", "password", "confidential")
_GOVERNANCE_FILES = ("governance.yaml", "kb_governance.yaml")
_GENERATION_WARNING_CODES = {
    "duplicate_content",
    "oversized_file",
    "private_marker",
    "stale_file",
}

try:
    import yaml
except ImportError:  # pragma: no cover - only exercised in stripped installs
    yaml = None


@dataclass
class KBGovernance:
    canonical_files: list[str] = field(default_factory=list)
    ignored_files: list[str] = field(default_factory=list)

    def is_canonical(self, path: str | Path) -> bool:
        return _name(path) in _normalized_names(self.canonical_files)

    def is_ignored(self, path: str | Path) -> bool:
        return _name(path) in _normalized_names(self.ignored_files)

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "canonical_files": list(self.canonical_files),
            "ignored_files": list(self.ignored_files),
        }


@dataclass
class KBDocument:
    name: str
    path: str
    suffix: str
    role: str
    size_bytes: int
    chars: int
    approx_tokens: int
    modified_at: str
    sha256: str
    canonical: bool = False
    ignored: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KBWarning:
    code: str
    severity: str
    message: str
    path: str | None = None
    action: str = "review"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KBAudit:
    user: str
    kb_dir: str
    generated_at: str
    governance: KBGovernance = field(default_factory=KBGovernance)
    documents: list[KBDocument] = field(default_factory=list)
    warnings: list[KBWarning] = field(default_factory=list)

    @property
    def total_chars(self) -> int:
        return sum(doc.chars for doc in self.documents)

    @property
    def total_tokens(self) -> int:
        return sum(doc.approx_tokens for doc in self.documents)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "kb_dir": self.kb_dir,
            "generated_at": self.generated_at,
            "summary": {
                "documents": len(self.documents),
                "chars": self.total_chars,
                "approx_tokens": self.total_tokens,
                "warnings": len(self.warnings),
            },
            "governance": self.governance.to_dict(),
            "documents": [doc.to_dict() for doc in self.documents],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


def load_governance(user: str, *, prompts_dir: Path | None = None) -> KBGovernance:
    root = prompts_dir or PROMPTS_DIR
    kb_dir = root / user / "knowledge_base"
    path = _governance_path(kb_dir)
    if path is None:
        return KBGovernance()
    data = _read_governance(path)
    return KBGovernance(
        canonical_files=_string_list(
            data.get("canonical_files")
            or data.get("canonical_voice_anchors")
            or data.get("canonical")
        ),
        ignored_files=_string_list(
            data.get("ignored_files")
            or data.get("ignored")
            or data.get("exclude")
        ),
    )


def save_governance(
    user: str,
    *,
    canonical_files: list[str],
    ignored_files: list[str],
    prompts_dir: Path | None = None,
) -> Path:
    root = prompts_dir or PROMPTS_DIR
    kb_dir = root / user / "knowledge_base"
    kb_dir.mkdir(parents=True, exist_ok=True)
    path = kb_dir / _GOVERNANCE_FILES[0]
    lines = [
        "# WhisperForge KB governance.",
        "# canonical_files are prioritized and labeled in prompts.",
        "# ignored_files are excluded from generation but remain visible in audits.",
        "canonical_files:",
    ]
    lines.extend(f"  - {item}" for item in _dedupe_names(canonical_files))
    lines.append("ignored_files:")
    lines.extend(f"  - {item}" for item in _dedupe_names(ignored_files))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def audit_profile(
    user: str,
    *,
    now: datetime | None = None,
    prompts_dir: Path | None = None,
) -> KBAudit:
    now = now or datetime.now(timezone.utc)
    root = prompts_dir or PROMPTS_DIR
    kb_dir = root / user / "knowledge_base"
    governance = load_governance(user, prompts_dir=root)
    audit = KBAudit(
        user=user,
        kb_dir=str(kb_dir),
        generated_at=_iso(now),
        governance=governance,
    )
    if not kb_dir.exists():
        audit.warnings.append(KBWarning(
            code="missing_kb",
            severity="warning",
            message=f"`prompts/{user}/knowledge_base/` does not exist.",
            action="Create a knowledge_base folder or pick another profile.",
        ))
        return audit

    docs = [
        _document(path, now, governance)
        for path in sorted(kb_dir.iterdir())
        if _is_kb_file(path)
    ]
    audit.documents = docs
    if not docs:
        audit.warnings.append(KBWarning(
            code="empty_kb",
            severity="warning",
            message=f"`prompts/{user}/knowledge_base/` has no .md or .txt files.",
            path=str(kb_dir),
            action="Upload .md or .txt context files before expecting in-voice output.",
        ))

    seen_hashes: dict[str, KBDocument] = {}
    for doc in docs:
        if doc.ignored:
            audit.warnings.append(KBWarning(
                code="ignored_file",
                severity="notice",
                message=f"`{Path(doc.path).name}` is intentionally ignored by KB governance.",
                path=doc.path,
                action="Excluded from generation.",
            ))
            continue
        if doc.chars == 0:
            audit.warnings.append(KBWarning(
                code="empty_file",
                severity="warning",
                message=f"`{Path(doc.path).name}` is empty.",
                path=doc.path,
                action="Delete it, replace it, or add it to ignored_files.",
            ))
        if doc.chars > _OVERSIZED_CHARS:
            audit.warnings.append(KBWarning(
                code="oversized_file",
                severity="notice",
                message=f"`{Path(doc.path).name}` is large enough that retrieval should be inspected.",
                path=doc.path,
                action="Inspect retrieval coverage or split it before relying on generation.",
            ))
        if _days_old(doc.modified_at, now) > _STALE_DAYS:
            audit.warnings.append(KBWarning(
                code="stale_file",
                severity="notice",
                message=f"`{Path(doc.path).name}` has not changed in more than {_STALE_DAYS} days.",
                path=doc.path,
                action="Review freshness, mark canonical if still true, or ignore it.",
            ))
        if any(marker in Path(doc.path).name.lower() for marker in _PRIVATE_MARKERS):
            audit.warnings.append(KBWarning(
                code="private_marker",
                severity="warning",
                message=f"`{Path(doc.path).name}` looks private or credential-adjacent; verify before sharing.",
                path=doc.path,
                action="Keep local, rename after review, or add it to ignored_files.",
            ))
        previous = seen_hashes.get(doc.sha256)
        if previous:
            audit.warnings.append(KBWarning(
                code="duplicate_content",
                severity="notice",
                message=f"`{Path(doc.path).name}` duplicates `{Path(previous.path).name}`.",
                path=doc.path,
                action="Keep one canonical source and ignore the duplicate.",
            ))
        else:
            seen_hashes[doc.sha256] = doc
    return audit


def generation_warnings(
    user: str,
    *,
    now: datetime | None = None,
    prompts_dir: Path | None = None,
) -> list[KBWarning]:
    audit = audit_profile(user, now=now, prompts_dir=prompts_dir)
    return [
        warning for warning in audit.warnings
        if warning.code in _GENERATION_WARNING_CODES
    ]


def generation_warning_summary(
    user: str,
    *,
    now: datetime | None = None,
    prompts_dir: Path | None = None,
    limit: int = 3,
) -> str:
    warnings = generation_warnings(user, now=now, prompts_dir=prompts_dir)
    if not warnings:
        return ""
    shown = warnings[:limit]
    parts = [
        f"{Path(warning.path).name if warning.path else warning.code}: {warning.action}"
        for warning in shown
    ]
    remaining = len(warnings) - len(shown)
    suffix = f"; +{remaining} more" if remaining else ""
    return f"{len(warnings)} unresolved KB governance finding(s): " + "; ".join(parts) + suffix


def _document(path: Path, now: datetime, governance: KBGovernance) -> KBDocument:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    stat = path.stat()
    return KBDocument(
        name=path.stem,
        path=str(path),
        suffix=path.suffix.lower(),
        role=_role(path),
        size_bytes=stat.st_size,
        chars=len(text),
        approx_tokens=max(1, len(text) // _CHARS_PER_TOKEN) if text else 0,
        modified_at=_iso(datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)),
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        canonical=governance.is_canonical(path),
        ignored=governance.is_ignored(path),
    )


def _is_kb_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".md", ".txt"} and not path.name.startswith(".")


def _governance_path(kb_dir: Path) -> Path | None:
    for filename in _GOVERNANCE_FILES:
        path = kb_dir / filename
        if path.exists():
            return path
    return None


def _read_governance(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if yaml is not None:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            data = {}
        return data if isinstance(data, dict) else {}
    return _read_simple_yaml(text)


def _read_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.endswith(":"):
            current = line[:-1].strip()
            data.setdefault(current, [])
            continue
        if current and line.startswith("-"):
            data[current].append(line[1:].strip().strip("'\""))
    return data


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _dedupe_names(values: list[str]) -> list[str]:
    seen: set[str] = set()
    names: list[str] = []
    for value in values:
        item = _name(value)
        if not item or item in seen:
            continue
        seen.add(item)
        names.append(item)
    return names


def _normalized_names(values: list[str]) -> set[str]:
    return {_name(value) for value in values}


def _name(path: str | Path) -> str:
    return Path(str(path)).name.lower()


def _role(path: Path) -> str:
    name = path.stem.lower()
    if any(token in name for token in ("voice", "style", "tone", "writing")):
        return "voice"
    if any(token in name for token in ("worldview", "belief", "principle")):
        return "worldview"
    if any(token in name for token in ("goal", "dream", "plan", "roadmap")):
        return "goals"
    if any(token in name for token in ("bio", "background", "dossier", "profile")):
        return "background"
    return "context"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _days_old(modified_at: str, now: datetime) -> int:
    try:
        modified = datetime.strptime(modified_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return 0
    return max(0, (now - modified).days)
