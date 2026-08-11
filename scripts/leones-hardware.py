#!/usr/bin/env python3
"""Print a small, privacy-conscious description of the current machine.

This script only answers: 'What hardware/OS am I running on?'
It does not benchmark, publish, inspect personal files, or run an agent.
"""
from pathlib import Path
import os, platform, subprocess, re

def command(*args):
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
    except Exception:
        return ""

def ram():
    try:
        return f"{os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE') / 1024**3:.1f} GB"
    except Exception:
        return "unknown"

def cpu():
    p=Path('/proc/cpuinfo')
    if p.exists():
        for line in p.read_text(errors='ignore').splitlines():
            if line.lower().startswith('model name:'):
                return line.split(':',1)[1].strip()
    return platform.processor() or "unknown"

def gpu():
    found=[]
    n=command('nvidia-smi','--query-gpu=name,memory.total','--format=csv,noheader')
    found += [f"NVIDIA: {x}" for x in n.splitlines() if x]
    for line in command('lspci').splitlines():
        if re.search(r'VGA compatible controller|3D controller|Display controller',line,re.I):
            found.append(line.split(': ',1)[-1].strip())
    return list(dict.fromkeys(found)) or ['none detected']

def main():
    print(f"CPU: {cpu()}")
    print(f"Architecture: {platform.machine()}")
    print(f"RAM: {ram()}")
    print(f"GPU: {'; '.join(gpu())}")
    print(f"OS: {platform.system()} {platform.release()}")

if __name__ == '__main__':
    main()
