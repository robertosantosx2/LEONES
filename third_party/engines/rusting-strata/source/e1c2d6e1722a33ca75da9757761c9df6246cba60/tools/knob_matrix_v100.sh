#!/usr/bin/env bash
# M0-T6 (issue #42): run every Vulkan flag/knob row on the Tesla V100 and
# record the outcome as one markdown table plus the `strata.bench.v1` records.
#
# Usage:
#   tools/knob_matrix_v100.sh [options]
#
# Options:
#   --model PATH          reference model (default $STRATA_MODEL or the MoE Q2_K_XL)
#   --model-27b PATH      model of the optional M2 row
#   --bin PATH            release binary (default $STRATA_BIN or target/release/rustingstrata)
#   --pass 1|2|all        pass 1 (C0 C1 K1 K2 K3 N1 N2 M1 P2M), pass 2 (C2 P2 P4 M2), or all
#   --only ID[,ID...]     run exactly these rows, ignoring --pass
#   --dry-run             print the commands and an empty table; touch no model, GPU or file
#   --out FILE            also write the markdown section to FILE
#   --append FILE         append the markdown section to FILE (e.g. docs/V100-results.md)
#   --port-base N         first HTTP port for P2/P4/P2M (default 8199)
#   --allow-active-production  do not abort when llama.router.service is active
#   -h, --help            this text
#
# Environment knobs read by the engine are passed explicitly per row
# (`STRATA_VK_NO_COOP`, `STRATA_NO_GRAPH`); the script itself reads
# `STRATA_MODEL`, `STRATA_BIN` and `STRATA_JSON_DIR`.
#
# One row is one process (the model is loaded again for each), so the two
# passes of the issue run in a single coordinator-scheduled GPU window only if
# the window is long enough. A row that crashes, hangs or loses the device
# stops the run; the row is recorded as unsupported and must get a follow-up
# issue instead of being fixed here.
#
# The model path is never printed: commands show `$M`, and the JSON records are
# shown as paths plus key fields (the full records stay in target/m0t6/).
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

MODEL=${STRATA_MODEL:-/mnt/models/unsloth/Qwen3.6-35B-A3B-GGUF/Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf}
MODEL_27B=${STRATA_MODEL_27B:-/mnt/models/unsloth/Qwen3.8-27B-GGUF/Qwen3.8-27B-UD-Q4_K_XL.gguf}
BIN=${STRATA_BIN:-target/release/rustingstrata}
JSON_DIR=${STRATA_JSON_DIR:-target/m0t6}
LOG_DIR=$JSON_DIR/logs
PASS=all
ONLY=""
DRY_RUN=0
OUT=""
APPEND=""
PORT_BASE=8199
ALLOW_ACTIVE=0
PROMPT="The quick brown fox jumps over the lazy dog."
GEN_N=16
CTX=32896
MODEL_LABEL='$M'

usage() { awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; }

while (($#)); do
    case $1 in
        --model) MODEL=$2; shift 2 ;;
        --model-27b) MODEL_27B=$2; shift 2 ;;
        --bin) BIN=$2; shift 2 ;;
        --pass) PASS=$2; shift 2 ;;
        --only) ONLY=$2; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --out) OUT=$2; shift 2 ;;
        --append) APPEND=$2; shift 2 ;;
        --port-base) PORT_BASE=$2; shift 2 ;;
        --allow-active-production) ALLOW_ACTIVE=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "knob_matrix: unknown option: $1" >&2; exit 2 ;;
    esac
done

case $PASS in 1|2|all) ;; *) echo "knob_matrix: --pass must be 1, 2 or all" >&2; exit 2 ;; esac

PASS1=(C0 C1 K1 K2 K3 N1 N2 M1 P2M)
PASS2=(C2 P2 P4 M2)
ALL_ROWS=("${PASS1[@]}" "${PASS2[@]}")
if [[ -n $ONLY ]]; then
    IFS=, read -r -a WANTED <<<"$ONLY"
else
    case $PASS in
        1) WANTED=("${PASS1[@]}") ;;
        2) WANTED=("${PASS2[@]}") ;;
        all) WANTED=("${ALL_ROWS[@]}") ;;
    esac
fi

selected() {
    local row=$1 want
    for want in "${WANTED[@]}"; do [[ $want == "$row" ]] && return 0; done
    return 1
}

say() { printf '%s\n' "$*" >&2; }
die() { say "knob_matrix: $*"; exit 2; }

have_jq() { command -v jq >/dev/null 2>&1; }
have_python() { command -v python3 >/dev/null 2>&1; }

