#!/usr/bin/env python3
import json, glob, os

OSI = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "MPL-2.0",
    "LGPL-2.1-only",
    "LGPL-2.1-or-later",
    "LGPL-3.0-only",
    "LGPL-3.0-or-later",
    "GPL-2.0-only",
    "GPL-2.0-or-later",
    "GPL-3.0-only",
    "GPL-3.0-or-later",
    "AGPL-3.0-only",
    "AGPL-3.0-or-later",
    "EPL-2.0",
    "CDDL-1.0",
    "CPL-1.0",
    "Artistic-2.0",
}
os.makedirs("data/discovery", exist_ok=True)
for fn in glob.glob("data/discovery/*.json"):
    with open(fn, encoding="utf-8") as f:
        d = json.load(f)
    if d.get("kind") == "models":
        for x in d.get("items", []):
            x["osi_status"] = "non-osi-model-license"
    else:
        for x in d.get("items", []):
            x["osi_status"] = (
                "osi-approved"
                if x.get("license") in OSI
                else ("unknown" if not x.get("license") else "non-osi-or-unverified")
            )
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
