#!/usr/bin/env python3
"""Real PTY integration tests plus validation and launcher unit tests."""
import fcntl
import importlib.util
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'bob_screensaver.py'
spec = importlib.util.spec_from_file_location('bob', APP)
bob = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bob)


class AppTests(unittest.TestCase):
    def test_bundled_art(self):
        art = bob.load_art(ROOT / 'art')
        self.assertEqual(len(art), 4)
        for name, lines in art:
            self.assertLessEqual(max(map(len, lines)), 80)
            self.assertLessEqual(len(lines), 40)

    def test_reject_escape_sequences(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'evil.txt').write_text('\x1b]52;c;secret\x07')
            with self.assertRaises(ValueError):
                bob.load_art(directory)

    def test_reject_empty_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                bob.load_art(directory)

    def test_invalid_intervals(self):
        for value in ('nan', 'inf', '-1', '0'):
            p = subprocess.run([sys.executable, str(APP), '--interval', value, '--check'],
                               capture_output=True)
            self.assertEqual(p.returncode, 2)

    def test_check_without_tty(self):
        p = subprocess.run([sys.executable, str(APP), '--check'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('4 valid scenes', p.stdout)

    def test_requires_tty(self):
        p = subprocess.run([sys.executable, str(APP)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertIn('interactive terminal', p.stderr)

    def test_launcher_argument_safety(self):
        for terminal in bob.TERMINALS:
            command = bob.terminal_command(terminal, ['--art-dir', '/tmp/a b;not-a-command'])
            self.assertEqual(command[-1], '/tmp/a b;not-a-command')
            self.assertIn(str(APP), command)
            self.assertNotIn('sh', command)

    def run_pty(self, effect='cycle', key=None, terminate=False, small=False, resize=False):
        master, slave = pty.openpty()
        original = termios.tcgetattr(slave)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 42, 100, 0, 0))
        if small:
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 10, 30, 0, 0))
        env = dict(os.environ, TERM='xterm-256color')
        command = [sys.executable, str(APP), '--once', '--interval', '0.15', '--effect', effect]
        if small:
            command.append('--no-color')
        proc = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, env=env)
        output = bytearray()
        deadline = time.monotonic() + 10
        acted = False
        try:
            while proc.poll() is None and time.monotonic() < deadline:
                ready, _, _ = select.select([master], [], [], 0.05)
                if ready:
                    output.extend(os.read(master, 65536))
                if not acted and b'\x1b[?25l' in output:
                    acted = True
                    if resize:
                        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 48, 120, 0, 0))
                        proc.send_signal(signal.SIGWINCH)
                    if key:
                        os.write(master, key)
                    if terminate:
                        proc.send_signal(signal.SIGTERM)
            if proc.poll() is None:
                proc.kill()
                self.fail('PTY renderer timed out')
            proc.wait(timeout=2)
            while select.select([master], [], [], 0)[0]:
                output.extend(os.read(master, 65536))
            self.assertEqual(proc.returncode, 0, output.decode(errors='replace'))
            self.assertEqual(termios.tcgetattr(slave), original, 'TTY modes not restored')
            self.assertIn(b'\x1b[?25h', output, 'Cursor not restored')
            self.assertIn(b'\x1b[?1049l', output, 'Alternate screen not restored')
            if small:
                self.assertIn(b'Bob needs', output)
            return bytes(output)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            os.close(master)
            os.close(slave)

    def test_real_pty_all_effects(self):
        for effect in ('cycle', 'reveal', 'scan', 'static'):
            with self.subTest(effect=effect):
                self.run_pty(effect)

    def test_key_exits(self):
        self.run_pty(key=b'q')

    def test_sigterm_restores_terminal(self):
        self.run_pty(terminate=True)

    def test_small_terminal(self):
        self.run_pty(small=True)

    def test_resize(self):
        self.run_pty(resize=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
