#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <case_json_path> <workdir>" >&2
  exit 64
fi

case_path="$1"
workdir="$2"

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
MODEL_NAME="gemma4-bench-32k"
MODEL_ALIAS="ollama_chat/${MODEL_NAME}"
OLLAMA_ENDPOINT="http://localhost:11434"

case_abs="$(readlink -f "$case_path")"
workdir_abs="$(readlink -f "$workdir")"
case_dir_abs="$(dirname "$workdir_abs")"
frontend_dir="${case_dir_abs}/.frontend"
config_abs="${REPO_ROOT}/.aider.conf.yml"
prompt="$(jq -r '.prompt' "$case_abs")"

mkdir -p "$frontend_dir"

aider_version="$(aider --version 2>/dev/null | head -1 | awk '{print $2}')"
ollama_version="$(curl -sS "${OLLAMA_ENDPOINT}/api/version" | jq -r '.version')"
tags_json="$(curl -sS "${OLLAMA_ENDPOINT}/api/tags")"
model_digest="$(jq -r --arg n "${MODEL_NAME}:latest" '.models[] | select(.name==$n) | .digest' <<<"$tags_json")"
upstream_digest="$(jq -r '.models[] | select(.name=="gemma4:e4b") | .digest' <<<"$tags_json")"
show_json="$(curl -sS "${OLLAMA_ENDPOINT}/api/show" -H 'Content-Type: application/json' -d "{\"model\":\"${MODEL_NAME}\"}")"
pinned_params="$(jq -r '.parameters' <<<"$show_json")"

jq -n \
  --arg frontend "aider" \
  --arg frontend_version "${aider_version}" \
  --arg model_alias "${MODEL_NAME}" \
  --arg model_digest "${model_digest}" \
  --arg upstream_model "gemma4:e4b" \
  --arg upstream_digest "${upstream_digest}" \
  --arg ollama_version "${ollama_version}" \
  --arg endpoint "${OLLAMA_ENDPOINT}" \
  --arg pinned_params "${pinned_params}" \
  --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{
     frontend: $frontend,
     frontend_version: $frontend_version,
     model_alias: $model_alias,
     model_digest: $model_digest,
     upstream_model: $upstream_model,
     upstream_digest: $upstream_digest,
     ollama_version: $ollama_version,
     endpoint: $endpoint,
     pinned_params: $pinned_params,
     permission_matrix: "n/a",
     timestamp: $timestamp
   }' > "${frontend_dir}/env.extra.json"

printf '%s' "$prompt" > "${frontend_dir}/prompt.txt"

cd "$workdir_abs"

set +e
OLLAMA_API_BASE="${OLLAMA_ENDPOINT}" \
AIDER_ANALYTICS_DISABLE=1 \
AIDER_AUTO_LINT=0 \
  aider --config "${config_abs}" \
        --model "${MODEL_ALIAS}" \
        --message-file "${frontend_dir}/prompt.txt" \
        --no-git \
        --no-check-update \
        --no-show-model-warnings \
  >"${frontend_dir}/stdout" 2>"${frontend_dir}/stderr"
rc=$?
set -e

printf '%d\n' "$rc" > "${frontend_dir}/exit_code"
exit "$rc"
