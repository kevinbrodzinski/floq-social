#!/usr/bin/env bash
set -euo pipefail

: "${RUNPOD_API:?RUNPOD_API secret required}"
RUNPOD_API_BASE="${RUNPOD_API_BASE:-https://rest.runpod.io/v1}"
TARGET_BRANCH="${TARGET_BRANCH:-rgi-ext-02g1-runpod-carrier-20260819}"
mkdir -p evidence
POD_ID=''
cleanup() {
  if [ -n "$POD_ID" ]; then
    code="$(curl -sS -o evidence/runpod_delete_response.txt -w '%{http_code}' -X DELETE -H "Authorization: Bearer ${RUNPOD_API}" "${RUNPOD_API_BASE}/pods/${POD_ID}" || true)"
    printf '%s\n' "$code" > evidence/runpod_delete_http_status.txt
  fi
}
trap cleanup EXIT

curl -fsSL https://github.com/runpod/runpodctl/releases/latest/download/runpodctl-linux-amd64 -o "$RUNNER_TEMP/runpodctl"
chmod +x "$RUNNER_TEMP/runpodctl"
mkdir -p "$HOME/.runpod"
touch "$HOME/.runpod/.runpod.yaml"
"$RUNNER_TEMP/runpodctl" config --apiKey "$RUNPOD_API" >/dev/null

# Do not override SSH_PUBLIC_KEY here. runpodctl manages an account-level SSH key;
# ssh info reports that exact key and whether RunPod sees it in the account.
jq -n '{name:"rgi-ext-02g1-one-shot",cloudType:"SECURE",computeType:"GPU",gpuCount:1,gpuTypeIds:["NVIDIA RTX A4000","NVIDIA GeForce RTX 3070","NVIDIA GeForce RTX 3080","NVIDIA RTX A4500","NVIDIA RTX A5000","NVIDIA L4","NVIDIA GeForce RTX 3090"],gpuTypePriority:"custom",imageName:"runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04",containerDiskInGb:20,volumeInGb:20,volumeMountPath:"/workspace",ports:["22/tcp"],supportPublicIp:true,interruptible:false,locked:false}' > "$RUNNER_TEMP/create_pod.json"
curl -sS -f -X POST -H "Authorization: Bearer ${RUNPOD_API}" -H 'Content-Type: application/json' --data-binary "@$RUNNER_TEMP/create_pod.json" "${RUNPOD_API_BASE}/pods" > "$RUNNER_TEMP/pod_created.json"
POD_ID="$(jq -r '.id // empty' "$RUNNER_TEMP/pod_created.json")"
[ -n "$POD_ID" ] || { jq '{id,name,costPerHr,adjustedCostPerHr,gpu,publicIp,portMappings}' "$RUNNER_TEMP/pod_created.json" > evidence/runpod_create_sanitized.json; exit 2; }
jq '{id,name,costPerHr,adjustedCostPerHr,gpu,publicIp,portMappings,image,machineId,lastStartedAt}' "$RUNNER_TEMP/pod_created.json" > evidence/runpod_create_sanitized.json

PUBLIC_IP=''; SSH_PORT=''; SSH_KEY=''; KEY_IN_ACCOUNT=''
for attempt in $(seq 1 90); do
  "$RUNNER_TEMP/runpodctl" ssh info "$POD_ID" > "$RUNNER_TEMP/ssh_info.json" 2> "$RUNNER_TEMP/ssh_info.err" || true
  PUBLIC_IP="$(jq -r '.ip // empty' "$RUNNER_TEMP/ssh_info.json" 2>/dev/null || true)"
  SSH_PORT="$(jq -r '.port // empty' "$RUNNER_TEMP/ssh_info.json" 2>/dev/null || true)"
  SSH_KEY="$(jq -r '.ssh_key.path // empty' "$RUNNER_TEMP/ssh_info.json" 2>/dev/null || true)"
  KEY_IN_ACCOUNT="$(jq -r '.ssh_key.in_account // false' "$RUNNER_TEMP/ssh_info.json" 2>/dev/null || true)"
  if [ -n "$PUBLIC_IP" ] && [ -n "$SSH_PORT" ] && [ -n "$SSH_KEY" ] && [ -f "$SSH_KEY" ] && [ "$KEY_IN_ACCOUNT" = "true" ]; then break; fi
  sleep 5
done
cp "$RUNNER_TEMP/ssh_info.json" evidence/runpod_ssh_info.json 2>/dev/null || true
cp "$RUNNER_TEMP/ssh_info.err" evidence/runpod_ssh_info.err 2>/dev/null || true
curl -sS -f -H "Authorization: Bearer ${RUNPOD_API}" "${RUNPOD_API_BASE}/pods/${POD_ID}" > "$RUNNER_TEMP/pod_status.json" || true
jq '{id,name,desiredStatus,lastStatusChange,publicIp,portMappings,gpu,machineId}' "$RUNNER_TEMP/pod_status.json" > evidence/runpod_final_status.json || true
if [ -z "$PUBLIC_IP" ] || [ -z "$SSH_PORT" ] || [ -z "$SSH_KEY" ] || [ ! -f "$SSH_KEY" ] || [ "$KEY_IN_ACCOUNT" != "true" ]; then
  exit 3
