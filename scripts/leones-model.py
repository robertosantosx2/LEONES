#!/usr/bin/env python3
"""Describe one local model file without running it."""
from pathlib import Path
import argparse, hashlib

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description='Describe a model file.')
    p.add_argument('model')
    a=p.parse_args(); path=Path(a.model)
    if not path.is_file(): raise SystemExit(f'No existe: {path}')
    print(f'File: {path.name}')
    print(f'Size: {path.stat().st_size/1024**3:.2f} GB')
    print(f'SHA-256: {sha256(path)}')
    print('Format: inferred from extension')
    print(f'Extension: {path.suffix.lower() or "unknown"}')

if __name__ == '__main__': main()
