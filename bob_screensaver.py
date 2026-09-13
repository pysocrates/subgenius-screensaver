#!/usr/bin/env python3
"""Portable SubGenius visual screensaver. Python 3.9+, standard library only.

Not a security lock. No network, systemd, compositor, or Omarchy dependency.
Code: MIT. Artwork has separate provenance; see THIRD_PARTY_ART.md.
"""
import argparse
import math
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import sys
import time

VERSION = '1.0.0'
ROOT = Path(__file__).resolve().parent
TERMINALS = ('foot', 'kitty', 'alacritty', 'xterm', 'gnome-terminal', 'konsole')


def load_art(directory):
    """Accept printable ASCII only: artwork cannot inject terminal escapes."""
    result = []
    for path in sorted(Path(directory).glob('*.txt')):
        if path.stat().st_size > 256_000:
            raise ValueError('Artwork is too large: ' + str(path))
        text = path.read_text(encoding='ascii')
        if any(c != '\n' and not ' ' <= c <= '~' for c in text):
            raise ValueError('Artwork must contain printable ASCII and newlines: ' + str(path))
        lines = text.splitlines()
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines or not any(line.strip() for line in lines):
            raise ValueError('Empty artwork: ' + str(path))
        result.append((path.name, lines))
    if not result:
        raise ValueError('No .txt artwork found in ' + str(directory))
    return result


def terminal_command(terminal, app_args):
    """Argument arrays, never shell commands. Fullscreen is terminal/WM-managed."""
    command = [sys.executable, str(Path(__file__).resolve())] + app_args
    prefixes = {
        'foot': ['foot', '--fullscreen', '--app-id=subgenius-screensaver', '-e'],
        'kitty': ['kitty', '--start-as=fullscreen', '--class=subgenius-screensaver'],
        'alacritty': ['alacritty', '--class=subgenius-screensaver', '--option',
                      'window.startup_mode="Fullscreen"', '-e'],
        'xterm': ['xterm', '-fullscreen', '-fa', 'monospace', '-fs', '14', '-e'],
        'gnome-terminal': ['gnome-terminal', '--full-screen', '--wait', '--'],
        'konsole': ['konsole', '--separate', '--fullscreen', '-e'],
    }
    return prefixes[terminal] + command


def launch(args):
    if not (os.environ.get('WAYLAND_DISPLAY') or os.environ.get('DISPLAY')):
        raise ValueError('No graphical display. Run without --launch in a terminal/TTY.')
    candidates = [args.terminal] if args.terminal else list(TERMINALS)
    terminal = next((name for name in candidates if shutil.which(name)
                     and (name != 'foot' or os.environ.get('WAYLAND_DISPLAY'))
                     and (name != 'xterm' or os.environ.get('DISPLAY'))), None)
    if not terminal:
        raise ValueError('No compatible terminal found. Install foot (Wayland) or xterm (X11), '
                         'or select another supported --terminal.')
    child_args = ['--art-dir', str(Path(args.art_dir).resolve()), '--interval', str(args.interval),
                  '--effect', args.effect]
    if args.once:
        child_args.append('--once')
    if args.no_color:
        child_args.append('--no-color')
    return subprocess.call(terminal_command(terminal, child_args))


