#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORKER=ROOT/'rgi-ext-02g2'/'gpu_measurement_point.py'
EXECUTOR=ROOT/'rgi-ext-02g2a'/'measurement_executor_equiv.py'


def load_worker():
    spec=importlib.util.spec_from_file_location('gpu_measurement_point',WORKER)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


class FakeRun:
    def __init__(self, active: bool): self.active=active
    def __call__(self, cmd, **kwargs):
        if '--query-gpu=uuid,name,temperature.gpu,utilization.gpu,memory.used,memory.total' in cmd:
            return subprocess.CompletedProcess(cmd,0,'GPU-test, NVIDIA RTX A4000, 42, 0, 123, 16376\n','')
        if cmd[:4]==['nvidia-smi','-q','-d','PERFORMANCE']:
            state='Active' if self.active else 'Not Active'
            text=f'SW Thermal Slowdown : {state}\nHW Thermal Slowdown : Not Active\n'
            return subprocess.CompletedProcess(cmd,0,text,'')
        raise AssertionError(f'unexpected command: {cmd!r}')


def require_snapshot_contract(snapshot):
    required={'uuid','name','temperature_c','utilization_pct','memory_used_mib','memory_total_mib','thermal_or_hw_slowdown_active','slowdown_evidence','at_ns'}
    missing=required-set(snapshot)
    assert not missing, f'missing snapshot fields: {sorted(missing)}'
    assert type(snapshot['thermal_or_hw_slowdown_active']) is bool
    assert isinstance(snapshot['slowdown_evidence'],list)


def main():
    src=EXECUTOR.read_text()
    assert "obj['pressure_pre_snapshot']['thermal_or_hw_slowdown_active']" in src
    assert "obj['pressure_post_snapshot']['thermal_or_hw_slowdown_active']" in src
    mod=load_worker(); original=mod.subprocess.run
    try:
        mod.subprocess.run=FakeRun(False); inactive=mod.smi_snapshot(); require_snapshot_contract(inactive); assert inactive['thermal_or_hw_slowdown_active'] is False
        mod.subprocess.run=FakeRun(True); active=mod.smi_snapshot(); require_snapshot_contract(active); assert active['thermal_or_hw_slowdown_active'] is True
    finally:
        mod.subprocess.run=original
    print('RGI_EXT_02G2B_SCHEMA_CONTRACT_PASS')


if __name__=='__main__': main()
