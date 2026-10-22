# AMD BC-250 cluster follow-up: 3/4/6-node reports and evidence gaps

**Research date:** 2026-10-22  
**Repository PR:** [LEONES PR #111](https://github.com/robertosantosx2/LEONES/pull/111)  
**Main research sheet:** [AMD-BC-250-LLM-CLUSTER.md](AMD-BC-250-LLM-CLUSTER.md)

This follow-up records additional Reddit reports and clarifies node counts. All performance figures below are author-reported community results, not LEONES measurements.

## Newly traced reports

### A post titled four-node, but with three functional nodes

Source: [The super junky 4 node BC250 cluster is complete! — r/homelab](https://www.reddit.com/r/homelab/comments/1vfzpqg/the_super_junky_4_node_bc250_cluster_is_complete/)

The author states that one of four purchased boards arrived dead and all benchmarks in the post were run on **three active nodes**. Catalog it as a three-node run, not a four-node benchmark.

- Software: Ubuntu, llama.cpp Vulkan + RPC layer parallelism, llama-swap, Ansible provisioning.
- The author adapted a 40-CU unlock procedure for Ubuntu.
- Hardware/cost reported: 3D-printed rack, used SSDs, 1000 W PSU, inexpensive switch; around €1,000 total.
- Goal: run two models concurrently (Qwen 3.6 27B for reasoning and Qwen 3.6 35B-A3B as executor).
- Interpretation: this is primarily a memory-capacity / concurrent-model deployment. Do not infer linear decode scaling from the title or hardware count.

### Six-board field report

Source: [6 board local AI setup using llama Vulkan and RPC over 1gb Ethernet](https://www.reddit.com/r/BC250Gaming/comments/1wwdwy4/6_board_local_ai_setup_using_llama_vulcan_and_rpc/)

The author reports:
- Four 40-CU boards running Qwen Flash Next 3.8 IQ_XS: about **26 tok/s at 100K context**.
- A two-board pair running Qwen3.6-35B: about **60 tok/s at 100K context**; the author also mentions 60 tok/s with 50K generated context in a test.
- Network: onboard 1 GbE; a 2.5 GbE test was planned.
- Cooling: fans on individual heatsinks plus a plenum; reported load temperatures 60–75 °C.

These are separate model/group results. They do not establish that four nodes are faster than two for an identical workload.

### Independent two-board report

Source: [My foray into local AI — two BC-250 boards, Qwen3.6-35B-A3B Q4_K_M at 60 tok/s](https://www.reddit.com/r/LocalLLaMA/comments/1wou3gr/my_foray_into_local_ai_two_bc250_ex_mining_apus/)

- Reported model: Qwen3.6-35B-A3B Q4_K_M.
- Reported result: approximately 60 tok/s at 64K context.
- Software/network: Bazzite, llama.cpp Vulkan + RPC, onboard 1 GbE.
- Reported combined GPU-visible memory: about 27 GB.
- Reported cost: around US$300 including PSU.

This is an independent author report, not the same deployment as the Fedora/Ansible 4claps project.

### Historical 12-board numbers remain unverified

Source discussion: [Thoughts on the AMD BC-250 16GB “Cards”?](https://www.reddit.com/r/LocalLLaMA/comments/1ovgs5p/thoughts_on_the_amd_bc250_16gb_cards/)

The thread discusses the feasibility of twelve boards, onboard 1 GbE, USB 3 networking and possible M.2 networking. It does not itself provide a reproducible 12-board inference benchmark.

A community aggregation, [BC-250 unofficial community guide — AI inference](https://github.com/katzzero/bc250-unofficial-community-guide/blob/main/12-ai-inference.md), indexes Discord users and historical benchmark claims, and is useful for finding usernames/models. It is a secondary compilation, not the original Discord evidence. In this research pass, the original message/report and raw logs behind specific historical 12-board performance claims were **not located**. Keep these claims labelled **UNVERIFIED / SECONDARY CLAIM**; do not cite them as confirmed benchmarks.

## Normalized comparison

| Active boards during reported run | Model/workload | Reported result | Runtime/network | Evidence quality |
|---|---|---|---|---|
| 2 | Qwen3-30B-A3B Q4_K_M, 8K context | pp 72.48; generation 77.77 tok/s | 4claps, Vulkan + RPC, Fedora 44, pinned llama.cpp commit | Deployment documentation with reproducible configuration |
| 2 | Qwen3.6-35B-A3B Q4_K_M, 64K context | ~60 tok/s generation | Bazzite, Vulkan + RPC, 1 GbE | Author report |
| 3 (four purchased; one dead) | Qwen 3.6 27B + Qwen 3.6 35B-A3B, concurrent-model objective | Do not normalize without per-run logs | Ubuntu, Vulkan + RPC, llama-swap, Ansible | Author report; active-node count clarified |
| 4 | Qwen Flash Next 3.8 IQ_XS, 100K context | ~26 tok/s generation | Vulkan + RPC, 1 GbE | Author report |
| 2 (from a six-board set) | Qwen3.6-35B, 100K context | ~60 tok/s generation | Vulkan + RPC, 1 GbE | Author report |
| 5 | Qwen3-Coder-Next Q4, 30K / 100K context | ~40 / ~30 tok/s generation | Vulkan + RPC, 1 GbE | Author report |
| 12 | Primary report not located | No validated value | Network choices discussed | Unverified secondary claim |

Never treat purchased/installed board count as the active count in a particular run. Record the number of active boards, detected Vulkan/RPC devices, exact model/quantization, runtime commit, actual context, prompt tokens, generated tokens, duration, transport, power and thermal profile.

## Follow-up checklist

- [x] Find a purported four-node post and correct the benchmark count to three active boards.
- [x] Find a six-board report with separate four-board and two-board figures.
- [x] Find an independent two-board 64K-context report.
- [x] Find a secondary community guide that indexes Discord claims.
- [ ] Locate the original Discord message or raw report behind the historical 12-board figures.
- [ ] Obtain complete logs and exact commands for the 3-, 4-, 5- and 6-board reports.
- [ ] Reproduce selected runs under LEONES before assigning the evidence state MEASURED.

**Evidence rule:** Reddit/Discord figures remain third-party claims until LEONES reproduces and records the run.
