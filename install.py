#!/usr/bin/env python3
"""Dependency-free, user-local managed installer (Python 3.9+)."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import sys
import tempfile

APP = "share/subgenius-screensaver"
MANIFEST = APP + "/install-manifest.json"
LAUNCHER = "bin/subgenius-screensaver"
DESKTOP = "share/applications/subgenius-screensaver.desktop"
DOCS = ("README.md", "LICENSE", "THIRD_PARTY_ART.md")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(prefix, relative):
    path = prefix / relative
    for component in [path] + list(path.parents):
        if component.is_symlink():
            raise ValueError("Refusing symlink: " + str(component))
        if component != path and component.exists() and not component.is_dir():
            raise ValueError("Not a directory: " + str(component))
    return path


def allowed(relative):
    if relative in (LAUNCHER, DESKTOP, APP + "/bob_screensaver.py"):
        return True
    if relative in tuple(APP + "/" + name for name in DOCS):
        return True
    p = PurePosixPath(relative)
    return (str(p) == relative and str(p.parent) == APP + "/art"
            and p.name.endswith(".txt") and p.name not in (".", ".."))


def load_manifest(prefix):
    path = safe_path(prefix, MANIFEST)
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError("Manifest is not a regular file")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(manifest, dict) or manifest.get("format") != 1
            or manifest.get("application") != "subgenius-screensaver"
            or manifest.get("prefix") != str(prefix)
            or not isinstance(manifest.get("files"), dict)):
        raise ValueError("Invalid ownership manifest; refusing to modify installation")
    for relative, entry in manifest["files"].items():
        if (not allowed(relative) or not isinstance(entry, dict)
                or not isinstance(entry.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
                or entry.get("mode") not in (0o644, 0o755)):
            raise ValueError("Invalid ownership entry: " + relative)
    return manifest


def check_owned(prefix, entries):
    for relative, entry in entries.items():
        path = safe_path(prefix, relative)
        if not path.exists():
            continue  # Missing managed files can be repaired or forgotten.
        if (not path.is_file() or digest(path.read_bytes()) != entry["sha256"]
                or stat.S_IMODE(path.stat().st_mode) != entry["mode"]):
            raise ValueError("Managed file changed; back it up and move it aside before retrying: "
                             + str(path))


def desktop_quote(value):
    # Exec quoting first, then Desktop Entry string escaping. Percent is a field code.
    value = value.replace("%", "%%")
    value = "".join("\\" + c if c in '\\"`$' else c for c in value)
    return ('"' + value + '"').replace("\\", "\\\\")


def payload(prefix):
    source = Path(__file__).resolve().parent
    main = source / "bob_screensaver.py"
    art = sorted((source / "art").glob("*.txt"))
    if not main.is_file() or not art:
        raise ValueError("Source bundle needs bob_screensaver.py and at least one art/*.txt")
    files = {APP + "/bob_screensaver.py": (main.read_bytes(), 0o755)}
    for path in art:
        if not path.is_file() or path.is_symlink():
            raise ValueError("Artwork must be a regular file: " + str(path))
        files[APP + "/art/" + path.name] = (path.read_bytes(), 0o644)
    for name in DOCS:
        files[APP + "/" + name] = ((source / name).read_bytes(), 0o644)
    launcher = '#!/bin/sh\nexec python3 ' + shlex.quote(str(prefix / APP / "bob_screensaver.py")) + ' "$@"\n'
    files[LAUNCHER] = (launcher.encode(), 0o755)
    desktop = ("[Desktop Entry]\nType=Application\nName=SubGenius Screensaver\n"
               "Comment=Terminal ASCII art animation (not a screen lock)\n"
               "Exec=" + desktop_quote(str(prefix / LAUNCHER)) + " --launch\n"
               "Terminal=false\nCategories=Graphics;\nStartupNotify=false\n")
    files[DESKTOP] = (desktop.encode(), 0o644)
    return files


def write_atomic(path, data, mode, new=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".subgenius-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            os.fchmod(stream.fileno(), mode)
        if new:
            os.link(temporary, path)  # Atomic exclusive creation; never clobber a stranger.
        else:
            os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prune(prefix):
    # Never remove shared bin/, share/, applications/, or the prefix itself.
    for relative in (APP + "/art", APP):
        try:
            safe_path(prefix, relative).rmdir()
        except OSError:
            pass


def install(prefix):
    desired = payload(prefix)
    old = load_manifest(prefix)
    entries = old["files"] if old else {}
    check_owned(prefix, entries)
    for relative in desired:
        path = safe_path(prefix, relative)
        if relative not in entries and path.exists():
            raise ValueError("Refusing to overwrite unrelated file: " + str(path))
    manifest = {"format": 1, "application": "subgenius-screensaver",
                "prefix": str(prefix), "files": {
                    relative: {"sha256": digest(data), "mode": mode}
                    for relative, (data, mode) in desired.items()}}
    desired[MANIFEST] = ((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(), 0o644)
    affected = set(entries) | set(desired)
    before = {}
    for relative in affected:
        path = safe_path(prefix, relative)
        before[relative] = ((path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
                            if path.exists() else None)
    touched = []
    try:
        for relative, (data, mode) in desired.items():
            path = safe_path(prefix, relative)
            write_atomic(path, data, mode, new=before[relative] is None)
            touched.append(relative)
        for relative in set(entries) - set(desired):
            path = safe_path(prefix, relative)
            if path.exists():
                touched.append(relative)
                path.unlink()
    except OSError:
        for relative in reversed(touched):
            path = safe_path(prefix, relative)
            original = before[relative]
            if original is None:
                if path.exists():
                    path.unlink()
            else:
                write_atomic(path, *original)
        prune(prefix)
        raise
    print("Installed {} managed files into {}".format(len(manifest["files"]), prefix))
    print("Launcher: " + str(prefix / LAUNCHER))
    print("Manifest: " + str(prefix / MANIFEST))


def uninstall(prefix):
    manifest = load_manifest(prefix)
    if manifest is None:
        print("No managed installation found at " + str(prefix))
        return
    # Abort the entire uninstall before deletion if ANY owned file was changed.
    check_owned(prefix, manifest["files"])
    for relative in manifest["files"]:
        path = safe_path(prefix, relative)
        if path.exists():
            path.unlink()
    safe_path(prefix, MANIFEST).unlink()
    prune(prefix)
    print("Uninstalled managed files from " + str(prefix) + "; unrelated files preserved")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=Path.home() / ".local",
                        help="installation root (default: ~/.local)")
    parser.add_argument("--uninstall", action="store_true", help="remove unchanged managed files")
    args = parser.parse_args()
    prefix = Path(os.path.abspath(args.prefix.expanduser()))
    if any(ord(c) < 32 or ord(c) == 127 for c in str(prefix)):
        parser.error("prefix must not contain control characters")
    try:
        (uninstall if args.uninstall else install)(prefix)
    except (OSError, ValueError, TypeError) as exc:
        print("Error: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