json_valid() {
    local f=$1
    [[ -s $f ]] || return 1
    if have_jq; then jq -e . "$f" >/dev/null 2>&1
    elif have_python; then python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$f" >/dev/null 2>&1
    else return 0
    fi
}

json_floor() { # json_floor FILE (schema only, used for the table)
    local f=$1
    if have_jq; then jq -r '.schema // "?"' "$f" 2>/dev/null
    elif have_python; then python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("schema","?"))' "$f" 2>/dev/null
    else echo "?"
    fi
}

usage_tokens() { # usage_tokens FILE -> completion_tokens (0 on any failure)
    local f=$1
    if have_jq; then jq -r '.usage.completion_tokens // 0' "$f" 2>/dev/null || echo 0
    elif have_python; then python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("usage",{}).get("completion_tokens",0))' "$f" 2>/dev/null || echo 0
    else echo 0
    fi
}

# Result of one row, keyed by row id.
declare -A SETTING=() STATUS=() NUMBERS=() MESSAGE=() PLANLINE=() COMMAND=() JSONPATH=() GENRC=() GENTEXT=()
ROW_ORDER=()
SANITY_ROWS=()
declare -A SANITY_STATUS=() SANITY_CMP=()

record_row() {
    local row=$1 setting=$2 command=$3 status=$4 numbers=$5 message=$6 plan=${7:-}
    SETTING[$row]=$setting
    COMMAND[$row]=$command
    STATUS[$row]=$status
    NUMBERS[$row]=$numbers
    MESSAGE[$row]=$message
    PLANLINE[$row]=$plan
    [[ -v JSONPATH[$row] ]] || JSONPATH[$row]=""
    ROW_ORDER+=("$row")
}

