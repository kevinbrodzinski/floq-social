# RGI-EXT-02G.2a — Prospective GPU Carrier Equivalence Amendment

## Purpose

This amendment exists because the first frozen EXT-02G.2 scientific authorization correctly terminated at `GPU_IDENTITY_MISMATCH_STOP_NO_MEASUREMENT`: RunPod supplied another NVIDIA RTX A4000 rather than the exact ephemeral physical GPU UUID used for EXT-02G.1 carrier admission.

The failed preflight is immutable evidence. It is not rescued, edited, or reinterpreted. No scientific measurement boundary was crossed in that run.

## Sole amendment

The exact-device-UUID admission rule is replaced prospectively by a frozen carrier-equivalence class. Physical UUID and PCI identity remain mandatory provenance fields but are no longer scientific admission criteria.

The admissible carrier class is `NVIDIA_RTX_A4000_CC86_16GB_NATIVE_2MIB_CUDA118_V1` and requires all of the following before any response measurement:

- NVIDIA RTX A4000 exactly;
- compute capability 8.6 exactly;
- native PyTorch device capacity 16,883,908,608 bytes exactly;
- nvidia-smi capacity 16,376 MiB exactly;
- exactly one visible GPU;
- no MIG or other partitioning;
- CUDA allocation granularity exactly 2 MiB;
- resource coordinate `GPU_DEVICE_MEMORY_FRACTION` unchanged;
- exact frozen container `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04`;
- `cuda-python==11.8.3`;
- CUDA 11.8 userspace semantics;
- NVIDIA Linux driver >= 520.61.05 and < 600.0.0;
- the already-frozen scientific measurement workload remains seeded FP32 1024x1024 with seed 260819;
- carrier compatibility is checked separately with the exact EXT-02G.1 admitted compute probe: FP32 `arange` left operand, FP32 constant `1/n` right operand, `n=1024`, checksum `1048574.625 +/- 0.001`;
- all environmental, thermal, idle-load, p-grid, ordering, repetition, estimator, Theta, class, and blind-outcome rules unchanged.

## One-shot order

Exactly one new GPU provisioning attempt is authorized under this amendment. The executor must record the fresh UUID, verify the entire equivalence class, native quantum, exact admitted-carrier checksum compatibility, and unchanged idle environmental gates, then seal either `CARRIER_EQUIVALENCE_CERTIFIED` or `GPU_CARRIER_EQUIVALENCE_REFUSED_STOP_NO_MEASUREMENT`.

Only `CARRIER_EQUIVALENCE_CERTIFIED` may open the already-frozen 15-level alpha sweep in the same one-shot execution. A failed equivalence preflight terminates the amendment identity with no retry or substitute GPU.

## Claim boundary

The equivalence certificate establishes only that a newly provisioned carrier satisfies the prospectively frozen hardware/runtime class required to execute EXT-02G.2. It does not itself establish alpha, beta, Theta, Brodzinski class, blind replication, contact behavior, or cross-hardware-family universality.
