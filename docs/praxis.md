# Praxis in This Workflow

Use Praxis after you establish a stable local inference profile.

## Good Fit
- Adversarial behavior tests
- Prompt leakage probes
- Agent/tool misuse scenarios
- Endpoint interaction abuse paths

## Not a Good Fit
- Token throughput benchmarking
- CPU/RAM micro-optimization benchmarking
- Kernel/runtime tuning

## Recommended Phase Placement
Run Praxis in a separate phase after performance tuning so you can isolate:
- runtime/inference regressions
- security-behavior regressions
