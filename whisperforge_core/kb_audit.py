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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KBWarning:
    code: str
    severity: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KBAudit:
    user: str
    kb_dir: str
    generated_at: str
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
            "documents": [doc.to_dict() for doc in self.documents],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


def audit_profile(user: str, *, now: datetime | None = None) -> KBAudit:
    now = now or datetime.now(timezone.utc)
    kb_dir = PROMPTS_DIR / user / "knowledge_base"
    audit = KBAudit(
        user=user,
        kb_dir=str(kb_dir),
        generated_at=_iso(now),
    )
    if not kb_dir.exists():
        audit.warnings.append(KBWarning(
            code="missing_kb",
            severity="warning",
            message=f"`prompts/{user}/knowledge_base/` does not exist.",
        ))
        return audit

    docs = [_document(path, now) for path in sorted(kb_dir.iterdir()) if _is_kb_file(path)]
    audit.documents = docs
    if not docs:
        audit.warnings.append(KBWarning(
            code="empty_kb",
            severity="warning",
            message=f"`prompts/{user}/knowledge_base/` has no .md or .txt files.",
            path=str(kb_dir),
        ))

    seen_hashes: dict[str, KBDocument] = {}
    for doc in docs:
        if doc.chars == 0:
            audit.warnings.append(KBWarning(
                code="empty_file",
                severity="warning",
                message=f"`{Path(doc.path).name}` is empty.",
                path=doc.path,
            ))
        if doc.chars > _OVERSIZED_CHARS:
            audit.warnings.append(KBWarning(
                code="oversized_file",
                severity="notice",
                message=f"`{Path(doc.path).name}` is large enough that retrieval should be inspected.",
                path=doc.path,
            ))
        if _days_old(doc.modified_at, now) > _STALE_DAYS:
            audit.warnings.append(KBWarning(
                code="stale_file",
                severity="notice",
                message=f"`{Path(doc.path).name}` has not changed in more than {_STALE_DAYS} days.",
                path=doc.path,
            ))
        if any(marker in Path(doc.path).name.lower() for marker in _PRIVATE_MARKERS):
            audit.warnings.append(KBWarning(
                code="private_marker",
                severity="warning",
                message=f"`{Path(doc.path).name}` looks private or credential-adjacent; verify before sharing.",
                path=doc.path,
            ))
        previous = seen_hashes.get(doc.sha256)
        if previous:
            audit.warnings.append(KBWarning(
                code="duplicate_content",
                severity="notice",
                message=f"`{Path(doc.path).name}` duplicates `{Path(previous.path).name}`.",
                path=doc.path,
            ))
        else:
            seen_hashes[doc.sha256] = doc
    return audit


def _document(path: Path, now: datetime) -> KBDocument:
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
    )


def _is_kb_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".md", ".txt"} and not path.name.startswith(".")


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
