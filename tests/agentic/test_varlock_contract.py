from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".env.schema"
FIXTURE = ROOT / "tests" / "agentic" / "fixtures" / "varlock" / "shared"
VARLOCK = shutil.which("varlock")
SANITIZED_VALUE = "fixture-varlock-redaction-proof"
SHARED_NAMES = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "NOTION_API_KEY",
    "NOTION_DATABASE_ID",
    "GOOGLE_API_KEY",
    "LINEAR_API_KEY",
    "WHISPERX_HF_TOKEN",
    "HF_TOKEN",
)
RUNTIME_ROOTS = {
    "app.py",
    "services",
    "shared",
    "scripts",
    "styles.py",
    "ui",
    "whisperforge.py",
    "whisperforge_core",
}
EXCLUDED_PARTS = {
    ".venv",
    "ENV",
    "archive",
    "archives",
    "backups",
    "build",
    "dist",
    "fixtures",
    "generated",
    "tests",
    "venv",
    "whisperforge-env",
}
INDIRECT_RUNTIME_NAMES = {
    "AGENTIC_PROVIDER_COMMAND",
    "WF_RAG",
    "WHISPERFORGE_E2E_FIXTURE_PATH",
}
VARLOCK_AUDIT_IGNORE_NAMES = {
    "AGENTIC_PROVIDER",
    "AGENTIC_PROVIDER_COMMAND",
    "GOOGLE_API_KEY",
    "ISSUE_BODY",
    "ISSUE_LABELS",
    "LOOP_PAUSED",
    "WF_RAG",
    "WHISPERFORGE_E2E_FIXTURE_PATH",
}
ENV_REFERENCE = re.compile(
    r"(?:os\.getenv|os\.environ\.get)\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]"
)
SCHEMA_DECLARATION = re.compile(r"^([A-Z][A-Z0-9_]*)=", re.MULTILINE)


def is_runtime_path(path: Path) -> bool:
    return path.parts[0] in RUNTIME_ROOTS and not EXCLUDED_PARTS.intersection(
        path.parts
    )


class VarlockContractTests(unittest.TestCase):
    def test_schema_is_tracked_while_value_files_stay_ignored(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".env.schema"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(tracked.returncode, 0)

        schema_ignore = subprocess.run(
            ["git", "check-ignore", "--no-index", ".env.schema"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(schema_ignore.returncode, 1)

        values_ignore = subprocess.run(
            [
                "git",
                "check-ignore",
                "--no-index",
                ".env.local",
                ".env.shared.local",
                ".env.spektorai.local",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(values_ignore.returncode, 0)

    def test_shared_imports_are_selective_optional_and_non_authoritative(self) -> None:
        schema = SCHEMA.read_text(encoding="utf-8")
        picks = ",".join(SHARED_NAMES)

        for source in (
            "~/.agents/env/values/.env.shared.local",
            "~/.agents/env/values/.env.spektorai.local",
        ):
            self.assertIn(
                f"# @import({source}, pick=[{picks}], allowMissing=true)", schema
            )

        import_lines = "\n".join(
            line for line in schema.splitlines() if line.startswith("# @import(")
        )
        self.assertNotIn("SERVICE_TOKEN", import_lines)
        self.assertTrue(
            set(SHARED_NAMES).issubset(set(SCHEMA_DECLARATION.findall(schema)))
        )

    def test_active_tracked_runtime_names_are_declared(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files", "-z", "--", "*.py"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout.decode().split("\0")
        runtime_paths = [
            Path(name) for name in tracked if name and is_runtime_path(Path(name))
        ]
        referenced = set(INDIRECT_RUNTIME_NAMES)

        self.assertIn(Path("whisperforge_core/config.py"), runtime_paths)

        for path in runtime_paths:
            referenced.update(
                ENV_REFERENCE.findall((ROOT / path).read_text(encoding="utf-8"))
            )

        declared = set(
            SCHEMA_DECLARATION.findall(SCHEMA.read_text(encoding="utf-8"))
        )
        self.assertIn("OPENAI_API_KEY", referenced)
        self.assertIn("TRANSCRIPTION_BACKEND", referenced)
        self.assertEqual(referenced - declared, set())

    def test_names_only_audit_excludes_non_runtime_noise(self) -> None:
        self.assertTrue(is_runtime_path(Path("whisperforge_core/config.py")))
        for path in (
            "venv/lib/python/site-packages/provider.py",
            "generated/runtime.py",
            "archive/legacy.py",
            "tests/fixtures/runtime.py",
        ):
            with self.subTest(path=path):
                self.assertFalse(is_runtime_path(Path(path)))

        schema = SCHEMA.read_text(encoding="utf-8")
        for name in VARLOCK_AUDIT_IGNORE_NAMES:
            with self.subTest(name=name):
                self.assertRegex(
                    schema,
                    rf"# [^\n]*@auditIgnore[^\n]*\n{re.escape(name)}=",
                )

    def test_external_runtime_names_are_documented(self) -> None:
        contract = (ROOT / "README.md").read_text(encoding="utf-8")

        for name in (
            "GH_TOKEN",
            "GITHUB_*",
            "RUNNER_*",
            "PYTHONPATH",
            "PYTHONUNBUFFERED",
            "PYTHON",
            "PORT",
            "SMOKE_PORT",
            "COMPOSE",
            "VARLOCK",
        ):
            with self.subTest(name=name):
                self.assertIn(f"`{name}`", contract)

    @unittest.skipUnless(VARLOCK, "standalone Varlock CLI is not installed")
    def test_redacted_load_and_noop_run_use_an_isolated_home(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            isolated_env = {
                "HOME": home,
                "PATH": f"{Path(str(VARLOCK)).parent}{os.pathsep}{os.defpath}",
            }
            version = subprocess.run(
                [str(VARLOCK), "--version"],
                cwd=ROOT,
                env=isolated_env,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            self.assertGreaterEqual(tuple(map(int, version.split("."))), (1, 10, 0))

            self._run_varlock(
                ["load", "--agent", "--show-all", "--path", ROOT], isolated_env
            )
            self._run_varlock(
                [
                    "run",
                    "--inject",
                    "vars",
                    "--path",
                    ROOT,
                    "--",
                    sys.executable,
                    "-c",
                    "pass",
                ],
                isolated_env,
            )
            output = self._run_varlock(
                ["load", "--agent", "--show-all", "--path", FIXTURE], isolated_env
            )
            self.assertNotIn(SANITIZED_VALUE, output)
            self._run_varlock(
                [
                    "run",
                    "--inject",
                    "vars",
                    "--path",
                    FIXTURE,
                    "--",
                    sys.executable,
                    "-c",
                    (
                        "import os,sys;"
                        "sys.exit(os.getenv('VARLOCK_REDACTION_PROOF') != "
                        f"'{SANITIZED_VALUE}')"
                    ),
                ],
                isolated_env,
            )

    def _run_varlock(self, arguments: list[str | Path], env: dict[str, str]) -> str:
        result = subprocess.run(
            [str(VARLOCK), *(str(argument) for argument in arguments)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertNotIn(SANITIZED_VALUE, output)
        return output


if __name__ == "__main__":
    unittest.main()
