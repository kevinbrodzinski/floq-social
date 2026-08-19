package main

import (
  "crypto/ed25519"
  "crypto/rand"
  "encoding/base64"
  "encoding/json"
  "fmt"
  "os"
  "os/exec"
  "runtime"
  "time"
)

type Probe struct {
  Subject string `json:"subject"`
  Architecture string `json:"architecture"`
  ProfileSHA string `json:"profile_sha256"`
  PassCount int `json:"pass_count"`
  Total int `json:"total"`
  Status string `json:"status"`
  State map[string]any `json:"state"`
}
func load(path string) Probe { b,e:=os.ReadFile(path); if e!=nil{panic(e)}; var p Probe; if e=json.Unmarshal(b,&p);e!=nil{panic(e)}; return p }
func stateID(p Probe) string { v,_:=p.State["state_id"].(string); return v }
func hasBrodzinski(p Probe) bool { _,ok:=p.State["brodzinski"]; return ok }
func stateStatus(p Probe) string { v,_:=p.State["status"].(string); return v }
func reasonCode(p Probe) string { r,_:=p.State["reason"].(map[string]any); v,_:=r["code"].(string); return v }
func uname() string { b,e:=exec.Command("uname","-a").CombinedOutput(); if e!=nil{return string(b)}; return string(b) }

func main(){
  if len(os.Args)!=4 { panic("usage: evaluator X64.json ARM64.json OUT.json") }
  x:=load(os.Args[1]); a:=load(os.Args[2])
  checks:=map[string]bool{
    "x64_blackbox_pass":x.Status=="PASS" && x.PassCount==x.Total,
    "arm64_blackbox_pass":a.Status=="PASS" && a.PassCount==a.Total,
    "same_profile":x.ProfileSHA!="" && x.ProfileSHA==a.ProfileSHA,
    "different_architectures":x.Architecture=="x86_64" && a.Architecture=="arm64",
    "x64_unknown":stateStatus(x)=="UNKNOWN",
    "arm64_unknown":stateStatus(a)=="UNKNOWN",
    "x64_no_theta":!hasBrodzinski(x),
    "arm64_no_theta":!hasBrodzinski(a),
    "x64_reason":reasonCode(x)=="MEASUREMENT_NOT_EXECUTED",
    "arm64_reason":reasonCode(a)=="MEASUREMENT_NOT_EXECUTED",
  }
  pass:=true; for _,v:=range checks { if !v {pass=false} }
  result:="REAL_HARDWARE_TYPED_REFUSAL_INTEROPERABILITY_PASS"; if !pass { result="FAIL" }
  payload:=fmt.Sprintf("RGI-EXT-02A-EVALUATOR-1\nprofile_sha256=%s\nx64_state_id=%s\narm64_state_id=%s\nresult=%s\n",x.ProfileSHA,stateID(x),stateID(a),result)
  pub,priv,e:=ed25519.GenerateKey(rand.Reader); if e!=nil{panic(e)}; sig:=ed25519.Sign(priv,[]byte(payload))
  out:=map[string]any{
    "trial":"RGI-EXT-02A","stage":"REAL_HETEROGENEOUS_HARDWARE_TYPED_REFUSAL","result":result,
    "profile_sha256":x.ProfileSHA,"x64_state_id":stateID(x),"arm64_state_id":stateID(a),"checks":checks,
    "evaluator":map[string]any{"implementation":"go-independent-evaluator","go_version":runtime.Version(),"os":runtime.GOOS,"arch":runtime.GOARCH,"uname":uname(),"evaluated_at":time.Now().UTC().Format(time.RFC3339Nano)},
    "public_key_base64":base64.StdEncoding.EncodeToString(pub),"signature_base64":base64.StdEncoding.EncodeToString(sig),"signed_payload_base64":base64.StdEncoding.EncodeToString([]byte(payload)),
    "claim_boundary":"Demonstrates RGI interoperability and scientifically correct UNKNOWN/refusal semantics on real heterogeneous hosted hardware. It does not certify a numeric Brodzinski Number or real GPU Resource Geometry.",
  }
  b,_:=json.MarshalIndent(out,"","  "); b=append(b,'\n'); if e=os.WriteFile(os.Args[3],b,0644);e!=nil{panic(e)}; fmt.Print(string(b)); if !pass {os.Exit(2)}
}
