"""校验 agent_team/skills/*/v1 初始 Skill 库。"""

from __future__ import annotations

import re
from pathlib import Path

SKILLS_ROOT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "llm_werewolf"
    / "agent_team"
    / "skills"
)
INITIAL_VERSION = "v1"
WOLF_ROLES = frozenset({
    "wolf", "wolf_king", "white_wolf", "wolf_beauty", "guardian_wolf",
    "hidden_wolf", "nightmare_wolf", "blood_moon_apostle",
})
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
FAKE_STAT_RE = re.compile(r"胜率下降|命中率不足|胜率不足")


def _parse_meta(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta


def _quality_checks(role: str, meta: dict[str, str], body: str) -> list[str]:
    issues: list[str] = []
    when = meta.get("when_to_use", "")
    if not when:
        issues.append("missing when_to_use")
    elif "信念矩阵触发" not in when and "狼队矩阵触发" not in when:
        issues.append("when_to_use missing matrix trigger")
    if role in WOLF_ROLES and "狼队矩阵触发" not in when:
        issues.append("wolf role should use 狼队矩阵触发")
    if role not in WOLF_ROLES and "信念矩阵触发" not in when:
        issues.append("good/neutral role should use 信念矩阵触发")
    if meta.get("status") != "active":
        issues.append(f"status={meta.get('status')}")
    if meta.get("quality_passed") not in {"True", "true"}:
        issues.append("quality_passed not True")
    for section in ("## 公开行为", "## 避免"):
        if section not in body:
            issues.append(f"missing {section}")
    if FAKE_STAT_RE.search(body):
        issues.append("contains fabricated win-rate stats")
    return issues


def main() -> int:
    errors = 0
    roles_checked = 0
    skills_checked = 0
    for role_dir in sorted(SKILLS_ROOT.iterdir()):
        if not role_dir.is_dir():
            continue
        role = role_dir.name
        v1 = role_dir / INITIAL_VERSION
        if not v1.is_dir():
            print(f"[{role}] ERROR: missing v1/")
            errors += 1
            continue
        mds = sorted(v1.glob("*.md"))
        if not mds:
            print(f"[{role}] ERROR: v1/ has no skills")
            errors += 1
            continue
        roles_checked += 1
        print(f"\n[{role}] {len(mds)} skill(s)")
        for path in mds:
            skills_checked += 1
            text = path.read_text(encoding="utf-8")
            meta = _parse_meta(text)
            issues = _quality_checks(role, meta, text)
            if issues:
                print(f"  WARN {path.stem}: {'; '.join(issues)}")
                errors += len(issues)
            else:
                print(f"  OK   {path.stem}")
    print(f"\nDone. roles={roles_checked} skills={skills_checked} issues={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
