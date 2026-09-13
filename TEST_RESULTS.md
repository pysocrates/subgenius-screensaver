# Verification report

## Executed environments

- Host: Omarchy 4.0.3 (`ID_LIKE=arch`), Python 3.14.7.
- Debian userspace: Debian GNU/Linux 12 (bookworm), Python 3.13.15, from the official `python:3.13-slim-bookworm` image. Run using unprivileged bubblewrap on the host kernel; this was not a separate Debian desktop or VM.
- Image manifest used: `sha256:2f2e5a876c71a6757f55ec57f2add0225ddaf01c802a33fcc29073943f94d907`.

## Results

`python3 -m unittest discover -s tests -v`:

- Arch-based host: **16 tests passed**.
- Debian userspace: **16 tests passed**.
- Both include real pseudoterminal rendering, all animation modes, a complete four-scene rotation, keyboard exit, SIGTERM cleanup, terminal resize, small-terminal behavior, input validation, installer lifecycle, preservation of user-modified artwork, and unusual install paths.
- `--check`: all four scenes valid, curses available, exit 0 on both environments.
- Staged installation launcher: `--check` exit 0.
- Generated desktop file: `desktop-file-validate` exit 0 on the host.
- `python3 tests/smoke_desktop.py`: actual Foot fullscreen window detected at 3440x1440 on Hyprland; one complete rotation; launcher exit 0.
- Foot emitted a nonfatal warning about the compositor not implementing the optional xdg-toplevel-icon protocol.

## Limits

The Debian test uses the image's Python 3.13, not Debian 12's distribution-default Python. No Debian graphical session, GNOME, KDE, X11 terminal, multi-monitor behavior, or automatic idle integration was exercised. The graphical smoke test covers Foot on the existing Arch-based Wayland desktop only. Other terminal launchers are implemented, with argument construction unit-tested, but are not claimed as visually verified.

This is not a secure screen lock. Installation does not change idle/lock settings or the existing Omarchy screensaver.

## Repeat

```sh
python3 -m unittest discover -s tests -v
python3 bob_screensaver.py --check
# Optional, requires a live Hyprland session and Foot; opens a window:
python3 tests/smoke_desktop.py
# Deterministic source archive and SHA-256:
python3 tools/build_release.py
```
