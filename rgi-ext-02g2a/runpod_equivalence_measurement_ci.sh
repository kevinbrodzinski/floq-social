#!/usr/bin/env bash
set -euo pipefail
: "${RUNPOD_API:?RUNPOD_API secret required}"
RUNPOD_API_BASE="${RUNPOD_API_BASE:-https://rest.runpod.io/v1}"
TARGET_BRANCH="${TARGET_BRANCH:-rgi-ext-02g2a1-preobservation-retry-exec-20260819}"
mkdir -p evidence
POD_ID=''
cleanup(){
  if [ -n "$POD_ID" ]; then
    code="$(curl -sS -o evidence/runpod_delete_response.txt -w '%{http_code}' -X DELETE -H "Authorization: Bearer ${RUNPOD_API}" "${RUNPOD_API_BASE}/pods/${POD_ID}" || true)"
    printf '%s\n' "$code" > evidence/runpod_delete_http_status.txt
  fi
}
trap cleanup EXIT
curl -fsSL https://github.com/runpod/runpodctl/releases/latest/download/runpodctl-linux-amd64 -o "$RUNNER_TEMP/runpodctl"
chmod +x "$RUNNER_TEMP/runpodctl"
mkdir -p "$HOME/.runpod"; touch "$HOME/.runpod/.runpod.yaml"
"$RUNNER_TEMP/runpodctl" config --apiKey "$RUNPOD_API" >/dev/null
jq -n '{name:"rgi-ext-02g2a-one-shot",cloudType:"SECURE",computeType:"GPU",gpuCount:1,gpuTypeIds:["NVIDIA RTX A4000"],gpuTypePriority:"custom",imageName:"runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04",containerDiskInGb:20,volumeInGb:20,volumeMountPath:"/workspace",ports:["22/tcp"],supportPublicIp:true,interruptible:false,locked:false}' > "$RUNNER_TEMP/create_pod.json"
http_code="$(curl -sS -o "$RUNNER_TEMP/pod_created.json" -w '%{http_code}' -X POST -H "Authorization: Bearer ${RUNPOD_API}" -H 'Content-Type: application/json' --data-binary "@$RUNNER_TEMP/create_pod.json" "${RUNPOD_API_BASE}/pods" || true)"
printf '%s\n' "$http_code" > evidence/runpod_create_http_status.txt
if [[ "$http_code" =~ ^5[0-9][0-9]$ ]]; then
  cp "$RUNNER_TEMP/pod_created.json" evidence/runpod_create_response.txt 2>/dev/null || true
  python3 - "$http_code" > evidence/TERMINAL_RECEIPT.json <<'PY'
import hashlib,json,sys,time
code=sys.argv[1]
o={"artifact_type":"RGI_EXT_02G2A1_TERMINAL_RECEIPT","terminal_state":"PRE_OBSERVATION_PROVIDER_CREATE_FAILURE_STOP_NO_FURTHER_RETRY","stage":"RUNPOD_CREATE","http_status":code,"pod_id_issued":False,"gpu_observed":False,"carrier_equivalence_preflight_started":False,"scientific_measurement_started":False,"completed_at_ns":time.time_ns()}
o["receipt_sha256"]=hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
print(json.dumps(o,indent=2,sort_keys=True))
PY
  exit 0
fi
if [ "$http_code" -lt 200 ] || [ "$http_code" -ge 300 ]; then
  cp "$RUNNER_TEMP/pod_created.json" evidence/runpod_create_response.txt 2>/dev/null || true
  python3 - "$http_code" > evidence/TERMINAL_RECEIPT.json <<'PY'
import hashlib,json,sys,time
code=sys.argv[1]
o={"artifact_type":"RGI_EXT_02G2A1_TERMINAL_RECEIPT","terminal_state":"PRE_OBSERVATION_PROVIDER_CREATE_NON5XX_FAILURE_STOP_NO_FURTHER_RETRY","stage":"RUNPOD_CREATE","http_status":code,"pod_id_issued":False,"gpu_observed":False,"carrier_equivalence_preflight_started":False,"scientific_measurement_started":False,"completed_at_ns":time.time_ns()}
o["receipt_sha256"]=hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
print(json.dumps(o,indent=2,sort_keys=True))
PY
  exit 0
fi
POD_ID="$(jq -r '.id // empty' "$RUNNER_TEMP/pod_created.json")"
if [ -z "$POD_ID" ]; then
  cp "$RUNNER_TEMP/pod_created.json" evidence/runpod_create_response.txt 2>/dev/null || true
  python3 > evidence/TERMINAL_RECEIPT.json <<'PY'
import hashlib,json,time
o={"artifact_type":"RGI_EXT_02G2A1_TERMINAL_RECEIPT","terminal_state":"PRE_OBSERVATION_CREATE_RESPONSE_MISSING_POD_ID_STOP_NO_FURTHER_RETRY","stage":"RUNPOD_CREATE","pod_id_issued":False,"gpu_observed":False,"carrier_equivalence_preflight_started":False,"scientific_measurement_started":False,"completed_at_ns":time.time_ns()}
o["receipt_sha256"]=hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest();print(json.dumps(o,indent=2,sort_keys=True))
PY
  exit 0
