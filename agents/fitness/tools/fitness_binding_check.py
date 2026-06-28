"""Read-only binding readiness check for Fitness Agent."""

from __future__ import annotations

from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
AGENT_ROOT = WORKSPACE_ROOT / "agents" / "fitness"
SKILL_FILE = WORKSPACE_ROOT / "skills" / "fitness-coach" / "SKILL.md"


REQUIRED_FILES = {
    "Core handler": AGENT_ROOT / "handler.py",
    "Channel adapter": AGENT_ROOT / "channel_adapter.py",
    "OpenClaw scaffold": AGENT_ROOT / "integrations" / "openclaw_adapter.py",
    "Skill file": SKILL_FILE,
}

REFERENCE_FILES = [
    SKILL_FILE,
    AGENT_ROOT / "channel_adapter.py",
    AGENT_ROOT / "integrations" / "openclaw_adapter.py",
    AGENT_ROOT / "docs" / "OPENCLAW_RUNTIME_DISCOVERY.md",
    AGENT_ROOT / "docs" / "OPENCLAW_INTEGRATION.md",
    WORKSPACE_ROOT / ".openclaw" / "workspace-state.json",
]

RUNTIME_PATTERNS = (
    "def handle_message",
    "def on_message",
    "on_message(",
    "entrypoint",
    "dispatcher",
    "runtime.dispatch",
    "plugin.json",
)

IGNORED_PARTS = {
    ".git",
    "README.md",
    "agents/fitness",
    "docs/agents/fitness",
    "memory",
    "outputs",
    "skills",
}


def _status(path: Path) -> str:
    return "OK" if path.exists() else "MISSING"


def _is_ignored(path: Path) -> bool:
    rel = path.relative_to(WORKSPACE_ROOT).as_posix()
    return any(rel == part or rel.startswith(f"{part}/") for part in IGNORED_PARTS)


def discover_runtime_entrypoints() -> list[Path]:
    """Conservatively scan for runtime-like entrypoint files outside Fitness docs/code."""
    hits: list[Path] = []
    for path in WORKSPACE_ROOT.rglob("*"):
        if not path.is_file() or _is_ignored(path):
            continue
        if path.suffix.lower() not in {".py", ".js", ".ts", ".json", ".md", ".yaml", ".yml", ".toml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if any(pattern in text for pattern in RUNTIME_PATTERNS):
            hits.append(path)
    return sorted(hits)


def main() -> int:
    runtime_hits = discover_runtime_entrypoints()
    runtime_found = bool(runtime_hits)
    binding_mode = "runtime-wrapper" if runtime_found else "skill-guided"

    print("Fitness Agent Binding Check")
    print()
    for label, path in REQUIRED_FILES.items():
        print(f"{label}: {_status(path)}")
    print(f"Runtime entrypoint discovered: {'YES' if runtime_found else 'NO'}")
    print(f"Recommended binding mode: {binding_mode}")
    print()

    for path in REFERENCE_FILES:
        rel = path.relative_to(WORKSPACE_ROOT)
        print(f"{rel}: {'found' if path.exists() else 'missing'}")

    if runtime_hits:
        print()
        print("Runtime-like candidates:")
        for path in runtime_hits:
            print(f"- {path.relative_to(WORKSPACE_ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
