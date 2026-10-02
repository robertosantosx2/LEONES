# Axolotl — ODS Post-Training Service Provider

## Executive summary

[Axolotl](https://github.com/axolotl-ai-cloud/axolotl) is an open-source post-training and fine-tuning framework for modern language and multimodal models. Its configuration-driven workflow, Docker support, broad training methods, distributed execution and cloud-oriented deployment make it a strong candidate for integration with ODS.

The recommended architecture is not to make Axolotl an ODS core dependency. ODS should expose a stable Post-Training Service and register Axolotl as one interchangeable provider alongside LLaMA-Factory and future backends.

LEONES → ODS Post-Training Service → Axolotl provider → training job → artifact → validation/conversion → ODS Model Registry → ODS Runtime → benchmark → evidence → LEONES.

## Why Axolotl fits ODS

Current Axolotl documentation describes support for supervised fine-tuning and pretraining; full fine-tuning, LoRA and QLoRA; preference methods including DPO, IPO, KTO and ORPO; RL methods including GRPO/GDPO; reward-model workflows; multimodal language/vision and selected audio models; quantization and quantization-aware training; distributed training with FSDP2, DeepSpeed, Torchrun and Ray; local and remote datasets; Docker; inference; and LoRA merging.

See the official [Axolotl documentation](https://docs.axolotl.ai/) for the current capability matrix.

## Proposed ODS contract

ODS should expose a provider-neutral API. Axolotl YAML should remain an implementation detail of the provider and a provenance artifact, rather than becoming the public ODS API.

Conceptual operations:

- create a post-training job;
- inspect job status;
- cancel a job;
- retrieve logs;
- retrieve artifacts;
- request validation/benchmarking.

A provider capability record can advertise SFT, LoRA, QLoRA, full fine-tuning, DPO/IPO/KTO/ORPO, GRPO, reward modelling, multimodal, quantization and distributed execution.

ODS can then select a provider according to workload requirements and measured evidence instead of hard-coding a training framework.

## Job lifecycle

A useful ODS lifecycle is:

CREATE → PREPARE → RUN → VALIDATE → EXPORT → CONVERT (if required) → REGISTER → BENCHMARK → DEPLOY.

Axolotl owns the training stage. ODS should own scheduling, credentials, isolation, artifact handling, provenance, validation, registry integration and deployment.

## Container integration

Axolotl publishes official Docker images and documents GPU-enabled container execution. This maps naturally to an ODS job provider.

The provider should launch Axolotl per job with explicit dataset/model/cache mounts, scoped secrets, resource limits and an explicit artifact directory. Axolotl should not need to become a permanent ODS daemon.

## Artifacts and ODS runtime

Adapters should be first-class artifacts.

A representative path is:

base model + dataset → Axolotl → LoRA/QLoRA adapter → validation → optional merge → format conversion → ODS Model Registry → ODS inference runtime.

Compatibility between a training output and an ODS inference runtime must be validated explicitly. A Hugging Face/Transformers checkpoint should not automatically be assumed to be directly consumable by every ODS backend.

Where a runtime requires GGUF or another specific representation, conversion should be an explicit pipeline stage with recorded tool version, configuration and result.

## Datasets

ODS should mediate dataset access rather than allowing every training provider to define the platform data model.

The provider contract should receive a dataset identifier/version, reproducible source reference, format/schema, access policy, credentials when required, preprocessing configuration and provenance.

Production traces should not automatically become training data. Any such pipeline should pass through explicit policy, consent, filtering/redaction and provenance controls.

## Hybrid compute

Axolotl supports local and cloud-oriented execution, but cloud execution is not itself evidence of provider independence.

ODS should separate the Training Provider from the Compute Provider:

Training Provider: Axolotl.

Compute Provider: local machine, remote VM, Kubernetes, cloud GPU or another execution substrate.

This lets LEONES choose a training framework independently from where the workload runs.

## TangleML relationship

TangleML and Axolotl solve different layers.

TangleML = workflow orchestration.
Axolotl = training/post-training execution.
ODS = registry, deployment, inference and operations.

TangleML can orchestrate multi-stage pipelines while Axolotl performs the training stage. ODS remains the stable operational boundary.

## Advanced integration path

A staged roadmap is:

1. SFT + LoRA provider proof of concept.
2. QLoRA.
3. Adapter validation and merge.
4. Export/conversion into an ODS-supported inference format.
5. DPO and other preference optimization.
6. Multimodal post-training.
7. GRPO/RL workflows.
8. Integration with serving systems used during RL, including documented vLLM LoRA-sync paths where applicable.

Each stage should produce independent evidence rather than treating framework documentation as a measurement.

## Security and isolation

An ODS provider should enforce isolated execution, explicit dataset/model/artifact mounts, scoped credentials, controlled network access, resource limits, explicit artifact export, provenance of configuration/software versions, and retention/deletion policy.

The training provider should not silently gain access to unrelated ODS data or credentials.

## Evidence model

LEONES should distinguish estimated, reported, observed and measured evidence.

For Axolotl:
- reported = capability stated by Axolotl documentation;
- observed = behavior seen during an ODS integration run;
- measured = independently benchmarked result;
- estimated = planner prediction before execution.

Published Axolotl benchmarks or examples should not be recorded as LEONES measurements unless reproduced.

## Licensing and independence

The Axolotl repository declares an Apache-2.0 license. This supports evaluating Axolotl as an external provider, but Axolotl licensing does not determine the terms of base models, datasets, training data, checkpoints, cloud GPU providers, container registries or external services.

LEONES should record those separately.

## Recommended proof of concept

ODS API → Axolotl provider → isolated container → SFT + LoRA → adapter artifact → validation → optional merge → conversion if required → ODS Model Registry → ODS runtime → benchmark → evidence.

Success criteria should include reproducible job creation, provider isolation, artifact discovery, provenance capture, successful registration, validated inference, independent benchmarking and clean failure/cancellation behavior.

## Assessment

Axolotl is a first-line candidate for the ODS Post-Training Service provider layer.

Its strongest architectural properties for ODS are its container-friendly job model, configuration-driven reproducibility, broad post-training coverage, multimodal support and distributed/cloud execution options.

It should remain an interchangeable provider rather than become an ODS core dependency. LLaMA-Factory and Axolotl should be evaluated through the same ODS contract and selected according to workload capabilities and evidence.

## Official references

- [Axolotl documentation](https://docs.axolotl.ai/)
- [Axolotl GitHub repository](https://github.com/axolotl-ai-cloud/axolotl)
- [Installation](https://docs.axolotl.ai/docs/installation.html)
- [Docker](https://docs.axolotl.ai/docs/docker.html)
- [Quickstart](https://docs.axolotl.ai/docs/getting-started.html)
- [Dataset formats](https://docs.axolotl.ai/docs/dataset-formats/index.html)
- [CLI and cloud configuration](https://docs.axolotl.ai/docs/cli.html)
- [RLHF documentation](https://github.com/axolotl-ai-cloud/axolotl/blob/main/docs/rlhf.qmd)
