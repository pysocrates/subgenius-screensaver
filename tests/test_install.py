#!/usr/bin/env python3
"""Installer integration checks, always isolated under temporary directories."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / 'install.py'


@unittest.skipUnless(INSTALLER.exists(), 'installer not present')
class InstallTests(unittest.TestCase):
    def run_install(self, prefix, *args):
        return subprocess.run([sys.executable, str(INSTALLER), '--prefix', str(prefix), *args],
                              capture_output=True, text=True)

    def test_install_run_reinstall_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / 'prefix with spaces'
            install = self.run_install(prefix)
            self.assertEqual(install.returncode, 0, install.stderr)
            launcher = prefix / 'bin/subgenius-screensaver'
            result = subprocess.run([str(launcher), '--check'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('4 valid scenes', result.stdout)
            again = self.run_install(prefix)
            self.assertEqual(again.returncode, 0, again.stderr)
            unrelated = prefix / 'share/keep-me.txt'
            unrelated.write_text('unrelated')
            remove = self.run_install(prefix, '--uninstall')
            self.assertEqual(remove.returncode, 0, remove.stderr)
            self.assertFalse(launcher.exists())
            self.assertEqual(unrelated.read_text(), 'unrelated')

    def test_refuse_unrelated_launcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp)
            launcher = prefix / 'bin/subgenius-screensaver'
            launcher.parent.mkdir()
            launcher.write_text('unrelated application')
            result = self.run_install(prefix)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(launcher.read_text(), 'unrelated application')

    def test_preserve_modified_art_on_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp)
            result = self.run_install(prefix)
            self.assertEqual(result.returncode, 0, result.stderr)
            art = next((prefix / 'share/subgenius-screensaver/art').glob('*.txt'))
            art.write_text('CUSTOM USER ART\n')
            self.run_install(prefix, '--uninstall')
            self.assertEqual(art.read_text(), 'CUSTOM USER ART\n')

    def test_shell_metacharacters_in_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "a 'quoted' ; dollar$ prefix"
            result = self.run_install(prefix)
            self.assertEqual(result.returncode, 0, result.stderr)
            run = subprocess.run([str(prefix / 'bin/subgenius-screensaver'), '--version'],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('1.0.0', run.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
