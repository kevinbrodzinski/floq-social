#!/usr/bin/env python3
import json, subprocess, sys, tempfile
from pathlib import Path

root=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as td:
    out=Path(td)/'receipt.json'
    r=subprocess.run([sys.executable,str(root/'orchestrate.py'),'--target',f'{sys.executable} {root/"gpu_target_nvidia.py"}','--out',str(out)],text=True,capture_output=True)
    assert r.returncode==0, r.stderr
    obj=json.loads(out.read_text())
    assert obj['result']=='GPU_TARGET_INELIGIBLE', obj
    assert obj['theta_estimated'] is False
    assert obj['brodzinski_class_assigned'] is False
    assert obj['brodzinski_state_certified'] is False
    assert obj['identity']['status']=='REFUSED'
    assert 'carrier_commitment_sha256' not in obj
print('RGI-EXT-02G NO-FABRICATION REFUSAL: PASS')
