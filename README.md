# SubGenius terminal screensaver

A standalone terminal ASCII-art screensaver for Linux, using Python's standard library and `curses`. **This is a visual screensaver, not a screen lock or authentication boundary.** It does not secure your session. Keep your existing locker and lock timers enabled.

## Requirements

- Python **3.9 or newer**, with the standard-library `curses` module.
- An interactive terminal for direct use; a supported installed terminal emulator for `--launch`.
- No pip packages, network downloads, administrator privileges, or system services are required by the installer.

If Python or a terminal is missing, an administrator can install distribution packages separately:

```sh
# Debian / Ubuntu (run with appropriate administrator privileges):
apt install python3
apt install foot      # optional, Wayland
# or: apt install xterm   # X11 / XWayland

# Arch (run with appropriate administrator privileges):
pacman -S python
pacman -S foot         # optional, Wayland
# or: pacman -S xterm     # X11 / XWayland
```

Existing kitty, alacritty, gnome-terminal, or konsole installations can also be used. A graphical terminal needs a functioning graphical session; plain SSH without a display should use direct terminal mode.

## Run from this directory

```sh
python3 bob_screensaver.py --check
python3 bob_screensaver.py --list
python3 bob_screensaver.py --once
python3 bob_screensaver.py                       # animate in current TTY
python3 bob_screensaver.py --launch              # open a terminal window
python3 bob_screensaver.py --launch --terminal foot
```

Use `--help` for the renderer's exact options. Any key or mouse click exits; Ctrl+C also stops direct execution. If Bob does not fit, enlarge the terminal or reduce its font size: the bundled scenes need up to 75 columns and 34 rows, including a safety margin. The original tall source portraits are archived in `source-art/`; the active scenes use the compact portrait without cropping.

## Deployment archive and tests

The same source bundle works on Debian and Arch; no compilation or pip installation is needed. To build a portable archive:

```sh
python3 tools/build_release.py
```

Copy `dist/subgenius-screensaver-1.0.0.tar.gz` and its `.sha256` file to the other computer. Verify and extract there:

```sh
sha256sum -c subgenius-screensaver-1.0.0.tar.gz.sha256
tar -xzf subgenius-screensaver-1.0.0.tar.gz
cd subgenius-screensaver-1.0.0
python3 install.py
"$HOME/.local/bin/subgenius-screensaver" --launch
```

Run `python3 -m unittest discover -s tests -v` to exercise the renderer and installer. See [TEST_RESULTS.md](TEST_RESULTS.md) in the source bundle for the tested environments and limits. Fullscreen Foot was tested on the Arch-based desktop; Debian testing covers a real Debian userspace and terminal rendering, not a Debian graphical desktop.

| Option | Purpose |
| --- | --- |
| `--launch` | Start in a supported graphical terminal |
| `--terminal foot\|kitty\|alacritty\|xterm\|gnome-terminal\|konsole` | Select the emulator for `--launch` |
| `--list` | List bundled artwork |
| `--once` | Show one complete artwork rotation in an interactive TTY, then exit |
| `--interval SECONDS` | Set artwork rotation interval (finite, at least 0.1 seconds) |
| `--effect cycle\|reveal\|scan\|static` | Choose animation effect |
| `--no-color` | Disable colors |
| `--art-dir DIRECTORY` | Use a separate directory of `.txt` artwork |
| `--check` | Check runtime/art availability without entering animation |
| `--version` | Print version |

## User-local install

From this source directory:

```sh
python3 install.py
"$HOME/.local/bin/subgenius-screensaver" --check
"$HOME/.local/bin/subgenius-screensaver" --launch
```

The default prefix is `~/.local`. Custom paths, including spaces, are supported:

```sh
python3 install.py --prefix "$HOME/Applications/Bob Screensaver"
"$HOME/Applications/Bob Screensaver/bin/subgenius-screensaver" --once
```

Installed layout:

```text
PREFIX/bin/subgenius-screensaver
PREFIX/share/subgenius-screensaver/bob_screensaver.py
PREFIX/share/subgenius-screensaver/art/*.txt
PREFIX/share/subgenius-screensaver/README.md
PREFIX/share/subgenius-screensaver/LICENSE
PREFIX/share/subgenius-screensaver/THIRD_PARTY_ART.md
PREFIX/share/subgenius-screensaver/install-manifest.json
PREFIX/share/applications/subgenius-screensaver.desktop
```

The shell launcher runs `python3` from your PATH with the absolute installed script path and forwards all arguments unchanged. The desktop entry invokes the launcher with `--launch`. Desktop menus normally discover the default prefix; a custom prefix may require manually launching the executable or configuring your desktop's application search path. This installer does not edit PATH, shell startup files, desktop configuration, autostart, idle daemons, or lock settings. Keep the source `install.py` for uninstalling; it does not need the renderer or art for uninstall.

### Ownership, updates, and uninstall

Rerun the same install command to update. A manifest records exact owned paths, SHA-256 hashes and permissions. Existing unrelated destination files are never overwritten, even if identical. Changed managed files cause the entire update or uninstall to **abort before changes**. Back up and move changed files outside the managed installation, then retry; missing managed files can be repaired by reinstall. Do not delete or edit the ownership manifest. A malformed manifest aborts; a missing manifest means existing files cannot be adopted automatically.

```sh
python3 install.py --uninstall
# For a custom installation, use exactly the same prefix:
python3 install.py --prefix "$HOME/Applications/Bob Screensaver" --uninstall
```

Uninstall removes only verified managed files and the manifest. Unrelated files and nonempty directories remain. Shared `bin`, `share`, and `applications` directories are never removed. Symlinks in destination paths (including the prefix) are rejected rather than followed; use a real directory path. Control characters in prefix names are rejected. Do not run concurrent installs/uninstalls or edit managed files during installation. Writes are per-file atomic on ordinary Linux filesystems with hard-link support; recoverable write failures attempt rollback, but a killed process or failing disk is not a fully transactional installation. Keep backups of your own work. No system-wide installation is attempted.

## Optional idle demonstration (manual, not installed)

On a Wayland compositor that supports the idle notification protocol used by `swayidle`, you may manually start an **additional** demonstration timer in a terminal:

```sh
swayidle -w timeout 300 '"$HOME/.local/bin/subgenius-screensaver" --launch'
```

This requires separately installed `swayidle` and a supported terminal. Stop the demonstration daemon with Ctrl+C in its terminal; close the launched screensaver window separately. It does not add a resume handler or guarantee automatic window dismissal, fullscreen behavior, or multi-monitor coverage. **Do not replace or disable your existing lock daemon/timers** with this example. Avoid running duplicate demonstration timers.

Sway/compatible Wayland compositors may support this protocol; GNOME may not. There is **no guaranteed GNOME or KDE native idle/screensaver integration**. The application does not register as a desktop locker. For reliable locking, continue using your desktop's supported locker.

## Omarchy: intentionally independent

Installation leaves an existing Omarchy installation completely untouched, including its artwork, theme, Hyprland, idle and lock configuration. No Omarchy component is needed here.

If you separately want to use an artwork in your existing Omarchy setup, first inspect your installed version's supported user artwork location and format. Back up any destination artwork before manually copying a selected `art/*.txt` file into that **user-owned** location. Never overwrite a whole configuration directory, replace stock configuration with this repository, or edit packaged `/usr/share/omarchy` files. Alternatively, leave Omarchy alone and use this application's `--art-dir` with your own independent directory.


