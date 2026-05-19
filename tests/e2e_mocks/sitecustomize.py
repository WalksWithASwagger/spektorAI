"""Browser-E2E mock injector.

Streamlit is launched as a subprocess for the fresh-run browser smoke, which
means we cannot use pytest's ``monkeypatch`` to stub out LLM and Notion calls
the way the in-process AppTest does. Instead, we put the directory holding
this file on ``PYTHONPATH``: Python auto-imports ``sitecustomize`` at
interpreter startup, before Streamlit imports the app.

Activated by setting ``WHISPERFORGE_E2E_MOCK=1`` so a stray ``PYTHONPATH``
entry can't ever silently disable real LLM calls in production.

Patching is deferred via an import hook because ``whisperforge_core`` is not
yet importable when sitecustomize runs — Streamlit prepends the repo root to
``sys.path`` later, when it executes ``app.py``.
"""

from __future__ import annotations

import os
import sys
from importlib.abc import Loader, MetaPathFinder
from importlib.util import find_spec
from types import ModuleType, SimpleNamespace


def _patched_modules() -> dict:
    return {"whisperforge_core.adapters": _patch_adapters,
            "whisperforge_core.llm": _patch_llm}


def _patch_adapters(module: ModuleType) -> None:
    from whisperforge_core import pipeline as core_pipeline

    fake_pipeline_result = core_pipeline.PipelineResult(
        wisdom="E2E mock: a grounded insight from the fresh-run smoke.",
        outline="1. Hook\n2. Body\n3. Close",
        social_posts="LinkedIn: ship the deadline, not the curriculum.",
        image_prompts="Wide bright workshop scene, documentary feel.",
        article=(
            "# Fresh-run E2E smoke article\n\n"
            "The fresh-run browser smoke executes the full paste -> recipe -> "
            "review -> export loop without hitting any real LLM provider."
        ),
        chapters=[{"title": "Intro", "summary": "Start", "start_seconds": 0}],
    )

    def fake_run_pipeline(transcript, provider, model, **kwargs):
        progress = kwargs.get("progress")
        checkpoint = kwargs.get("checkpoint")
        if progress:
            progress(0.3, "Extracting wisdom...")
            progress(1.0, "Done")
        if checkpoint:
            checkpoint("wisdom", {"wisdom": fake_pipeline_result.wisdom})
        return fake_pipeline_result

    fake_adapters = module.Adapters(
        transcriber=SimpleNamespace(
            transcribe=lambda *_a, **_k: "",
            transcribe_detailed=lambda *_a, **_k: None,
        ),
        processor=SimpleNamespace(
            generate=lambda *_a, **_k: "",
            run_pipeline=fake_run_pipeline,
        ),
        storage=SimpleNamespace(
            save=lambda *_a, **_k: "https://notion.so/e2e-mock",
        ),
    )
    module.get_adapters = lambda: fake_adapters


def _patch_llm(module: ModuleType) -> None:
    module.generate_title = lambda *_a, **_k: "E2E Fresh Run"
    module.generate_summary = lambda *_a, **_k: "E2E smoke summary."
    module.generate_tags = lambda *_a, **_k: ["e2e-smoke"]
    module.generate = lambda *_a, **_k: ""


class _WhisperforgePatcher(MetaPathFinder):
    """Lets the default machinery import the target module, then patches it."""

    def __init__(self) -> None:
        self._targets = _patched_modules()
        self._busy: set[str] = set()

    def find_spec(self, fullname, path, target=None):
        if fullname not in self._targets or fullname in self._busy:
            return None
        self._busy.add(fullname)
        try:
            spec = find_spec(fullname)
        finally:
            self._busy.discard(fullname)
        if spec is None or spec.loader is None:
            return None
        original_loader = spec.loader
        patch = self._targets[fullname]

        class _Wrapped(Loader):
            def create_module(self, spec):
                if hasattr(original_loader, "create_module"):
                    return original_loader.create_module(spec)
                return None

            def exec_module(self, module):
                original_loader.exec_module(module)
                try:
                    patch(module)
                except Exception as exc:  # pragma: no cover - debug aid
                    sys.stderr.write(
                        f"[e2e-mock] failed to patch {fullname}: {exc}\n"
                    )

        spec.loader = _Wrapped()
        return spec


def _install() -> None:
    if os.environ.get("WHISPERFORGE_E2E_MOCK") != "1":
        return
    # If our finder is already on the path (e.g. duplicated PYTHONPATH entry),
    # skip — re-adding would patch twice.
    for finder in sys.meta_path:
        if isinstance(finder, _WhisperforgePatcher):
            return
    sys.meta_path.insert(0, _WhisperforgePatcher())


_install()
