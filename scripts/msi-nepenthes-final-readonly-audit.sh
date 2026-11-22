#!/usr/bin/env bash
# Read-only MSI audit; publishes sanitized text report and hashes to interaccion-MSI.
set -Eeuo pipefail
umask 077
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_ID="nepenthes-final-readonly-$STAMP"
OUT="$HOME/$RUN_ID"
REPORT="$OUT/report"
LOG="$OUT/run.log"
mkdir -p "$REPORT/repos"
exec > >(tee -a "$LOG") 2>&1
echo "RUN_ID=$RUN_ID"
echo "START=$(date --iso-8601=seconds)"
echo "PID=$$"
echo "HOST=$(hostname)"
echo "Kernel=$(uname -sr)"
echo "READ_ONLY=yes; raw captures/models excluded; no patches or file contents published."
redact(){ sed "s|$HOME|\\$HOME|g"; }
audit_repo(){
 local label="$1" path="$2"
 local d="$REPORT/repos/$label"
 mkdir -p "$d"
 {
  echo "LABEL=$label"; echo "PATH=$(printf '%s' "$path" | redact)"
  if [[ ! -e "$path/.git" && ! -f "$path/.git" ]]; then echo MISSING_OR_NOT_WORKTREE; return; fi
  echo "HEAD=$(git -C "$path" rev-parse HEAD 2>&1)"
  echo "BRANCH=$(git -C "$path" branch --show-current 2>&1)"
  echo "COMMON_DIR=$(git -C "$path" rev-parse --git-common-dir 2>&1 | redact)"
  echo "STATUS:"; git -C "$path" status --porcelain=v2 --branch 2>&1 | redact
  echo "BRANCHES:"; git -C "$path" branch -vv --no-abbrev 2>&1 | redact
  echo "WORKTREES:"; git -C "$path" worktree list --porcelain 2>&1 | redact
  echo "STASHES:"; git -C "$path" stash list --format='%gd%x09%H%x09%gs' 2>&1 | redact
  echo "REMOTE_NAMES:"; git -C "$path" remote 2>&1
  echo "STAGED_DIFF_STAT:"; git -C "$path" diff --cached --stat 2>&1
  echo "UNSTAGED_DIFF_STAT:"; git -C "$path" diff --stat 2>&1
  echo "UNTRACKED_METADATA_SHA256:"
  git -C "$path" ls-files --others --exclude-standard -z 2>/dev/null |
    while IFS= read -r -d '' f; do
     [[ -f "$path/$f" ]] && { stat -c '%n %s bytes' "$path/$f" | redact; sha256sum "$path/$f"; }
    done
 } > "$d/state.txt"
}
say(){ printf '%s\n' "$*" | tee -a "$REPORT/00-summary.txt"; }
say "NEPENTHES MSI READ-ONLY AUDIT"
say "Date=$(date --iso-8601=seconds)"
audit_repo leones-tandem-evidence "$HOME/leones-work/LEONES-tandem-evidence"
audit_repo tandem-pr7-parent "$HOME/tandem-pr7-physical-20261120"
audit_repo tandem-pr7-nested "$HOME/tandem-pr7-physical-20261120/tandem"
audit_repo pinned-validation "$HOME/nepenthes-pinned-validation-20261115"
audit_repo tensorfold-pr1879 "$HOME/tensorfold-pr1879-real-validation-20261109/TensorFold"
audit_repo ods-cafe-staging "$HOME/leones-cafe-staging/ods-src"
audit_repo ods-cafe-pr "$HOME/ods-cafe-pr"
audit_repo nepenthes-cli "$HOME/LEONES-nepenthes-cli-20261115"
audit_repo nepenthes-importer "$HOME/LEONES-nepenthes-importer-20261115"
audit_repo betelgeuse "$HOME/betelgeuse-qwen35-validation"
for path in "$HOME/tandem-pr7-physical-20261120" "$HOME/nepenthes-pinned-validation-20261115"; do
 label="$(basename "$path")"
 {
  echo "PATH=$(printf '%s' "$path" | redact)"
  if [[ -d "$path" ]]; then
   find "$path" -type d \( -name .git -o -name node_modules -o -name .cache -o -name build -o -name models -o -name __pycache__ \) -prune -o -type f -printf '%P\t%s bytes\n' | sort
   echo SHA256:
   find "$path" -type d \( -name .git -o -name node_modules -o -name .cache -o -name build -o -name models -o -name __pycache__ \) -prune -o -type f -print0 | sort -z | xargs -0 -r sha256sum
  else echo MISSING; fi
 } > "$REPORT/files-$(basename "$path").txt"
done
AFF="$HOME/leones-work/LEONES-tandem-evidence/artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_nepenthes_affinity_ab.sh"
{ echo "SCRIPT=$(printf '%s' "$AFF" | redact)"; [[ -f "$AFF" ]] && { stat -c '%s bytes' "$AFF"; sha256sum "$AFF"; echo "CONTENT NOT INCLUDED"; } || echo MISSING; } > "$REPORT/affinity-script-metadata.txt"
{
 for f in "$HOME/leones-cafe-staging/ods-src/os" "$HOME/leones-cafe-staging/os"; do
  [[ -f "$f" ]] && { printf '%s\n' "$(printf '%s' "$f" | redact)"; stat -c '%s bytes' "$f"; sha256sum "$f"; file "$f"; }
 done
} > "$REPORT/ods-postscript-metadata.txt"
find "$REPORT" -type f -printf '%P %s bytes\n' | sort > "$REPORT/MANIFEST.txt"
find "$REPORT" -type f -print0 | sort -z | xargs -0 -r sha256sum > "$REPORT/SHA256SUMS.txt"
tar -czf "$OUT.tar.gz" -C "$OUT" report
sha256sum "$OUT.tar.gz" > "$OUT.tar.gz.sha256"
echo "BUNDLE=$OUT.tar.gz"
echo "BUNDLE_SHA=$(sha256sum "$OUT.tar.gz" | cut -d' ' -f1)"
# Publishing through authenticated GitHub CLI; no secrets written to files.
if ! command -v gh >/dev/null || ! gh auth status >/dev/null 2>&1; then
 echo "PUBLISH_BLOCKED: gh CLI/auth unavailable; bundle remains local."
 exit 20
fi
PUB="$OUT/publish"
gh repo clone robertosantosx2/interaccion-MSI "$PUB" -- --depth 1 >/dev/null
cd "$PUB"
BR="audit/$RUN_ID"
git switch -c "$BR"
DEST="nepenthes/$STAMP"
mkdir -p "$DEST"
cp "$OUT.tar.gz" "$DEST/"
cp "$OUT.tar.gz.sha256" "$DEST/"
cp "$REPORT/00-summary.txt" "$DEST/"
cp "$LOG" "$DEST/run.log"
git add "$DEST"
git -c user.name="MSI Audit" -c user.email="audit@users.noreply.github.com" commit -m "archive $RUN_ID"
git push origin "$BR"
echo "PUBLISH_BRANCH=$BR"
echo "PUBLISH_PATH=$DEST"
# Remote verification of committed bundle checksum and branch tip
REMOTE_SHA="$(git ls-remote origin "refs/heads/$BR" | awk '{print $1}')"
LOCAL_SHA="$(git rev-parse HEAD)"
[[ "$REMOTE_SHA" == "$LOCAL_SHA" ]] || { echo "VERIFY_FAILED: branch SHA mismatch"; exit 30; }
echo "REMOTE_COMMIT_VERIFIED=$REMOTE_SHA"
echo "END=$(date --iso-8601=seconds)"
echo "EXIT_CODE=0"
