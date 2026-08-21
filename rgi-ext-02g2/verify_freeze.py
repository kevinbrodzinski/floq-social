#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
f = json.loads((root / "MEASUREMENT_ADMISSIBILITY_FREEZE.json").read_text())
receipt = root / "EXT02G1_SUCCESSFUL_CARRIER_RECEIPT.json"

assert hashlib.sha256(receipt.read_bytes()).hexdigest() == f["parent"]["carrier_receipt_sha256"]
r = json.loads(receipt.read_text())
assert r["result"] == "GPU_EXECUTION_CARRIER_ADMITTED"
assert r["identity"]["device_uuid"] == f["gpu_identity_lock"]["device_uuid"]
assert r["native_quantum"]["quantum"] == 2097152 == f["native_quantum"]["bytes"]
assert r["workload"]["payload"]["resource_coordinate"] == "GPU_DEVICE_MEMORY_FRACTION"
assert r["theta_estimated"] is False
assert r["brodzinski_class_assigned"] is False
assert r["brodzinski_state_certified"] is False

p = [float(x) for x in f["alpha_measurement_grid"]["requested_p"]]
assert len(p) == 15
assert all(0 < x <= 0.5 for x in p)
assert all(p[i] < p[i + 1] for i in range(14))
for k, x in enumerate(p):
    assert abs(x - 2 ** (-8 + k / 2)) < 1e-15

blocks = f["measurement_ordering"]["blocks"]
assert len(blocks) == 11
assert sum(b["kind"] == "WARMUP" for b in blocks) == 2
assert sum(b["kind"] == "RETAINED" for b in blocks) == 9
assert all(sorted(b["level_indices"]) == list(range(15)) for b in blocks)

a = f["alpha_estimator"]
assert a["gates"]["r2_min"] == 0.999
assert a["gates"]["alpha_ci_width_max"] == 0.03
assert a["gates"]["leave_one_level_out_alpha_range_max"] == 0.02

b = f["beta_estimator"]
assert b["equation"] == "beta = c/m"
assert b["beta_hat"] == 1.0
assert b["ci95"] == [1.0, 1.0]

t = f["theta_rule"]
assert t["equation"] == "Theta_hat = alpha_hat + beta_hat"

c = f["class_rule"]
assert c["superquadratic"] == "Theta_CI95_high < 0.97"
assert c["quadratic"] == "Theta_CI95_low > 1.03"

assert f["custody"] == {
    "alpha_measured": False,
    "beta_empirically_measured": False,
    "blind_outcome_collected": False,
    "boundary_contact_H_seen": False,
    "boundary_contact_K_seen": False,
    "class_assigned": False,
    "freeze_required_before_any_scientific_gpu_call": True,
    "scientific_sweep_executed": False,
    "theta_computed": False,
}
assert f["parent"]["no_repeat_carrier_admission_under_this_identity"] is True

print("RGI-EXT-02G.2 FREEZE VERIFIER: PASS")