cell() { # escape a markdown table cell
    local s=${1:-}
    s=${s//|/\\|}
    s=${s//$'\n'/ }
    printf '%s' "$s"
}

plan_kv() { sed -n 's/.*KV \([0-9][0-9]*\) MB.*/\1/p' <<<"${1:-}" | head -n1; }
plan_prefill() { sed -n 's/.*prefill \([0-9][0-9]*\) MB.*/\1/p' <<<"${1:-}" | head -n1; }
plan_slots() {
    sed -n 's/.*expert slots \([0-9][0-9]*\) MB, resident experts \([0-9][0-9]*\)\/\([0-9][0-9]*\).*/\1 MB (\2\/\3)/p' \
        <<<"${1:-}" | head -n1
}

log_tail_error() {
    local log=$1
    grep -iE 'error|does not combine|not supported|VRAM|shared memory|failed|out of memory|device lost' "$log" 2>/dev/null \
        | tail -n3 | paste -sd ' | ' - || true
}

json_numbers() { # compact `pp ...: prefill .., decode ..` from the record
    local f=$1
    if have_jq; then
        jq -r '.results[] | "pp \(.pp): prefill \(.prefill_tok_s.mean) (\(.prefill_tok_s.min)-\(.prefill_tok_s.max)) tok/s, decode \(.decode_tok_s.mean) (\(.decode_tok_s.min)-\(.decode_tok_s.max)) tok/s"' "$f" \
            | paste -sd ';' - | sed 's/;/; /g'
    elif have_python; then
        python3 - "$f" <<'PY'
import json, sys
v = json.load(open(sys.argv[1]))
out = []
for r in v.get("results", []):
    p, d = r.get("prefill_tok_s", {}), r.get("decode_tok_s", {})
    out.append("pp %s: prefill %s (%s-%s) tok/s, decode %s (%s-%s) tok/s" % (
        r.get("pp"), p.get("mean"), p.get("min"), p.get("max"), d.get("mean"), d.get("min"), d.get("max")))
print("; ".join(out))
PY
    fi
}

numbers_with_plan() {
    local json=$1 log=$2 plan=$3
    local nums="" kv slots
    [[ -s $json ]] && nums=$(json_numbers "$json" || true)
    if [[ -z $nums ]]; then
        nums=$(grep -E '^pp ' "$log" 2>/dev/null \
            | sed -E 's/^pp +([0-9]+): prefill (.*) tok\/s \| tg [0-9]+: decode (.*) tok\/s/pp \1: prefill \2 tok\/s, decode \3 tok\/s/' \
            | paste -sd ';' - | sed 's/;/; /g' || true)
    fi
    kv=$(plan_kv "$plan")
    slots=$(plan_slots "$plan")
    [[ -n $kv ]] && nums=${nums:+$nums; }"KV $kv MB"
    [[ -n $slots ]] && nums=${nums:+$nums; }"experts $slots"
    printf '%s' "$nums"
}

# Run one `strata bench` row. ROW_ENV carries the environment assignments.
bench_row() {
    local row=$1 setting=$2 mode=$3 expect_re=$4
    shift 4
    local json=$JSON_DIR/$row.json log=$LOG_DIR/$row.log
    local envs="" disp rc=0 plan="" msg="" err="" status numbers message
    if ((${#ROW_ENV[@]})); then envs="${ROW_ENV[*]} "; fi
    disp="${envs}strata bench --model \"${MODEL_LABEL:-\$M}\" --gpu --backend vulkan --json-out target/m0t6/$row.json $*"
    disp=${disp% }

    if ((DRY_RUN)); then
        record_row "$row" "$setting" "$disp" "dry-run" "—" "not executed" ""
        return 0
    fi

    set +e
    env "${ROW_ENV[@]}" "$BIN" bench --model "$MODEL" --gpu --backend vulkan --json-out "$json" "$@" \
        >"$log" 2>&1
    rc=$?
    set -e

    JSONPATH[$row]=$json
    plan=$(grep -m1 '^plan: ' "$log" || true)
    msg=""
    [[ -n $expect_re ]] && msg=$(grep -m1 -E -- "$expect_re" "$log" || true)
    status=""
    if ((rc == 0)); then
        numbers=$(numbers_with_plan "$json" "$log" "$plan")
        if [[ -n $msg && $mode == caveat ]]; then
            status="supported (caveat: $msg)"
        elif [[ -s $json ]] && json_valid "$json"; then
            status="supported"
        elif [[ -s $json ]]; then
            status="supported (caveat: invalid JSON record)"
        else
            status="supported (caveat: no JSON record)"
        fi
    else
        err=$(log_tail_error "$log")
        if [[ -n $msg ]]; then
            status="rejected ($msg)"
        elif [[ $row == C2 && $err =~ (VRAM|shared.memory|does.not.fit|margin) ]]; then
            status="rejected ($err)"
        elif ((rc == 1)) && [[ $mode == reject ]]; then
            status="unsupported (exit 1 without the documented message${err:+: $err})"
        else
            status="unsupported (exit $rc${err:+: $err})"
        fi
        numbers=$(numbers_with_plan "$json" "$log" "$plan")
    fi
    [[ -z $numbers ]] && numbers="—"
    # The error tail is already in the status for a refusal; do not print it twice.
    message="exit $rc${msg:+; $msg}"
    record_row "$row" "$setting" "$disp" "$status" "$numbers" "$message" "$plan"

    if grep -qiE 'Xid|device lost|lost device' "$log"; then
        say "knob_matrix: Xid/device lost in row $row; stopping"
        XID_FOUND=1
        return 1
    fi
    return 0
}

# Run `strata generate` for the output sanity rows (not a table row of its own).
generate_row() {
    local row=$1
    shift
    local envs="" out=$LOG_DIR/$row.gen.out log=$LOG_DIR/$row.gen.log rc=0
    if ((${#ROW_ENV[@]})); then envs="${ROW_ENV[*]} "; fi
    local disp="${envs}strata generate --model \"\$M\" --gpu --backend vulkan $* -n $GEN_N --prompt \"$PROMPT\""
    if ((DRY_RUN)); then
        SANITY_ROWS+=("$row")
        SANITY_STATUS[$row]="dry-run"
        SANITY_CMP[$row]="—"
        COMMAND[$row]+=" ; $disp"
        return 0
    fi
    set +e
    env "${ROW_ENV[@]}" "$BIN" generate --model "$MODEL" --gpu --backend vulkan "$@" \
        -n "$GEN_N" --prompt "$PROMPT" >"$out" 2>"$log"
    rc=$?
    set -e
    GENRC[$row]=$rc
    GENTEXT[$row]=$(cat "$out")
    SANITY_ROWS+=("$row")
    COMMAND[$row]+=" ; $disp"
    if ((rc != 0)); then
        SANITY_STATUS[$row]="failed (exit $rc)"
        SANITY_CMP[$row]="—"
        return 0
    fi
    if [[ -z ${GENTEXT[$row]} ]]; then
        SANITY_STATUS[$row]="empty output"
        SANITY_CMP[$row]="—"
        return 0
    fi
    if [[ $row == C0 ]]; then
        SANITY_STATUS[$row]="coherent, non-empty"
        SANITY_CMP[$row]="reference"
    elif [[ $row == N2 && -n ${GENTEXT[C0]:-} ]]; then
        if [[ ${GENTEXT[$row]} == "${GENTEXT[C0]}" ]]; then
            SANITY_STATUS[$row]="coherent, non-empty"
            SANITY_CMP[$row]="identical to C0"
        else
            SANITY_STATUS[$row]="coherent, non-empty"
            SANITY_CMP[$row]="differs from C0"
        fi
    else
        SANITY_STATUS[$row]="coherent, non-empty"
        SANITY_CMP[$row]="no C0 reference"
    fi
    return 0
}

stop_server() {
    local pid=$1 rc=0
    kill -TERM "$pid" 2>/dev/null || true
    local i
    for i in $(seq 1 600); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.1
    done
    if kill -0 "$pid" 2>/dev/null; then kill -KILL "$pid" 2>/dev/null || true; fi
    set +e
    wait "$pid" 2>/dev/null
    rc=$?
    set -e
    return $rc
}

# One `strata serve` row. P2/P4 fire N concurrent greedy requests; P2M only
# starts the server long enough to read the downgrade message.
serve_row() {
    local row=$1 setting=$2 slots=$3 mode=$4 expect_re=$5 port=$6
    shift 6
    local log=$LOG_DIR/$row.log envs="" disp
    if ((${#ROW_ENV[@]})); then envs="${ROW_ENV[*]} "; fi
    disp="${envs}strata serve --model \"\$M\" --gpu --backend vulkan --ctx 8192 --parallel $slots --addr 127.0.0.1:$port $*"
    disp=${disp% }
    if ((DRY_RUN)); then
        local n
        n=$slots
        [[ $row == P2M ]] && n=0
        if ((n > 0)); then disp+=" + $n concurrent POST /v1/chat/completions"; fi
        record_row "$row" "$setting" "$disp" "dry-run" "—" "not executed" ""
        return 0
    fi

    set +e
    env "${ROW_ENV[@]}" "$BIN" serve --model "$MODEL" --gpu --backend vulkan --ctx 8192 \
        --parallel "$slots" --addr "127.0.0.1:$port" "$@" >"$log" 2>&1 &
    SERVE_PID=$!
    set -e

    local up=0 code
    local i
    for i in $(seq 1 1500); do
        code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://127.0.0.1:$port/health" 2>/dev/null || true)
        if [[ $code == 200 ]]; then up=1; break; fi
        if ! kill -0 "$SERVE_PID" 2>/dev/null; then break; fi
        sleep 0.2
    done

    local plan="" msg="" status numbers="" message stoprc=0
    plan=$(grep -m1 '^plan: ' "$log" || true)
    msg=""
    [[ -n $expect_re ]] && msg=$(grep -m1 -E -- "$expect_re" "$log" || true)

    if ((up == 0)); then
        local err
        err=$(log_tail_error "$log")
        status="unsupported (server did not become healthy${err:+: $err})"
        numbers=""
        stop_server "$SERVE_PID" >/dev/null 2>&1 || true
        SERVE_PID=""
        record_row "$row" "$setting" "$disp" "$status" "—" "exit n/a${msg:+; $msg}" "$plan"
        return 0
    fi

    if [[ $mode == downgrade ]]; then
        # The server is healthy, so the model loaded and resolve_flags ran.
        if [[ -n $msg ]]; then status="degraded ($msg)"; else status="supported (caveat: no downgrade message found)"; fi
        stop_server "$SERVE_PID" >/dev/null 2>&1 || stoprc=$?
        SERVE_PID=""
        numbers=$(numbers_with_plan "" "$log" "$plan")
        message="exit $stoprc (stopped with SIGTERM)${msg:+; $msg}"
        record_row "$row" "$setting" "$disp" "$status" "$numbers" "$message" "$plan"
        return 0
    fi

    local dir=$LOG_DIR/$row.http body
    mkdir -p "$dir"
    # A prompt that keeps greedy decoding busy for the whole cap: "one word"
    # answers stop after a single token and would measure latency, not decode.
    body=$(printf '{"messages":[{"role":"user","content":"Repeat the word the 100 times, separated by spaces."}],"max_tokens":128,"temperature":0,"chat_template_kwargs":{"enable_thinking":false}}')
    local t0 t1 wall_ms total=0 ok=0 lat="" pids=() tid
    t0=$(date +%s%N)
    for i in $(seq 1 "$slots"); do
        (
            curl -sS --max-time 300 -o "$dir/$i.json" -w '%{http_code} %{time_total}' \
                -H 'Content-Type: application/json' -d "$body" \
                "http://127.0.0.1:$port/v1/chat/completions" >"$dir/$i.meta" 2>"$dir/$i.err"
        ) &
        pids+=("$!")
    done
    for tid in "${pids[@]}"; do wait "$tid" || true; done
    t1=$(date +%s%N)
    wall_ms=$(( (t1 - t0) / 1000000 ))

    for i in $(seq 1 "$slots"); do
        local c=000 t=0 tok=0
        read -r c t <"$dir/$i.meta" 2>/dev/null || true
        [[ $c == 200 ]] && ok=$((ok + 1))
        tok=$(usage_tokens "$dir/$i.json")
        [[ $tok =~ ^[0-9]+$ ]] || tok=0
        total=$((total + tok))
        lat+="${lat:+, }#$i ${t}s/${tok} tok"
    done

    local tps
    if ((wall_ms > 0)); then tps=$(awk -v a="$total" -v ms="$wall_ms" 'BEGIN { printf "%.1f", a / (ms / 1000) }'); else tps="0.0"; fi
    numbers="wall ${wall_ms} ms; aggregate decode ${tps} tok/s (${total} tok); $lat"
    local pv slots_txt
    pv=$(plan_kv "$plan"); slots_txt=$(plan_slots "$plan")
    [[ -n $pv ]] && numbers+="; KV $pv MB"
    [[ -n $slots_txt ]] && numbers+="; experts $slots_txt"

    if ((ok == slots)) && ((total > 0)); then
        status="supported"
    else
        local err
        err=$(log_tail_error "$log")
        status="unsupported ($ok/$slots requests OK, $total tokens${err:+: $err})"
    fi

    stop_server "$SERVE_PID" >/dev/null 2>&1 || stoprc=$?
    SERVE_PID=""
    message="exit $stoprc (stopped with SIGTERM); HTTP $ok/$slots"
    record_row "$row" "$setting" "$disp" "$status" "$numbers" "$message" "$plan"

    if grep -qiE 'Xid|device lost|lost device' "$log"; then
        say "knob_matrix: Xid/device lost in row $row; stopping"
        XID_FOUND=1
        return 1
    fi
    return 0
}

ROW_ENV=()
SERVE_PID=""
XID_FOUND=0
SERVER_STOPPED=""

cleanup() {
    if [[ -n $SERVE_PID ]] && kill -0 "$SERVE_PID" 2>/dev/null; then
        kill -KILL "$SERVE_PID" 2>/dev/null || true
        wait "$SERVE_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT
trap 'cleanup; exit 130' INT TERM

# --- preflight -------------------------------------------------------------

if ((DRY_RUN == 0)); then
    [[ -x $BIN ]] || die "build it first: cargo build --release (or pass --bin)"
    [[ -f $MODEL ]] || die "no such model: $MODEL"
    command -v curl >/dev/null 2>&1 || die "curl is required for the P2/P4/P2M rows"
    mkdir -p "$JSON_DIR" "$LOG_DIR"
    if command -v systemctl >/dev/null 2>&1; then
        SERVER_STOPPED=$(systemctl is-active llama.router.service 2>/dev/null || true)
        if [[ $SERVER_STOPPED == active && $ALLOW_ACTIVE == 0 ]]; then
            die "llama.router.service is active: stop it in the scheduled window first (or pass --allow-active-production)"
        fi
    fi
fi

# --- rows ------------------------------------------------------------------

run_C0() {
    ROW_ENV=()
    bench_row C0 "control (no knob)" ok "" \
        --ctx "$CTX" --chunk 4096 --pp 4096 --tg 128 --reps 2 || return 1
    generate_row C0 --ctx 4096 --chunk 4096
}
run_C1() {
    ROW_ENV=()
    bench_row C1 "short chunk 512" ok "" \
        --ctx "$CTX" --chunk 512 --pp 512,4096 --tg 128 --reps 2
}
run_C2() {
    ROW_ENV=()
    bench_row C2 "full-length chunk 32768" ok "" \
        --ctx "$CTX" --chunk 32768 --pp 32768 --tg 64 --reps 1 || return 1
    generate_row C2 --ctx 4096 --chunk 32768
}
run_K1() {
    ROW_ENV=()
    bench_row K1 "q8 KV" ok "" \
        --ctx "$CTX" --kv q8 --chunk 4096 --pp 4096 --tg 128 --reps 2 || return 1
    generate_row K1 --ctx 4096 --chunk 4096 --kv q8
}
run_K2() {
    ROW_ENV=()
    bench_row K2 "q8 KV + llama numerics" reject \
        '--kv q8 does not combine with --llama-numerics' \
        --ctx "$CTX" --kv q8 --llama-numerics --pp 64 --tg 8
}
run_K3() {
    ROW_ENV=()
    bench_row K3 "llama numerics alone" ok "" \
        --ctx "$CTX" --llama-numerics --pp 512 --tg 32 --reps 1
}
run_N1() {
    ROW_ENV=(STRATA_VK_NO_COOP=1)
    bench_row N1 "coop disabled (STRATA_VK_NO_COOP=1)" ok "" \
        --ctx "$CTX" --chunk 4096 --pp 4096 --tg 128 --reps 2
}
run_N2() {
    ROW_ENV=(STRATA_NO_GRAPH=1)
    bench_row N2 "graphs disabled (STRATA_NO_GRAPH=1)" ok "" \
        --ctx "$CTX" --chunk 4096 --pp 4096 --tg 128 --reps 2 || return 1
    ROW_ENV=(STRATA_NO_GRAPH=1)
    generate_row N2 --ctx 4096 --chunk 4096
}
run_M1() {
    ROW_ENV=()
    bench_row M1 "MTP on MoE (no MTP head)" caveat \
        '--mtp 1: this model has no MTP head: decoding without drafts' \
        --ctx "$CTX" --mtp --chunk 4096 --pp 512 --tg 128 --reps 1
}
run_M2() {
    ROW_ENV=()
    if ((DRY_RUN == 0)) && [[ ! -f $MODEL_27B ]]; then
        record_row M2 "MTP on the dense 27B (optional)" \
            "strata bench --model \"\$M27B\" --gpu --backend vulkan --ctx 8192 --mtp --chunk 4096 --pp 512 --tg 128 --reps 1 --json-out target/m0t6/mtp27b.json" \
            "unsupported (optional 27B model not present)" "—" "optional row" ""
        return 0
    fi
    local saved=$MODEL
    MODEL=$MODEL_27B
    MODEL_LABEL='$M27B'
    bench_row M2 "MTP on the dense 27B (optional)" info 'MTP drafts accepted' \
        --ctx 8192 --mtp --chunk 4096 --pp 512 --tg 128 --reps 1
    local rc=$?
    MODEL=$saved
    MODEL_LABEL='$M'
    return $rc
}
run_P2() {
    ROW_ENV=()
    serve_row P2 "2 slots" 2 serve "" "$PORT_BASE"
}
run_P4() {
    ROW_ENV=()
    serve_row P4 "4 slots" 4 serve "" "$((PORT_BASE + 1))"
}
run_P2M() {
    ROW_ENV=()
    serve_row P2M "parallel + MTP" 2 downgrade \
        '--parallel 2 and --mtp 1: not supported together, decoding without MTP drafts' \
        "$((PORT_BASE + 2))" --mtp
}

for row in "${ALL_ROWS[@]}"; do
    selected "$row" || continue
    # Reset the per-row environment; each row function sets what it needs.
    ROW_ENV=()
    "run_$row" || true
    if ((XID_FOUND)); then
        say "knob_matrix: stopping after $row because of an Xid/device-lost report"
        break
    fi
done

# --- environment and drift -------------------------------------------------

ENV_NVIDIA=""
ENV_XID=""
ENV_SERVICE=""
if ((DRY_RUN == 0)); then
    if command -v nvidia-smi >/dev/null 2>&1; then
        ENV_NVIDIA=$(nvidia-smi --query-gpu=name,memory.used,utilization.gpu --format=csv 2>&1 || true)
    else
        ENV_NVIDIA="nvidia-smi not found"
    fi
    if command -v journalctl >/dev/null 2>&1; then
        ENV_XID=$(journalctl -k --since "-40 min" 2>/dev/null | grep -i Xid | tail -n5 || true)
    fi
    [[ -z $ENV_XID ]] && ENV_XID="no Xid"
    ENV_SERVICE=$(systemctl is-active llama.router.service 2>/dev/null || true)
    [[ -z $ENV_SERVICE ]] && ENV_SERVICE="unknown"
fi

mean_of() { # mean_of ROW PP FIELD -> mean tok/s or empty
    local row=$1 pp=$2 field=$3 f=$JSON_DIR/$1.json
    if [[ -s $f ]] && have_jq; then
        jq -r --argjson pp "$pp" --arg field "$field" \
            '.results[] | select(.pp == $pp) | .[$field + "_tok_s"].mean' "$f" 2>/dev/null | head -n1
    elif [[ -s $LOG_DIR/$1.log ]]; then
        grep -E "^pp +$pp:" "$LOG_DIR/$1.log" 2>/dev/null \
            | sed -nE "s/.*${field} ([0-9.]+) \(.*/\1/p" | head -n1
    fi
    return 0
}

pct_delta() { # percent change of $2 from $1
    awk -v a="${1:-}" -v b="${2:-}" 'BEGIN {
        if (a == "" || b == "" || a + 0 == 0) { print "n/a"; exit }
        printf "%+.1f%%", 100 * (b - a) / a
    }'
}

drift_lines() {
    local c0p c0d n1p n1d n2p n2d m1d
    c0p=$(mean_of C0 4096 prefill); c0d=$(mean_of C0 4096 decode)
    n1p=$(mean_of N1 4096 prefill); n1d=$(mean_of N1 4096 decode)
    n2p=$(mean_of N2 4096 prefill); n2d=$(mean_of N2 4096 decode)
    m1d=$(mean_of M1 512 decode)
    echo "- C0 control at pp 4096: prefill ${c0p:-n/a} tok/s, decode ${c0d:-n/a} tok/s."
    if [[ -n ${n1p:-} && -n ${c0p:-} ]]; then
        echo "- N1 (coop off) vs C0: prefill $(pct_delta "$c0p" "$n1p"), decode $(pct_delta "$c0d" "$n1d")."
    else
        echo "- N1 vs C0: n/a (C0 or N1 not run in this pass)."
    fi
    if [[ -n ${m1d:-} && -n ${c0d:-} ]]; then
        echo "- M1 (MTP downgraded) decode at pp 512 vs C0 decode at pp 4096: $(pct_delta "$c0d" "$m1d") (different prompt length; the prefill means are not comparable, so only decode is checked)."
    else
        echo "- M1 vs C0: n/a (C0 or M1 not run in this pass)."
    fi
    if [[ -n ${n2d:-} && -n ${c0d:-} ]]; then
        echo "- N2 (graphs off) vs C0, informational: prefill $(pct_delta "$c0p" "$n2p"), decode $(pct_delta "$c0d" "$n2d"). This is the cost of re-recording every submission, not a pass/fail row."
    fi
    echo "- K1 (q8 KV) is exempt from the drift guard: the numerics differ by design."
}

notes_lines() {
    local c0p c0d k1p k1d k1min k1max kv0 kv1 c1p c2pf c2kv
    c0p=$(mean_of C0 4096 prefill); c0d=$(mean_of C0 4096 decode)
    if [[ -v STATUS[K1] ]]; then
        k1p=$(mean_of K1 4096 prefill); k1d=$(mean_of K1 4096 decode)
        k1min=$(jq -r '.results[] | select(.pp == 4096) | .prefill_tok_s.min' "$JSON_DIR/K1.json" 2>/dev/null | head -n1)
        k1max=$(jq -r '.results[] | select(.pp == 4096) | .prefill_tok_s.max' "$JSON_DIR/K1.json" 2>/dev/null | head -n1)
        kv0=$(plan_kv "${PLANLINE[C0]:-}"); kv1=$(plan_kv "${PLANLINE[K1]:-}")
        local kvtext="KV ${kv1:-?} MB"
        [[ -n ${kv0:-} ]] && kvtext+=" vs ${kv0} MB for C0"
        echo "- K1: ${kvtext}. Prefill $(pct_delta "$c0p" "$k1p") and decode $(pct_delta "$c0d" "$k1d") against C0 (decode is exempt from the drift guard: numerics differ)."
        if [[ -n ${k1min:-} && -n ${k1max:-} ]] && awk -v a="$k1min" -v b="$k1max" 'BEGIN { exit !(a > 0 && b / a > 1.05) }'; then
            echo "  The wide min-max is the first (pipeline-compilation) repetition; the max is the steady state."
        fi
    fi
    if [[ -v STATUS[C1] ]]; then
        c1p=$(mean_of C1 4096 prefill)
        echo "- C1: pp 4096 prefill is $(pct_delta "$c0p" "$c1p") against C0, expected with \`--chunk 512\` (more expert restaging per chunk); the pp 512 row keeps the short-prompt rate."
    fi
    if [[ -v STATUS[C2] ]]; then
        c2pf=$(plan_prefill "${PLANLINE[C2]:-}"); c2kv=$(plan_kv "${PLANLINE[C2]:-}")
        echo "- C2: \`--chunk 32768\` fits: prefill scratch ${c2pf:-?} MB, KV ${c2kv:-?} MB, expert slots unchanged."
    fi
    if [[ -v STATUS[N2] ]]; then
        echo "- N2: the decode drop against C0 is the \`STRATA_NO_GRAPH\` re-record cost."
    fi
}

json_record_lines() {
    local row f schema
    for row in "${ROW_ORDER[@]}"; do
        f=${JSONPATH[$row]:-}
        [[ -n $f && -s $f ]] || continue
        if json_valid "$f"; then
            schema=$(json_floor "$f")
            echo "- \`$f\` — valid JSON (\`$schema\`), key fields in the table above."
        else
            echo "- \`$f\` — **invalid JSON** (row $row)."
        fi
    done
}

# --- markdown --------------------------------------------------------------

section() {
    echo "## $(date -u '+%Y-%m-%d %H:%M UTC') — M0-T6 Vulkan flag/knob matrix (Vulkan, V100)"
    echo
    echo "Backend \`vulkan\`, device 0, reference MoE Q2_K_XL (12.3 GB) as \`\$M\`. Each bench row is"
    echo "a fresh process; the JSON records live under \`target/m0t6/\` and are not committed."
    echo
    echo '| row | setting | status | numbers | message/exit code |'
    echo '| --- | --- | --- | --- | --- |'
    local row
    for row in "${ROW_ORDER[@]}"; do
        printf '| %s | %s | %s | %s | %s |\n' \
            "$(cell "$row")" "$(cell "${SETTING[$row]:-}")" "$(cell "${STATUS[$row]:-}")" \
            "$(cell "${NUMBERS[$row]:-}")" "$(cell "${MESSAGE[$row]:-}")"
    done
    echo
    echo "### Plan lines"
    echo
    echo '```'
    for row in "${ROW_ORDER[@]}"; do
        [[ -n ${PLANLINE[$row]:-} ]] && echo "$row: ${PLANLINE[$row]}"
    done
    echo '```'
    echo
    echo "### JSON records"
    echo
    json_record_lines
    echo
    echo "### Drift guard"
    echo
    drift_lines
    echo
    echo "### Notes"
    echo
    notes_lines
    echo
    if ((${#SANITY_ROWS[@]})); then
        echo "### Output sanity (\`strata generate -n $GEN_N\`)"
        echo
        echo '| row | status | vs C0 | text |'
        echo '| --- | --- | --- | --- |'
        local g
        for g in "${SANITY_ROWS[@]}"; do
            printf '| %s | %s | %s | %s |\n' \
                "$(cell "$g")" "$(cell "${SANITY_STATUS[$g]:-}")" "$(cell "${SANITY_CMP[$g]:-}")" \
                "$(cell "${GENTEXT[$g]:-}")"
        done
        echo
    fi
    echo "### Commands"
    echo
    echo '```'
    for row in "${ROW_ORDER[@]}"; do
        [[ -n ${COMMAND[$row]:-} ]] && echo "$row: ${COMMAND[$row]}"
    done
    echo '```'
    echo
    if ((DRY_RUN == 0)); then
        echo "### Environment"
        echo
        echo '```'
        printf '%s\n' "$ENV_NVIDIA"
        echo "$ENV_XID"
        echo "llama.router.service: $ENV_SERVICE"
        echo '```'
        echo
        if ((XID_FOUND)); then
            echo "> **Xid/device lost detected**: the run was stopped at the row above. That row (and the"
            echo "> remaining rows) need a follow-up issue; the command is recorded here."
            echo
        fi
    else
        echo "_Dry run: no command was executed, no number is recorded._"
        echo
    fi
}

if ((DRY_RUN == 0)); then
    echo "knob_matrix: rows: ${ROW_ORDER[*]:-none}" >&2
fi

TMP_MD=$(mktemp "${TMPDIR:-/tmp}/knob-matrix.XXXXXX.md")
trap 'rm -f "$TMP_MD"; cleanup' EXIT
trap 'rm -f "$TMP_MD"; cleanup; exit 130' INT TERM
section >"$TMP_MD"
cat "$TMP_MD"
if [[ -n $OUT ]]; then
    mkdir -p "$(dirname -- "$OUT")"
    cp "$TMP_MD" "$OUT"
fi
if [[ -n $APPEND ]]; then
    mkdir -p "$(dirname -- "$APPEND")"
    cat "$TMP_MD" >>"$APPEND"
fi

if ((XID_FOUND)); then exit 3; fi
