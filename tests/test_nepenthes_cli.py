from __future__ import annotations
import csv,json,os,sqlite3,subprocess,sys
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"nepenthes.py"
def invoke(*args,env=None):
 return subprocess.run([sys.executable,str(SCRIPT),*args],capture_output=True,text=True,check=False,timeout=20,env=env)
def test_version_doctor():
 assert "NEPENTHES 0.1.0" in invoke("--version").stdout
 result=invoke("doctor");assert result.returncode==0 and "procfs" in json.loads(result.stdout)
def test_capture_bundle(tmp_path):
 result=invoke("run","--profile","smoke","--interval","0.1","--output",str(tmp_path),"--name","test","--",sys.executable,"-c","print('nepenthes-output')")
 assert result.returncode==0,result.stderr+result.stdout
 run=next(tmp_path.iterdir());m=json.loads((run/"manifest.json").read_text())
 assert m["status"]=="completed" and m["exit_code"]==0 and m["sample_count"]>=1
 assert m["engine_probe_activation"]["environment_variables_set"] is True
 assert m["event_merge"]["counts"]["host-events.jsonl"]>=2
 assert (run/"raw"/"host-events.jsonl").is_file()
 assert "nepenthes-output" in (run/"session.log").read_text()
 events=[json.loads(x) for x in (run/"raw"/"events.jsonl").read_text().splitlines()]
 assert events[0]["event_kind"]=="capture_started" and events[-1]["event_kind"]=="capture_finished"
 required={"schema_version","run_id","event_id","source","timestamp_unix_ns","monotonic_ns","request_id","event_kind","label","value0","value1","duration_ns","flags"}
 assert all(required.issubset(event) for event in events)
 assert all(event["schema_version"]=="1.0" and event["source"]=="nepenthes-host" for event in events)
 assert {event["run_id"] for event in events}=={m["run_id"]}
 assert len({event["event_id"] for event in events})==len(events)
 with (run/"data"/"samples.csv").open() as f:assert next(csv.DictReader(f)) is not None
 assert (run/"data"/"summary.json").is_file() and (run/"reports"/"index.html").is_file()
 with sqlite3.connect(run/"data"/"observations.sqlite") as db:
  assert db.execute("select count(*) from samples").fetchone()[0]>=1
  assert db.execute("select count(*) from events").fetchone()[0]>=2
 assert (run/"checksums.sha256").is_file()
 assert (run/"reports"/"report.md").is_file()
 verified=invoke("verify",str(run))
 assert verified.returncode==0,verified.stdout+verified.stderr
 assert json.loads(verified.stdout)["ok"] is True
 with (run/"session.log").open("a") as log:log.write("tampered\\n")
 invalid=invoke("verify",str(run))
 assert invalid.returncode==1 and "checksum mismatch" in invalid.stdout
def test_nonzero_exit_preserved(tmp_path):
 result=invoke("run","--profile","smoke","--interval","0.1","--output",str(tmp_path),"--",sys.executable,"-c","raise SystemExit(7)")
 assert result.returncode==7
 m=json.loads(next(tmp_path.iterdir()).joinpath("manifest.json").read_text())
 assert m["exit_code"]==7 and m["status"]=="command_failed"
def test_missing_executable():
 result=invoke("run","--","nepenthes-command-that-does-not-exist")
 assert result.returncode==2 and "ejecutable no encontrado" in result.stderr

def test_installer_installs_and_uninstalls_user_space(tmp_path):
 installer=Path(__file__).resolve().parents[1]/"scripts"/"install_nepenthes.sh"
 bindir=tmp_path/"bin";datadir=tmp_path/"data"
 env=os.environ.copy();env["NEPENTHES_DATA_DIR"]=str(datadir)
 installed=subprocess.run(["bash",str(installer),"--bin-dir",str(bindir)],capture_output=True,text=True,env=env,timeout=20)
 assert installed.returncode==0,installed.stderr+installed.stdout
 cli=bindir/"nepenthes";assert cli.is_file()
 assert (datadir/"scripts"/"nepenthes_nsys_import.py").is_file()
 assert (datadir/"db"/"migrations"/"002_nepenthes_observability.sql").is_file()
 version=subprocess.run([str(cli),"--version"],capture_output=True,text=True,timeout=10)
 assert version.returncode==0 and "NEPENTHES 0.1.0" in version.stdout
 removed=subprocess.run(["bash",str(installer),"--bin-dir",str(bindir),"--uninstall"],capture_output=True,text=True,env=env,timeout=10)
 assert removed.returncode==0 and not cli.exists()
 assert not (datadir/"scripts"/"nepenthes_nsys_import.py").exists()
 assert not (datadir/"db"/"migrations"/"002_nepenthes_observability.sql").exists()

