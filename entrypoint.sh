#!/usr/bin/env bash
set -euo pipefail

echo "[collector] Launching collector entrypoint"

: "${PBS_USER:?PBS_USER must be set}"
: "${PBS_PASSWORD:?PBS_PASSWORD must be set}"
: "${PBS_KRB_CONF_HOST:?PBS_KRB_CONF_HOST must be set}"
: "${PBS_CONF_HOST:?PBS_CONF_HOST must be set}"

ENV_DIR=/env
PRINCIPAL="${PBS_USER}@META"
KRB5CCNAME=${KRB5CCNAME:-/tmp/krb5cc_collector}
REFRESH_INTERVAL="${PBS_TICKET_REFRESH_SECONDS:-21600}"
export SSHPASS="${PBS_PASSWORD}"

mkdir -p "${ENV_DIR}"
chmod 700 "${ENV_DIR}"

fetch_remote_file() {
  local host="$1"
  local remote_path="$2"
  local destination="$3"

  sshpass -e scp -q \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "${PBS_USER}@${host}:${remote_path}" "${destination}" >/dev/null
}

fetch_remote_file "${PBS_KRB_CONF_HOST}" "/etc/krb5.conf" "${ENV_DIR}/krb5.conf"
fetch_remote_file "${PBS_CONF_HOST}" "/etc/pbs.conf" "${ENV_DIR}/pbs.conf"

export KRB5_CONFIG="${ENV_DIR}/krb5.conf"
export PBS_CONF_FILE="${ENV_DIR}/pbs.conf"
export PBS_CONF="${ENV_DIR}/pbs.conf"
export KRB5CCNAME

printf '%s\n' "${PBS_PASSWORD}" | kinit "${PRINCIPAL}" >/dev/null 2>&1
printf '%s\n' "${PBS_PASSWORD}" | kinit -r 7d "${PRINCIPAL}" >/dev/null 2>&1

KTUTIL_CMDS=$(cat <<EOF
addent -password -p ${PRINCIPAL} -k 1 -e aes256-cts
${PBS_PASSWORD}
wkt ${ENV_DIR}/pbs.keytab
quit
EOF
)

printf '%s\n' "${KTUTIL_CMDS}" | ktutil >/dev/null
chmod 600 "${ENV_DIR}/pbs.keytab"

klist -k "${ENV_DIR}/pbs.keytab"

kinit -t "${ENV_DIR}/pbs.keytab" "${PRINCIPAL}" >/dev/null 2>&1

refresh_tickets() {
  while true; do
    sleep "${REFRESH_INTERVAL}"
    if ! kinit -t "${ENV_DIR}/pbs.keytab" "${PRINCIPAL}" >/dev/null 2>&1; then
      echo "[collector] Failed to refresh Kerberos ticket" >&2
    fi
  done
}

refresh_tickets &
REFRESH_PID=$!
trap 'kill "${REFRESH_PID}" 2>/dev/null || true' EXIT

exec python /app/src/main.py
