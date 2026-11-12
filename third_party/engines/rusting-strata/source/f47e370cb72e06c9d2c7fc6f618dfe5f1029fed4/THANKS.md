# Thanks

RustingStrata runs on many machines it was never developed on because people tested it there, reported what broke and
told us what they need. Thank you all.

## Testing and reports

- [runningman84](https://github.com/runningman84): multi-GPU testing on two AMD cards (issue #1), found that AMD cards
  downclock in the gaps of a layer split.
- [charmoky](https://github.com/charmoky): RX 9070 XT reports and reruns on Vulkan/RADV (issue #3).
- [ike287](https://github.com/ike287): feedback and feature requests.
- [pberenyi](https://github.com/pberenyi): fount bug with Swift-1.5-Qwen3.8-27B (issue #11)
- [luckydevil13](https://github.com/luckydevil13): helped with AMD benchmarks and some Ideas about new models.
- [hermeticvm](https://github.com/hermeticvm): RX 6700 XT / RADV report on slow 30K Qwen3.6 prefill (issue #10).
- [SugiKi1996](https://github.com/SugiKi1996): found that Turing (sm_75) was rejected on NVRTC 13.x, with the fix and
  RTX 2080 Ti numbers (issue #17).

## Ideas

- [FredWalter](https://github.com/FredWalter): multi-GPU and Qwen3.8-Flash-Next support (issue #1).
- [Ocean572](https://github.com/Ocean572): configurable allowed-host setting for LAN access (issue #13).
- [outbackdingo](https://github.com/outbackdingo): cuda-oxide kernels (issue #4).
- [KotPrezesOfficial](https://github.com/KotPrezesOfficial): MCP support and GUI options (issue #18).

## Code

- [bettercallcaleb](https://github.com/bettercallcaleb): GGUF loader rejects malformed metadata instead of panicking
  (PR #2), hiding incomplete GGUF shard sets from the model list (PR #8) and prequantizing the DeltaNet gate before
  batched GEMM (PR #9).
- [jazir555](https://github.com/jazir555): runtime LoRA abliteration without modifying base weights (PR #15) and the
  host RAM cap (PR #16).
- [x-Pepsy](https://github.com/x-Pepsy): the Turing (sm_75) CUDA path (PR #6).
- [masanork](https://github.com/masanork): Vulkan wave64 for the Radeon VII (PR #5).
- [pberenyi](https://github.com/pberenyi): server improvements for `strata serve` (PR #14).

## Reddit

- [gcavalcante8808](https://github.com/gcavalcante8808): First helper ever, did multiple benchmarks and rapports on AMD GPU, very big contribute!