fi
jq '{id,name,costPerHr,adjustedCostPerHr,gpu,publicIp,portMappings,image,machineId,lastStartedAt}' "$RUNNER_TEMP/pod_created.json" > evidence/runpod_create_sanitized.json
PUBLIC_IP='';SSH_PORT='';SSH_KEY='';KEY_IN_ACCOUNT=''
for attempt in $(seq 1 90); do
  "$RUNNER_TEMP/runpodctl" ssh info "$POD_ID" > "$RUNNER_TEMP/ssh_info.json" 2> "$RUNNER_TEMP/ssh_info.err" || true
  PUBLIC_IP="$(jq -r '.ip // empty' "$RUNNER_TEMP/ssh_info.json" 2>/dev/null || true)"
  SSH_PORT="$(jq -r '.port // empty' "$RUNNER_TEMP/ssh_info.json" 2>/dev/null || true)"
  SSH_KEY="$(jq -r '.ssh_key.path // empty' "$RUNNER_TEMP/ssh_info.json" 2>/dev/null || true)"
  KEY_IN_ACCOUNT="$(jq -r '.ssh_key.in_account // false' "$RUNNER_TEMP/ssh_info.json" 2>/dev/null || true)"
  if [ -n "$PUBLIC_IP" ] && [ -n "$SSH_PORT" ] && [ -f "$SSH_KEY" ] && [ "$KEY_IN_ACCOUNT" = true ]; then break; fi
  sleep 5
done
cp "$RUNNER_TEMP/ssh_info.json" evidence/runpod_ssh_info.json 2>/dev/null || true
if [ -z "$PUBLIC_IP" ] || [ -z "$SSH_PORT" ] || [ ! -f "$SSH_KEY" ]; then exit 3; fi
SSH_OPTS=(-i "$SSH_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -o IdentitiesOnly=yes)
for attempt in $(seq 1 40); do
  if ssh "${SSH_OPTS[@]}" "root@$PUBLIC_IP" 'echo EXT02G2A_SSH_READY' > evidence/ssh_probe.txt 2>&1; then break; fi
  sleep 5
done
grep -q EXT02G2A_SSH_READY evidence/ssh_probe.txt
ssh "${SSH_OPTS[@]}" "root@$PUBLIC_IP" "TARGET_BRANCH='${TARGET_BRANCH}' bash -s" <<'REMOTE'
set -euo pipefail
rm -rf /workspace/floq-social /workspace/ext02g2a-evidence
git clone --depth 1 --branch "$TARGET_BRANCH" https://github.com/kevinbrodzinski/floq-social.git /workspace/floq-social
cd /workspace/floq-social
python3 -m pip install --quiet --disable-pip-version-check 'cuda-python==11.8.3'
python3 rgi-ext-02g2a/verify_amendment.py
python3 rgi-ext-02g2a1/verify_retry_freeze.py
python3 -m py_compile rgi-ext-02g2/gpu_measurement_common.py rgi-ext-02g2/gpu_measurement_point.py rgi-ext-02g2/measurement_executor.py rgi-ext-02g2a/equivalence_preflight.py rgi-ext-02g2a/measurement_executor_equiv.py
mkdir -p /workspace/ext02g2a-evidence
python3 rgi-ext-02g2a/equivalence_preflight.py --out /workspace/ext02g2a-evidence > /workspace/ext02g2a-evidence/equivalence_stdout.txt 2> /workspace/ext02g2a-evidence/equivalence_stderr.txt
state="$(python3 - <<'PY'
import json
print(json.load(open('/workspace/ext02g2a-evidence/EQUIVALENCE_CERTIFICATE.json'))['state'])
PY
)"
printf '%s\n' "$state" > /workspace/ext02g2a-evidence/EQUIVALENCE_STATE.txt
if [ "$state" = "CARRIER_EQUIVALENCE_CERTIFIED" ]; then
  set +e
  python3 rgi-ext-02g2a/measurement_executor_equiv.py --out /workspace/ext02g2a-evidence --certificate /workspace/ext02g2a-evidence/EQUIVALENCE_CERTIFICATE.json > /workspace/ext02g2a-evidence/measurement_stdout.txt 2> /workspace/ext02g2a-evidence/measurement_stderr.txt
  rc=$?
  set -e
  printf '%s\n' "$rc" > /workspace/ext02g2a-evidence/MEASUREMENT_EXECUTOR_EXIT_CODE.txt
fi
REMOTE
ssh "${SSH_OPTS[@]}" "root@$PUBLIC_IP" 'tar -C /workspace -czf - ext02g2a-evidence' > "$RUNNER_TEMP/ext02g2a.tgz"
tar -xzf "$RUNNER_TEMP/ext02g2a.tgz" -C "$RUNNER_TEMP"
cp -a "$RUNNER_TEMP/ext02g2a-evidence/." evidence/
[ -f evidence/EQUIVALENCE_CERTIFICATE.json ]
state="$(jq -r '.state' evidence/EQUIVALENCE_CERTIFICATE.json)"
if [ "$state" = "CARRIER_EQUIVALENCE_CERTIFIED" ]; then
  [ -f evidence/TERMINAL_RECEIPT.json ]
  jq -e '.terminal_state=="NATIVE_QUANTUM_MISMATCH_STOP_NO_MEASUREMENT" or .terminal_state=="ENVIRONMENT_INADMISSIBLE_STOP_NO_ESTIMATE" or .terminal_state=="ALPHA_UNIDENTIFIABLE_STOP_NO_THETA" or .terminal_state=="BETA_GEOMETRY_PROFILE_INAPPLICABLE_STOP_NO_THETA" or .terminal_state=="AMBIGUOUS_STOP_BEFORE_BLIND_OUTCOME" or .terminal_state=="PREDICTION_LOCKED_HOLDOUT_UNOPENED"' evidence/TERMINAL_RECEIPT.json >/dev/null
else
  jq -e '.terminal_state=="GPU_CARRIER_EQUIVALENCE_REFUSED_STOP_NO_MEASUREMENT" and .scientific_measurement_started==false' evidence/TERMINAL_RECEIPT.json >/dev/null
fi
