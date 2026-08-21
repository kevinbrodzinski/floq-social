# RGI-EXT-02G — Pluggable Real-GPU Execution Target

Status: execution-carrier candidate. RGI v1.0 remains frozen.

## Purpose

This branch adds no Resource Geometry theory, estimator, classifier, certification rule, or runtime intelligence. It defines only the execution-carrier boundary needed to attach an independently provisioned discrete-GPU endpoint to the frozen RGI v1.0 / v0.9 certification pipeline.

## Required command interface

A target executable MUST implement exactly these public commands:

1. `identity`
2. `resource-inventory`
3. `native-quantum`
4. `run-workload --resource-level <p>`
5. `collect-response`
6. `seal-raw-outcome`

Each command emits exactly one UTF-8 JSON object to stdout and exits nonzero on refusal/failure.

## Admission rule

A target is MEASUREMENT_ELIGIBLE only if all are true:

- `identity.target_kind == DISCRETE_GPU`
- `identity.discrete_gpu == true`
- stable device identity is present
- native resource inventory identifies a primary GPU resource and positive capacity
- native quantum is positive and is supported by a native source
- workload execution at a requested resource level is confirmed by the target
- response collection refers to the exact workload execution receipt
- raw outcome sealing binds the exact response bytes with SHA-256

Otherwise the carrier MUST terminate with a typed refusal and MUST NOT fabricate alpha, beta, Theta, Brodzinski Class, or a certified Brodzinski State.

## Provider neutrality

The command contract is provider-neutral. Provider adapters MAY use NVIDIA CUDA/NVML/nvidia-smi, ROCm, a vendor SDK, a remote job API, SSH, Kubernetes device plugins, or an external lab runner, but provider-specific details remain behind this interface.

## Claim boundary

Passing this carrier contract proves only that a real discrete-GPU endpoint is natively accessible and can execute the frozen measurement workload interface. It does not by itself prove a valid Resource Geometry measurement channel, alpha, beta, Theta, Brodzinski Class, or scientific certification.
