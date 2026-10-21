# Raw benchmark archive verification

- Uploaded archive: `head-to-head-20261021-raw.tar.gz`
- Archive SHA-256: `60a752fb09cf3774aec0f051bc349ee9677780fbf9c56a9ea46600952efb72dc`
- Archive size: 1,494,277 bytes
- Contents verified: 36 original per-run files (12 `rep-*.log`, 12 `time-*.txt`, 12 `rc-*.txt`) across llama.cpp and RustingStrata.
- All 12 exit-code files contain `0\n`.
- The uploaded archive also contains a generated RustingStrata PTX/profile cache (about 6.3 MB uncompressed). It is intentionally excluded from this manifest because it is a generated cache, not primary benchmark evidence.

This manifest lists SHA-256 and byte size for every original log/timing/exit-code file. Paths are relative to the archive's `head-to-head-20261021/` root.

| File | Bytes | SHA-256 |
|---|---:|---|
| llama/time-6.txt | 1130 | 55e684736ac97c6c663ff398d658a56fad11bc48711c9b11531bd205b24ab531 |
| llama/rc-1.txt | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |
| llama/rep-5.log | 577127 | 59b00f869060cfc2a63ddcdf667631b8d74e27071e7c30d7d36555be8a7f0ac0 |
| llama/rep-6.log | 577109 | 91f7bda45f73eccee9821c1b47951deae3f434c66a8cd626c2cfe77679774267 |
| llama/rc-5.txt | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |
| llama/time-3.txt | 1132 | 259dff31d977c477f440dc69a4181f92580039775a59fbd30643e8c4a8c19da4 |
| llama/rep-2.log | 577165 | ae8fc5362623f5d781ef645cc13a2e4133b7bdb4fac02d44d4e942a5f2ce2d69 |
| llama/rc-3.txt | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |
| llama/rc-6.txt | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |
| llama/time-1.txt | 1130 | 0227b25d1cda89e88f71258707d9a7aeec02b0fc39924790098b94f7f1a5b67d |
| llama/rep-4.log | 576520 | 3245cb189c2514ec2d5c061fdca0b94dfb1cd8811b04d1ece09676190b2c57f0 |
| llama/time-5.txt | 1127 | 6fd4b56553380090863c244e6aeb0cf487c7451599c69115ddc8c96e6783173c |
| llama/rep-1.log | 577145 | 4af02dfc397a5845b80729a60dfbfe2d68c681e5c4ada4c37ea21dbd5f22aeb6 |
| llama/rep-3.log | 577036 | 7b23687105e3b14e2d408e8ada3ab23bed1734ff311fbeb1f7e15f85645c6cac |
| llama/rc-4.txt | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |
| llama/time-4.txt | 1129 | 5c669c2960bdeae2129811e9645484c84c0d25f40c31efb58ab73011f8c570af |
| llama/rc-2.txt | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |
| llama/time-2.txt | 1130 | a7e2403e7de42ee2402d4ada96362e639b65a78a54ba4314ca03776d84c8b4ef |
| strata/time-6.txt | 1017 | eec8bd671ca8569e743641ee1a7741574d7c9538b373b61e929b564bbd72c7b9 |
| strata/rc-1.txt | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |
| strata/rep-5.log | 875 | 4f597c821467467615793df803be6896934eb1b77c09c49c688d9f13be78eda6 |
| strata/rep-6.log | 873 | 8972b133485be550746c6a270398a238231f9e8b02a0d52f2a6355520d57fd9f |
| strata/rc-5.txt | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |
| strata/time-3.txt | 1017 | f435cd0c62f031babe304294aac869fc840369dcf156c3cc18c325279cf0040c |
| strata/rep-2.log | 749 | bf399812f81c5ab597db68c7fc2d6189019d7a0b103c1a73ebd6c5acf2dcee94 |
| strata/rc-3.txt | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |
| strata/rc-6.txt | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |
| strata/time-1.txt | 1025 | 14b9f875a5d7f831e8007914131bc1150f919fb3b38859629e524918012b559a |
| strata/rep-4.log | 769 | 0a25d7e1de074d358a6b69e580e4f0998f35eeece4d97c78d10a9cc4b39195b8 |
| strata/time-5.txt | 1016 | 49f2a4e2b3dad4de1028cd1582c33ffe07c307db81a76272e6d24e6c1e2c6fff |
| strata/rep-1.log | 864 | 4a89ee19020ede0f23b4a61603fc453626bb84485824be5b7ac8340f74fe7268 |
| strata/rep-3.log | 867 | e6ad7d41a5d81d583960f15a9cb2852bd0a8f1b2fd7bb58d319a969471718f1b |
| strata/rc-4.txt | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |
| strata/time-4.txt | 1016 | ba08339b3a336e0bb0dce7146bf3e0f7e5df7383bf11b7a82c7da47a2f15aeb8 |
| strata/rc-2.txt | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |
| strata/time-2.txt | 1018 | 71a8fb4b87680d0c3270241ae4e5917fcf4237760e69468e9c8daeac7313310e |