fi

printf '%s\n' "$PUBLIC_IP" > evidence/runpod_ssh_ip.txt
printf '%s\n' "$SSH_PORT" > evidence/runpod_ssh_port.txt
ssh-keygen -lf "$SSH_KEY" > evidence/runpod_ssh_key_fingerprint.txt
SSH_OPTS=(-i "$SSH_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -o IdentitiesOnly=yes)
for attempt in $(seq 1 40); do
  if ssh "${SSH_OPTS[@]}" "root@${PUBLIC_IP}" 'echo EXT02G1_SSH_READY' > evidence/ssh_probe.txt 2>&1; then break; fi
  sleep 5
done
grep -q EXT02G1_SSH_READY evidence/ssh_probe.txt

ssh "${SSH_OPTS[@]}" "root@${PUBLIC_IP}" "TARGET_BRANCH='${TARGET_BRANCH}' bash -s" <<'REMOTE'
set -euo pipefail
rm -rf /workspace/floq-social /workspace/rgi-ext-02g-native /workspace/.rgi-ext-02g-state
git clone --depth 1 --branch "$TARGET_BRANCH" https://github.com/kevinbrodzinski/floq-social.git /workspace/floq-social
cd /workspace/floq-social
python3 -m pip install --quiet --disable-pip-version-check 'cuda-python==11.8.3'
chmod +x rgi-ext-02g/runpod_quantum_helper.py rgi-ext-02g/runpod_workload_helper.py rgi-ext-02g/runpod_response_helper.py
export RGI_EXT02G_STATE_DIR=/workspace/.rgi-ext-02g-state
export RGI_EXT02G_NATIVE_STATE_DIR=/workspace/rgi-ext-02g-native
export RGI_EXT02G_QUANTUM_HELPER=/workspace/floq-social/rgi-ext-02g/runpod_quantum_helper.py
export RGI_EXT02G_WORKLOAD_HELPER=/workspace/floq-social/rgi-ext-02g/runpod_workload_helper.py
export RGI_EXT02G_RESPONSE_HELPER=/workspace/floq-social/rgi-ext-02g/runpod_response_helper.py
nvidia-smi > /workspace/RGI_EXT_02G1_NVIDIA_SMI.txt
python3 rgi-ext-02g/orchestrate.py --target "python3 rgi-ext-02g/gpu_target_nvidia.py" --resource-level 0.01 --out /workspace/RGI_EXT_02G1_RUNPOD_ADMISSION_RECEIPT.json > /workspace/RGI_EXT_02G1_ORCHESTRATOR_STDOUT.json
python3 - <<'PY'
import hashlib, json
from pathlib import Path
p=Path('/workspace/RGI_EXT_02G1_RUNPOD_ADMISSION_RECEIPT.json')
obj=json.loads(p.read_text())
Path('/workspace/RGI_EXT_02G1_RECEIPT_SHA256.txt').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n')
print(obj.get('result'))
PY
REMOTE

ssh "${SSH_OPTS[@]}" "root@${PUBLIC_IP}" 'tar -C /workspace -czf - RGI_EXT_02G1_RUNPOD_ADMISSION_RECEIPT.json RGI_EXT_02G1_ORCHESTRATOR_STDOUT.json RGI_EXT_02G1_NVIDIA_SMI.txt RGI_EXT_02G1_RECEIPT_SHA256.txt .rgi-ext-02g-state/last_execution.json .rgi-ext-02g-state/last_response.json .rgi-ext-02g-state/seal.json rgi-ext-02g-native/last_workload.json' > "$RUNNER_TEMP/evidence_remote.tar.gz"
tar -xzf "$RUNNER_TEMP/evidence_remote.tar.gz" -C "$RUNNER_TEMP"
cp "$RUNNER_TEMP/RGI_EXT_02G1_RUNPOD_ADMISSION_RECEIPT.json" evidence/
cp "$RUNNER_TEMP/RGI_EXT_02G1_ORCHESTRATOR_STDOUT.json" evidence/
cp "$RUNNER_TEMP/RGI_EXT_02G1_NVIDIA_SMI.txt" evidence/
cp "$RUNNER_TEMP/RGI_EXT_02G1_RECEIPT_SHA256.txt" evidence/
cp "$RUNNER_TEMP/.rgi-ext-02g-state/last_execution.json" evidence/
cp "$RUNNER_TEMP/.rgi-ext-02g-state/last_response.json" evidence/
cp "$RUNNER_TEMP/.rgi-ext-02g-state/seal.json" evidence/
cp "$RUNNER_TEMP/rgi-ext-02g-native/last_workload.json" evidence/native_last_workload.json
jq -e '.result == "GPU_EXECUTION_CARRIER_ADMITTED" and .theta_estimated == false and .brodzinski_class_assigned == false and .brodzinski_state_certified == false' evidence/RGI_EXT_02G1_RUNPOD_ADMISSION_RECEIPT.json
