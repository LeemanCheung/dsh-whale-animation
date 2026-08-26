from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DOCS = ROOT / "docs"
EXPECTED_STATES = ("dive", "sonar", "work", "compose", "idle", "alert")
EXPECTED_PLAYLIST = ["dive", "sonar", "work", "compose", "idle"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def webp_durations(path: Path) -> list[int]:
    data = path.read_bytes()
    require(data[:4] == b"RIFF" and data[8:12] == b"WEBP", f"Invalid RIFF WebP: {path.relative_to(ROOT)}")
    durations: list[int] = []
    offset = 12
    while offset + 8 <= len(data):
        kind = data[offset:offset + 4]
        size = int.from_bytes(data[offset + 4:offset + 8], "little")
        payload = offset + 8
        if kind == b"ANMF":
            require(payload + 15 <= len(data), f"Truncated ANMF chunk: {path.relative_to(ROOT)}")
            durations.append(int.from_bytes(data[payload + 12:payload + 15], "little"))
        offset = payload + size + (size & 1)
    return durations


def image_profile(path: Path) -> tuple[tuple[int, int], int, list[int]]:
    require(path.is_file(), f"Missing image: {path.relative_to(ROOT)}")
    image = Image.open(path)
    frame_count = int(getattr(image, "n_frames", 1))
    durations = webp_durations(path) if path.suffix.lower() == ".webp" and frame_count > 1 else []
    return image.size, frame_count, durations


def local_references(markdown: str) -> set[str]:
    refs: set[str] = set()
    patterns = (
        r"!\[[^\]]*\]\(([^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)",
        r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)",
        r"<(?:img|a)\b[^>]+(?:src|href)=[\"']([^\"']+)[\"']",
    )
    for pattern in patterns:
        refs.update(re.findall(pattern, markdown, flags=re.IGNORECASE))
    return refs


def validate_readme(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    require(text.count("```mermaid") == 1, f"{path.name} must contain exactly one Mermaid diagram")
    require("v0.4.0" in text, f"{path.name} does not document v0.4.0")
    require("docs/preview.webp" in text, f"{path.name} does not reference the animated preview")
    require("docs/state-gallery.png" in text, f"{path.name} does not reference the state gallery")
    require("docs/screenshots/" not in text, f"{path.name} still references removed v0.3 screenshots")

    checked: list[str] = []
    for raw in sorted(local_references(text)):
        ref = unquote(raw.split("#", 1)[0].split("?", 1)[0]).strip()
        if not ref or ref.startswith(("http://", "https://", "mailto:", "#", "data:")):
            continue
        target = (path.parent / ref).resolve()
        require(ROOT == target or ROOT in target.parents, f"Reference escapes repository: {raw}")
        require(target.exists(), f"Broken local reference in {path.name}: {raw}")
        checked.append(ref)
    return {"file": path.name, "localReferences": checked}


def main() -> None:
    manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
    require(manifest.get("schemaVersion") == 1, "Unexpected manifest schema")
    require(manifest.get("canvas") == [352, 352], "Unexpected source canvas")
    require(manifest.get("defaultState") == "dive", "Unexpected default animation state")
    require(manifest.get("playlist") == EXPECTED_PLAYLIST, "Unexpected timed playlist")
    require(manifest.get("playlistIntervalMs") == 9000, "Unexpected playlist interval")
    require(tuple(manifest.get("states", {}).keys()) == EXPECTED_STATES, "Unexpected state ordering or membership")

    source_profiles: dict[str, dict[str, object]] = {}
    for state in EXPECTED_STATES:
        spec = manifest["states"][state]
        require(spec["frames"] == 48, f"{state}: manifest frame count changed")
        require(spec["frameDurationMs"] == 40, f"{state}: manifest frame duration changed")
        require(spec["loopDurationMs"] == 1920, f"{state}: manifest loop duration changed")
        animated_path = ASSETS / spec["animated"]
        static_path = ASSETS / spec["static"]
        size, frames, durations = image_profile(animated_path)
        static_size, static_frames, _ = image_profile(static_path)
        require(size == (352, 352), f"{state}: unexpected WebP dimensions {size}")
        require(frames == 48, f"{state}: unexpected WebP frame count {frames}")
        require(set(durations) == {40}, f"{state}: unexpected WebP timing {sorted(set(durations))}")
        require(static_size == (352, 352) and static_frames == 1, f"{state}: invalid reduced-motion PNG")
        source_profiles[state] = {
            "frames": frames,
            "durationMs": sum(durations),
            "animatedBytes": animated_path.stat().st_size,
            "staticBytes": static_path.stat().st_size,
        }

    hero_size, hero_frames, _ = image_profile(DOCS / "hero.png")
    gallery_size, gallery_frames, _ = image_profile(DOCS / "state-gallery.png")
    preview_size, preview_frames, preview_durations = image_profile(DOCS / "preview.webp")
    require(hero_size == (1200, 420) and hero_frames == 1, f"Unexpected hero profile: {hero_size}, {hero_frames}")
    require(gallery_size == (1200, 760) and gallery_frames == 1, f"Unexpected gallery profile: {gallery_size}, {gallery_frames}")
    require(preview_size == (1000, 360), f"Unexpected preview dimensions: {preview_size}")
    require(preview_frames == 50, f"Unexpected preview frame count: {preview_frames}")
    require(set(preview_durations) == {55}, f"Unexpected preview timing: {sorted(set(preview_durations))}")
    require((DOCS / "preview.webp").stat().st_size <= 1024 * 1024, "README preview exceeds 1 MiB budget")

    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    require(package.get("version") == "0.4.0", "package.json version is not 0.4.0")
    require(package.get("scripts", {}).get("check") == "node scripts/check.mjs && python scripts/check-readme-assets.py", "Package check script is incomplete")

    readmes = [validate_readme(ROOT / "README.md"), validate_readme(ROOT / "README.zh-CN.md")]
    print(json.dumps({
        "ok": True,
        "states": list(EXPECTED_STATES),
        "sources": source_profiles,
        "hero": {"size": hero_size},
        "gallery": {"size": gallery_size},
        "preview": {
            "size": preview_size,
            "frames": preview_frames,
            "frameDurationMs": 55,
            "durationMs": sum(preview_durations),
            "bytes": (DOCS / "preview.webp").stat().st_size,
        },
        "readmes": readmes,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