def draw(screen, lines, points, effect, progress, color):
    import curses
    rows, cols = screen.getmaxyx()
    height, width = len(lines), max(map(len, lines))
    screen.erase()
    if height > rows - 1 or width > cols - 1:
        message = 'Bob needs %dx%d cells. Enlarge terminal or reduce font. Any key exits.' % (width + 1, height + 1)
        try:
            screen.addstr(max(0, rows // 2), 0, message[:max(0, cols - 1)])
        except curses.error:
            pass
    else:
        y0, x0 = (rows - height) // 2, (cols - width) // 2
        count = len(points) if effect == 'static' else int(len(points) * progress)
        scan_row = int(height * progress)
        for i, (y, x, character) in enumerate(points):
            if effect == 'reveal' and i >= count:
                continue
            if effect == 'scan' and y >= scan_row and progress < 1:
                continue
            try:
                screen.addch(y0 + y, x0 + x, character, color)
            except curses.error:
                # A resize can happen between getmaxyx() and addch().
                pass
    screen.refresh()


def animate(screen, artworks, args):
    import curses
    screen.keypad(True)
    screen.nodelay(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
    except curses.error:
        pass
    palette = [0]
    if not args.no_color and curses.has_colors():
        curses.start_color()
        for i, color in enumerate((curses.COLOR_CYAN, curses.COLOR_GREEN,
                                   curses.COLOR_MAGENTA, curses.COLOR_YELLOW), 1):
            curses.init_pair(i, color, curses.COLOR_BLACK)
        palette = [curses.color_pair(i) | curses.A_BOLD for i in range(1, 5)]
        screen.bkgd(' ', curses.color_pair(1))
    slide = 0
    while True:
        _, lines = artworks[slide % len(artworks)]
        points = [(y, x, ch) for y, line in enumerate(lines)
                  for x, ch in enumerate(line) if ch != ' ']
        random.Random(slide).shuffle(points)
        effect = ('reveal', 'scan', 'static')[slide % 3] if args.effect == 'cycle' else args.effect
        started = time.monotonic()
        animation_seconds = min(2.0, args.interval * 0.4)
        while True:
            key = screen.getch()
            if key not in (-1, curses.KEY_RESIZE):
                return 0
            elapsed = time.monotonic() - started
            progress = min(1.0, elapsed / animation_seconds)
            draw(screen, lines, points, effect, progress, palette[slide % len(palette)])
            if elapsed >= args.interval:
                break
            time.sleep(min(0.05, args.interval - elapsed))
        slide += 1
        if args.once and slide >= len(artworks):
            return 0


def positive_seconds(value):
    number = float(value)
    if not math.isfinite(number) or number < 0.1:
        raise argparse.ArgumentTypeError('interval must be finite and at least 0.1 seconds')
    return number


def parser():
    p = argparse.ArgumentParser(description='Animated Bob ASCII slideshow (NOT a screen lock).')
    p.add_argument('--version', action='version', version='subgenius-screensaver ' + VERSION)
    p.add_argument('--art-dir', default=str(ROOT / 'art'), help='directory of printable ASCII .txt scenes')
    p.add_argument('--interval', type=positive_seconds, default=15.0, help='seconds per scene (default: 15)')
    p.add_argument('--effect', choices=('cycle', 'reveal', 'scan', 'static'), default='cycle')
    p.add_argument('--once', action='store_true', help='show one complete rotation, then exit')
    p.add_argument('--no-color', action='store_true')
    p.add_argument('--list', action='store_true', help='list artwork dimensions and exit')
    p.add_argument('--check', action='store_true', help='validate assets and curses dependency without launching')
    p.add_argument('--launch', action='store_true', help='open a new fullscreen terminal')
    p.add_argument('--terminal', choices=TERMINALS, help='terminal to use with --launch')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        artworks = load_art(args.art_dir)
        if args.list or args.check:
            for name, lines in artworks:
                print('%s: %dx%d' % (name, max(map(len, lines)), len(lines)))
            if args.check:
                import curses
                print('OK: Python %s; curses available; %d valid scenes' %
                      (sys.version.split()[0], len(artworks)))
            return 0
        if args.launch:
            return launch(args)
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ValueError('An interactive terminal is required. Use --check or --launch instead.')
        if not os.environ.get('TERM') or os.environ.get('TERM') == 'dumb':
            raise ValueError('TERM must describe a capable terminal (for example xterm-256color).')
        import curses
        # SIGTERM/SIGHUP unwind curses.wrapper so terminal modes/cursor are restored.
        previous = {}
        def stop(signum, frame):
            raise KeyboardInterrupt
        for signum in (signal.SIGTERM, signal.SIGHUP):
            previous[signum] = signal.signal(signum, stop)
        try:
            return curses.wrapper(animate, artworks, args)
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, ImportError) as error:
        print('subgenius-screensaver: ' + str(error), file=sys.stderr)
        return 1
    except Exception as error:
        # Includes curses setupterm failures; wrapper already restores the terminal.
        print('subgenius-screensaver: %s: %s' % (type(error).__name__, error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
