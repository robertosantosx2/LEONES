#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${HOME}/nepenthes-msi-final-audit-${STAMP}"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/nepenthes-audit.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
REPORT="$TMP/report"
mkdir -p "$REPORT/repos"

say() { printf '%s\n' "$*" | tee -a "$REPORT/00-summary.txt"; }
hash_tree() {
  local root="$1" dest="$2"
  {
    printf 'ROOT\t%s\n' "$root"
    if [[ -d "$root" ]]; then
      find "$root" -type d \( -name .git -o -name node_modules -o -name .cache -o -name build -o -name models -o -name __pycache__ \) -prune -o -type f -printf '%P\t%s bytes\n' 2>/dev/null | sort
      printf '\nSHA256:\n'
      find "$root" -type d \( -name .git -o -name node_modules -o -name .cache -o -name build -o -name models -o -name __pycache__ \) -prune -o -type f -print0 2>/dev/null | sort -z | xargs -0 -r sha256sum
    else printf 'MISSING\n'; fi
  } > "$dest"
}
audit_repo() {
  local name="$1" path="$2" d="$REPORT/repos/$name"
  mkdir -p "$d"
  {
    echo "LABEL=$name"; echo "PATH=$path"
    if [[ ! -e "$path/.git" && ! -f "$path/.git" ]]; then echo "NOT_A_GIT_WORKTREE"; return 0; fi
    git -C "$path" rev-parse --show-toplevel 2>&1
    echo "HEAD=$(git -C "$path" rev-parse HEAD 2>&1)"
    echo "BRANCH=$(git -C "$path" branch --show-current 2>&1)"
    echo "GIT_DIR=$(git -C "$path" rev-parse --git-dir 2>&1)"
    echo "COMMON_DIR=$(git -C "$path" rev-parse --git-common-dir 2>&1)"
    echo "STATUS:"; git -C "$path" status --porcelain=v2 --branch 2>&1
    echo "BRANCHES:"; git -C "$path" branch -vv --no-abbrev 2>&1
    echo "WORKTREES:"; git -C "$path" worktree list --porcelain 2>&1
    echo "STASHES:"; git -C "$path" stash list --format='%gd%x09%H%x09%gs' 2>&1
    echo "REMOTES (names only):"; git -C "$path" remote 2>&1
  } > "$d/state.txt"
  git -C "$path" diff --cached --binary --no-ext-diff > "$d/staged.patch" 2>"$d/staged.err" || true
  git -C "$path" diff --binary --no-ext-diff > "$d/unstaged.patch" 2>"$d/unstaged.err" || true
  git -C "$path" ls-files --others --exclude-standard -z 2>/dev/null |
    while IFS= read -r -d '' f; do
      if [[ -f "$path/$f" ]]; then stat -c '%n\t%s bytes\t%y' "$path/$f"; sha256sum "$path/$f"
      elif [[ -d "$path/$f" ]]; then printf 'DIRECTORY\t%s\n' "$f"; fi
    done > "$d/untracked-files-and-sha256.txt"
  {
    while IFS=$'\t' read -r stash oid subject; do
      [[ -n "${oid:-}" ]] || continue
      echo "===== $stash $oid $subject ====="
      git -C "$path" stash show --stat --oneline "$oid" 2>&1 || true
      echo "OBJECT_TYPE=$(git -C "$path" cat-file -t "$oid" 2>&1 || true)"
    done < <(git -C "$path" stash list --format='%gd%x09%H%x09%gs' 2>/dev/null)
  } > "$d/stash-details.txt"
}

say "NEPENTHES / MSI FINAL READ-ONLY AUDIT"
say "Timestamp: $(date --iso-8601=seconds)"
say "Host: $(hostname)"; say "Kernel: $(uname -sr)"
say "No checkout, branch, stash, index, worktree, or source file is modified."
say "Only this report bundle is created; raw captures/models are not copied."

audit_repo "leones-tandem-evidence" "$HOME/leones-work/LEONES-tandem-evidence"
audit_repo "tandem-pr7-physical-parent" "$HOME/tandem-pr7-physical-20261120"
audit_repo "tandem-pr7-physical-nested-tandem" "$HOME/tandem-pr7-physical-20261120/tandem"
audit_repo "nepenthes-pinned-validation" "$HOME/nepenthes-pinned-validation-20261115"
audit_repo "tensorfold-pr1879" "$HOME/tensorfold-pr1879-real-validation-20261109/TensorFold"
audit_repo "ods-cafe-staging" "$HOME/leones-cafe-staging/ods-src"
audit_repo "ods-cafe-pr" "$HOME/ods-cafe-pr"
audit_repo "nepenthes-cli" "$HOME/LEONES-nepenthes-cli-20261115"
audit_repo "nepenthes-importer" "$HOME/LEONES-nepenthes-importer-20261115"
audit_repo "betelgeuse-qwen35" "$HOME/betelgeuse-qwen35-validation"

hash_tree "$HOME/tandem-pr7-physical-20261120" "$REPORT/tandem-pr7-physical-files.txt"
hash_tree "$HOME/nepenthes-pinned-validation-20261115" "$REPORT/nepenthes-pinned-validation-files.txt"

AFF="$HOME/leones-work/LEONES-tandem-evidence/artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/run_nepenthes_affinity_ab.sh"
{
  echo "PATH=$AFF"
  if [[ -f "$AFF" ]]; then stat -c '%n %s bytes' "$AFF"; sha256sum "$AFF"; nl -ba "$AFF"
  else echo "MISSING"; fi
} > "$REPORT/affinity-script.txt"

{
  for f in "$HOME/leones-cafe-staging/ods-src/os" "$HOME/leones-cafe-staging/os"; do
    if [[ -f "$f" ]]; then stat -c '%n %s bytes' "$f"; sha256sum "$f"; file "$f"; fi
  done
} > "$REPORT/ods-postscript-candidate.txt"

{
  for spec in \
    "tandem-evidence:$HOME/leones-work/LEONES-tandem-evidence" \
    "tandem-physical:$HOME/tandem-pr7-physical-20261120" \
    "pinned-validation:$HOME/nepenthes-pinned-validation-20261115" \
    "tensorfold:$HOME/tensorfold-pr1879-real-validation-20261109/TensorFold"; do
    label="${spec%%:*}"; path="${spec#*:}"
    echo "===== $label ====="
    if [[ -e "$path/.git" || -f "$path/.git" ]]; then
      git -C "$path" rev-parse HEAD 2>&1 || true
      git -C "$path" rev-parse --git-common-dir 2>&1 || true
      git -C "$path" cat-file -t 872ee09a16dca1327a9278f51f43e8ba6ea3d08a 2>&1 || true
      git -C "$path" show --stat --oneline --decorate HEAD 2>&1 | head -100
    else echo "MISSING"; fi
  done
} > "$REPORT/commit-resolution.txt"

(
  cd "$(dirname "$REPORT")"
  find report -type f -printf '%P\t%s bytes\n' | sort > report/FILE-MANIFEST.txt
  tar -czf "$OUT.tar.gz" report
)
sha256sum "$OUT.tar.gz" > "$OUT.tar.gz.sha256"
printf '\nAUDIT_BUNDLE=%s\n' "$OUT.tar.gz"
printf 'SHA256_FILE=%s\n' "$OUT.tar.gz.sha256"
printf 'BUNDLE_SIZE=%s bytes\n' "$(stat -c %s "$OUT.tar.gz")"
printf '\nUpload this single .tar.gz file in the chat. Do not upload raw .nsys-rep/.sqlite captures separately.\n'
