#!/bin/bash
set -euo pipefail

MODE="${1:-up}"
CARD="${2:-1}"
TARGET_VOL="${3:-85}"
FADE_SECONDS="${4:-2}"
STEPS=20

if ! command -v amixer >/dev/null 2>&1; then
  exit 0
fi

choose_control() {
  if [ -n "${AUDIO_MIXER_CONTROL:-}" ]; then
    echo "$AUDIO_MIXER_CONTROL"
    return
  fi

  local controls
  controls=$(amixer -c "$CARD" scontrols 2>/dev/null | sed -n "s/Simple mixer control '\(.*\)',.*/\1/p")

  for preferred in Master PCM Speaker Line Headphone Digital; do
    if echo "$controls" | grep -Fxq "$preferred"; then
      echo "$preferred"
      return
    fi
  done

  echo "$controls" | head -n1
}

CONTROL="$(choose_control)"
if [ -z "$CONTROL" ]; then
  exit 0
fi

if ! [[ "$TARGET_VOL" =~ ^[0-9]+$ ]]; then
  TARGET_VOL=85
fi

if ! [[ "$FADE_SECONDS" =~ ^[0-9]+$ ]]; then
  FADE_SECONDS=2
fi

if [ "$TARGET_VOL" -gt 100 ]; then
  TARGET_VOL=100
fi
if [ "$TARGET_VOL" -lt 0 ]; then
  TARGET_VOL=0
fi
if [ "$FADE_SECONDS" -lt 1 ]; then
  FADE_SECONDS=1
fi

current_volume() {
  amixer -c "$CARD" sget "$CONTROL" 2>/dev/null | grep -oE '[0-9]+%' | head -n1 | tr -d '%' || true
}

set_volume() {
  local v="$1"
  if [ "$v" -lt 0 ]; then v=0; fi
  if [ "$v" -gt 100 ]; then v=100; fi
  amixer -c "$CARD" sset "$CONTROL" "${v}%" unmute >/dev/null 2>&1 || true
}

mute_volume() {
  amixer -c "$CARD" sset "$CONTROL" 0% mute >/dev/null 2>&1 || true
}

sleep_step=$(awk "BEGIN {printf \"%.3f\", $FADE_SECONDS/$STEPS}")

case "$MODE" in
  set0)
    mute_volume
    ;;
  up)
    set_volume 0
    for i in $(seq 1 "$STEPS"); do
      v=$(( TARGET_VOL * i / STEPS ))
      set_volume "$v"
      sleep "$sleep_step"
    done
    ;;
  down)
    start_vol="$(current_volume)"
    if ! [[ "$start_vol" =~ ^[0-9]+$ ]]; then
      start_vol="$TARGET_VOL"
    fi
    if [ "$start_vol" -lt 1 ]; then
      mute_volume
      exit 0
    fi

    for i in $(seq "$STEPS" -1 0); do
      v=$(( start_vol * i / STEPS ))
      set_volume "$v"
      sleep "$sleep_step"
    done
    mute_volume
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    exit 1
    ;;
esac
