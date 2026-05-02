#!/usr/bin/env bash
# Orchestrator for autonomous bead execution.
# See docs/orchestration.md for the architectural contract.
#
# Usage:
#   bin/orchestrate.sh                  # run continuously until queue empty or halt
#   bin/orchestrate.sh --max-beads 3    # stop after executing N beads
#   bin/orchestrate.sh --dry-run        # show what would be picked, don't execute
#
# Halt conditions:
#   - Homelab vLLM endpoint unreachable
#   - Disk free < 1 GB
#   - Working tree dirty (avoids stomping in-progress changes)
#   - Claude command exits with rate-limit-style failure
#   - --max-beads reached (graceful)
#
# Per-bead failure handling: writes to bead-failures/<id>.json drive
# whether the bead is marked needs_attention, halts the train, or is left
# for retry. See docs/orchestrator-bead-executor-prompt.md.

set -u

cd "$(dirname "$0")/.." || exit 1

readonly HOMELAB_HEALTH_URL="http://192.168.100.101:8080/v1/models"
readonly EXECUTOR_PROMPT_TEMPLATE="docs/orchestrator-bead-executor-prompt.md"
readonly FAILURES_DIR="bead-failures"
readonly LOGS_DIR="logs/orchestrator"
readonly MIN_DISK_FREE_KB=$((1024 * 1024))  # 1 GB
readonly POLL_SLEEP_SECONDS=300  # 5 min between polls when queue empty

mkdir -p "$FAILURES_DIR" "$LOGS_DIR"

MAX_BEADS=""
DRY_RUN=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-beads) MAX_BEADS="$2"; shift 2 ;;
    --dry-run)   DRY_RUN=true; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

log() { printf '[orch %s] %s\n' "$(date -Iseconds)" "$*" | tee -a "$LOGS_DIR/orchestrate.log" >&2; }

systemic_health_ok() {
  if ! curl -sf --connect-timeout 5 "$HOMELAB_HEALTH_URL" > /dev/null; then
    log "HALT: homelab unreachable at $HOMELAB_HEALTH_URL"
    return 1
  fi
  local free_kb
  free_kb=$(df -k . | awk 'NR==2 {print $4}')
  if [ "$free_kb" -lt "$MIN_DISK_FREE_KB" ]; then
    log "HALT: disk free ${free_kb}KB below threshold ${MIN_DISK_FREE_KB}KB"
    return 1
  fi
  if ! git diff --quiet || ! git diff --cached --quiet; then
    log "HALT: working tree dirty; refusing to start a new bead. Resolve and restart."
    return 1
  fi
  return 0
}

pick_next_bead() {
  # Returns the top auto-executable bead ID, or empty if none.
  bd ready --json 2>/dev/null \
    | jq -r '[.[] | select(.labels // [] | index("auto-executable"))] | .[0].id // empty'
}

execute_bead() {
  local bead_id="$1"
  local bead_log="$LOGS_DIR/bead-${bead_id}-$(date +%s).log"
  local prompt
  prompt=$(sed "s/{BEAD_ID}/${bead_id}/g" "$EXECUTOR_PROMPT_TEMPLATE")

  log "executing $bead_id"
  if [ "$DRY_RUN" = "true" ]; then
    log "DRY RUN: would invoke claude -p with the bead-executor prompt"
    return 0
  fi

  # Use Claude Code in print mode. The agent does the full bead cycle.
  # Output is captured for diagnostics; success/failure signal comes from
  # the bead-failures/<id>.json file the executor writes (or doesn't).
  if ! claude -p "$prompt" > "$bead_log" 2>&1; then
    log "ERROR: claude exited non-zero for $bead_id (log: $bead_log)"
    return 2
  fi
  return 0
}

handle_bead_outcome() {
  local bead_id="$1"
  local failure_file="$FAILURES_DIR/${bead_id}.json"

  if [ ! -f "$failure_file" ]; then
    log "$bead_id: success (closed by executor)"
    return 0
  fi

  local failure_type
  failure_type=$(jq -r '.failure_type // "unknown"' < "$failure_file")
  case "$failure_type" in
    systemic)
      log "HALT: systemic failure on $bead_id: $(jq -r '.reason' < "$failure_file")"
      return 1
      ;;
    bead_specific)
      log "$bead_id: bead-specific failure, marking needs_attention"
      bd update "$bead_id" --labels needs_attention 2>&1 \
        | grep -v -E '^(Updated|✓)' >&2 || true
      # Remove auto-executable label so we don't re-pick it
      bd update "$bead_id" --remove-labels auto-executable 2>&1 \
        | grep -v -E '^(Updated|✓)' >&2 || true
      # Move the failure file aside so it doesn't trigger again
      mv "$failure_file" "${failure_file}.handled"
      return 0
      ;;
    transient_retry)
      log "$bead_id: transient failure, leaving in place for retry next cycle"
      mv "$failure_file" "${failure_file}.handled"
      return 0
      ;;
    *)
      log "WARNING: unknown failure_type '$failure_type' on $bead_id; treating as bead_specific"
      bd update "$bead_id" --labels needs_attention 2>&1 | tail -1 >&2 || true
      mv "$failure_file" "${failure_file}.handled"
      return 0
      ;;
  esac
}

# Main loop
log "orchestrator starting (max_beads=${MAX_BEADS:-unlimited}, dry_run=$DRY_RUN)"
beads_executed=0

while true; do
  if [ -n "$MAX_BEADS" ] && [ "$beads_executed" -ge "$MAX_BEADS" ]; then
    log "max_beads reached ($beads_executed); exiting cleanly"
    exit 0
  fi

  if ! systemic_health_ok; then
    exit 1
  fi

  bead=$(pick_next_bead)
  if [ -z "$bead" ]; then
    if [ "$DRY_RUN" = "true" ]; then
      log "dry run: no auto-executable beads in queue; exiting"
      exit 0
    fi
    log "queue empty; sleeping ${POLL_SLEEP_SECONDS}s"
    sleep "$POLL_SLEEP_SECONDS"
    continue
  fi

  if ! execute_bead "$bead"; then
    log "HALT: claude execution failed for $bead (assumed systemic)"
    exit 2
  fi

  if ! handle_bead_outcome "$bead"; then
    exit 3  # systemic failure signaled by the bead's failure file
  fi

  beads_executed=$((beads_executed + 1))
  log "completed $bead (total this run: $beads_executed)"
done