def test_full_profile_wraps_command_with_nsys_when_required(tmp_path):
 bindir=tmp_path/"fake-bin";bindir.mkdir()
 fake=bindir/"nsys"
 fake.write_text("""#!/bin/sh
[ "$1" = "profile" ] || exit 91
shift
out=""
while [ "$#" -gt 0 ]; do
 case "$1" in
  --output=*) out=$(printf '%s' "$1" | cut -d= -f2-) ;;
  --*) ;;
  *) break ;;
 esac
 shift
done
"$@"
status=$?
python3 - "$out.sqlite" <<'PY'
import sqlite3,sys
db=sqlite3.connect(sys.argv[1])
db.execute("CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(start INTEGER,end INTEGER,correlationId INTEGER,globalPid INTEGER,processId INTEGER,deviceId INTEGER,contextId INTEGER,streamId INTEGER,nameId INTEGER)")
db.execute("INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES(10,20,3,44,44,0,0,7,1)")
db.execute("CREATE TABLE StringIds(id INTEGER,value TEXT)")
db.execute("INSERT INTO StringIds VALUES(1,'mock_kernel')")
db.commit()
db.close()
PY
exit "$status"
""")
 fake.chmod(0o755)
 env=os.environ.copy();env["PATH"]=str(bindir)+os.pathsep+env.get("PATH","")
 engine_code=("import json,os,time; e={'schema_version':'1.0','run_id':os.environ['NEPENTHES_RUN_ID'],'event_id':'engine-test-1','source':'test-engine','timestamp_unix_ns':time.time_ns(),'monotonic_ns':time.monotonic_ns(),'request_id':0,'event_kind':'request_start','label':'test.request','value0':1,'value1':2,'duration_ns':0,'flags':0}; open(os.environ['NEPENTHES_TRACE_JSONL'],'a').write(json.dumps(e)+chr(10)); print('nsys-wrapped')")
 result=invoke("run","--profile","full","--nsys","required","--interval","0.1","--output",str(tmp_path/"runs"),"--",
               sys.executable,"-c",engine_code,env=env)
 assert result.returncode==0,result.stderr+result.stdout
 run=next((tmp_path/"runs").iterdir());m=json.loads((run/"manifest.json").read_text())
 assert m["nsys"]["enabled"] is True
 assert "raw/nsys.sqlite" in m["nsys"]["outputs"]
 assert (run/"raw"/"nsys.sqlite").is_file()
 assert (run/"raw"/"engine-events.jsonl").is_file()
 assert m["event_merge"]["counts"]["engine-events.jsonl"]==1
 combined=[json.loads(line) for line in (run/"raw"/"events.jsonl").read_text().splitlines()]
 assert any(event["source"]=="test-engine" and event["source_event_id"]=="engine-test-1" for event in combined)
 assert len({event["event_id"] for event in combined})==len(combined)
 assert m["nsys"]["import"]["status"]=="imported"
 assert (run/"data"/"nsys-import.json").is_file()
 with sqlite3.connect(run/"data"/"nepenthes-import.sqlite") as db:
  assert db.execute("select count(*) from nepenthes_events").fetchone()[0]>=4
  assert db.execute("select count(*) from nsys_activities").fetchone()[0]==1
 assert "nsys-wrapped" in (run/"session.log").read_text()

def test_self_test_creates_and_verifies_bundle(tmp_path):
 result=invoke("self-test","--output",str(tmp_path))
 assert result.returncode==0,result.stdout+result.stderr
 assert len(list(tmp_path.iterdir()))==1
 assert "NEPENTHES_SELF_TEST_OK" in next(tmp_path.iterdir()).joinpath("session.log").read_text()


def test_merge_event_files_excludes_invalid_and_mismatched_records(tmp_path):
 import importlib.util
 spec=importlib.util.spec_from_file_location("nepenthes_cli",SCRIPT)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 raw=tmp_path/"raw";raw.mkdir()
 valid={"schema_version":"1.0","run_id":"run-1","event_id":"ok","source":"test"}
 mismatch=dict(valid,event_id="wrong-run",run_id="other")
 (raw/"host-events.jsonl").write_text(
  json.dumps(valid)+"\\n"+json.dumps(mismatch)+"\\n"+"{broken\\n",
  encoding="utf-8")
 result=module.merge_event_files(tmp_path,"run-1")
 rows=[json.loads(line) for line in (raw/"events.jsonl").read_text().splitlines()]
 assert [row["event_id"] for row in rows]==["ok"]
 assert result["counts"]["host-events.jsonl"]==1
 assert any("invalid_json" in warning for warning in result["warnings"])
 assert any("run_id_mismatch" in warning for warning in result["warnings"])


def test_stop_process_group_signals_group_and_waits(monkeypatch):
 import importlib.util
 spec=importlib.util.spec_from_file_location("nepenthes_cli",SCRIPT)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 calls=[]
 def fake_killpg(pgid,sig):
  calls.append((pgid,sig))
  if sig==0: raise ProcessLookupError
 monkeypatch.setattr(module.os,"killpg",fake_killpg)
 class Child:
  def wait(self,timeout=None): return 0
 module.stop_process_group(Child(),4321)
 assert calls==[(4321,module.signal.SIGINT),(4321,0)]
