"""Hashes of current code and immutable experiment inputs."""
import hashlib
from pathlib import Path
from benchmark.core.bootstrap import PROJECT_ROOT

CORPUS = PROJECT_ROOT / 'data/collections/uploaded_files'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def code_files():
    # application/service keeps symlinks to the moved engine files (historical paths);
    # the package tree adds core modules that have no legacy path.
    paths = sorted((PROJECT_ROOT / 'application/service').rglob('*.py'))
    paths += sorted(p for p in (PROJECT_ROOT / 'packages/rag-ufc-core/src').rglob('*.py')
                    if '__pycache__' not in p.parts)
    paths += sorted(p for p in (PROJECT_ROOT / 'benchmark').rglob('*.py')
                    if p.relative_to(PROJECT_ROOT / 'benchmark').parts[0] not in ('results', 'datasets'))
    return paths

def implementation_hash():
    return hashlib.sha256(b''.join(str(p.relative_to(PROJECT_ROOT)).encode() + p.read_bytes()
                                  for p in code_files())).hexdigest()
