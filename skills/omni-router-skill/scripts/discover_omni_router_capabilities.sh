#!/usr/bin/env bash
set -euo pipefail

# Discover Lemonade OmniRouter capabilities without hardcoding model IDs.
# Requirements: curl, jq

BASE_URL="${LEMONADE_BASE_URL:-http://127.0.0.1:13305}"
API_KEY="${LEMONADE_API_KEY:-}"
OUT_FILE="${1:-./omni_capabilities.json}"

_auth_header=()
if [[ -n "$API_KEY" ]]; then
  _auth_header=(-H "Authorization: Bearer ${API_KEY}")
fi

echo "[info] Base URL: ${BASE_URL}" >&2

models_json="$(curl -sS "${BASE_URL}/v1/models?show_all=true" "${_auth_header[@]}")"

# Some servers return errors as JSON with an error field; surface quickly.
if echo "$models_json" | jq -e '.error' >/dev/null 2>&1; then
  echo "[error] /v1/models returned error:" >&2
  echo "$models_json" | jq '.' >&2
  exit 2
fi

# Build capability flags based on labels and endpoint probes.
# Endpoint probes use a tiny invalid payload and check non-404/non-405 to indicate endpoint exists.
probe_endpoint() {
  local path="$1"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "${BASE_URL}${path}" "${_auth_header[@]}" -H 'Content-Type: application/json' -d '{}')"
  if [[ "$code" == "404" || "$code" == "405" ]]; then
    echo "false"
  else
    echo "true"
  fi
}

has_image_label="$(echo "$models_json" | jq -r '[(.data // [])[] | (.labels // [])[]? | ascii_downcase] | any(. == "image")')"
has_edit_label="$(echo "$models_json" | jq -r '[(.data // [])[] | (.labels // [])[]? | ascii_downcase] | any(. == "edit")')"
has_tts_label="$(echo "$models_json" | jq -r '[(.data // [])[] | (.labels // [])[]? | ascii_downcase] | any(. == "tts" or . == "speech")')"
has_stt_label="$(echo "$models_json" | jq -r '[(.data // [])[] | (.labels // [])[]? | ascii_downcase] | any(. == "audio" or . == "transcription")')"
has_vision_llm="$(echo "$models_json" | jq -r '[(.data // [])[] | {id, labels: (.labels // [])}] | any((.labels | map(ascii_downcase) | any(. == "vision" or . == "tool-calling")))')"

chat_ok="$(probe_endpoint '/v1/chat/completions')"
img_gen_ok="$(probe_endpoint '/v1/images/generations')"
img_edit_ok="$(probe_endpoint '/v1/images/edits')"
tts_ok="$(probe_endpoint '/v1/audio/speech')"
stt_ok="$(probe_endpoint '/v1/audio/transcriptions')"

jq -n \
  --arg base_url "$BASE_URL" \
  --argjson models "$models_json" \
  --argjson has_image_label "$has_image_label" \
  --argjson has_edit_label "$has_edit_label" \
  --argjson has_tts_label "$has_tts_label" \
  --argjson has_stt_label "$has_stt_label" \
  --argjson has_vision_llm "$has_vision_llm" \
  --argjson chat_ok "$chat_ok" \
  --argjson img_gen_ok "$img_gen_ok" \
  --argjson img_edit_ok "$img_edit_ok" \
  --argjson tts_ok "$tts_ok" \
  --argjson stt_ok "$stt_ok" \
  '{
    base_url: $base_url,
    discovered_at_utc: (now | todateiso8601),
    endpoints: {
      chat_completions: $chat_ok,
      images_generations: $img_gen_ok,
      images_edits: $img_edit_ok,
      audio_speech: $tts_ok,
      audio_transcriptions: $stt_ok
    },
    labels: {
      image: $has_image_label,
      edit: $has_edit_label,
      tts_or_speech: $has_tts_label,
      audio_or_transcription: $has_stt_label,
      vision_or_tool_calling: $has_vision_llm
    },
    model_count: (($models.data // []) | length),
    models: ($models.data // []),
    omni_router_ready: (
      $chat_ok and $img_gen_ok and $img_edit_ok and $tts_ok and $stt_ok and
      $has_image_label and $has_tts_label and $has_stt_label
    )
  }' > "$OUT_FILE"

echo "[ok] Capability report written to: ${OUT_FILE}" >&2
cat "$OUT_FILE"
