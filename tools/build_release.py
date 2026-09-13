#!/usr/bin/env python3
"""Build a deterministic source/deployment archive without third-party tools."""
import gzip
import hashlib
import io
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'subgenius-screensaver-1.0.0'
FILES = ['bob_screensaver.py', 'install.py', 'README.md', 'LICENSE', 'THIRD_PARTY_ART.md']
for name in FILES:
    if not (ROOT / name).is_file():
        raise SystemExit('Missing release file: ' + name)
paths = [ROOT / name for name in FILES]
for folder in ('art', 'source-art', 'tests', 'tools'):
    paths += [p for p in (ROOT / folder).rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and p.suffix != '.pyc']
if (ROOT / 'TEST_RESULTS.md').exists():
    paths.append(ROOT / 'TEST_RESULTS.md')
out = ROOT / 'dist'
out.mkdir(exist_ok=True)
archive = out / (NAME + '.tar.gz')
with archive.open('wb') as destination:
    with gzip.GzipFile(filename='', mode='wb', fileobj=destination, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as tar:
            for path in sorted(paths):
                data = path.read_bytes()
                info = tarfile.TarInfo(NAME + '/' + str(path.relative_to(ROOT)))
                info.size = len(data)
                info.mode = 0o755 if path.suffix == '.py' else 0o644
                info.mtime = 0
                tar.addfile(info, io.BytesIO(data))
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
checksum = out / (archive.name + '.sha256')
checksum.write_text(digest + '  ' + archive.name + '\n')
print(archive)
print('Files:', len(paths), 'Bytes:', archive.stat().st_size)
print('SHA256:', digest)
