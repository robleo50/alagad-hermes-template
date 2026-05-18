#!/usr/bin/env bash
# Alagad Hermes Template — VM 100 install script
# Run as the `clawd` user on VM 100 before converting to a Proxmox template.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_DIR="${HOME}/.hermes"
SKILLS_DIR="${HERMES_DIR}/skills"

echo "🇵🇭 Alagad Hermes Template installer"
echo "    Repo dir: ${REPO_DIR}"
echo "    Hermes dir: ${HERMES_DIR}"
echo ""

# --- 0. Sanity: Hermes must be installed ---
if ! command -v hermes >/dev/null 2>&1; then
  echo "ERROR: hermes binary not found in PATH. Install Hermes Agent first." >&2
  exit 1
fi

mkdir -p "${SKILLS_DIR}"

# --- 1. Make sure Hermes is on the current version ---
echo "==> Updating Hermes to latest..."
hermes update || echo "  (continuing; update is non-fatal if already current)"

# --- 2. Enable the three bundled plugins we want ---
echo "==> Enabling bundled plugins..."
for plugin in disk-cleanup hermes-achievements image_gen; do
  hermes plugins enable "${plugin}" && echo "  ✓ ${plugin}" || echo "  ✗ ${plugin} (may already be enabled or unavailable)"
done

# --- 3. Install the 6 PH skills ---
echo "==> Installing Alagad PH Essentials skills..."
SKILLS=(
  "ph-payment-confirmation"
  "ph-gcash-maya-instructions"
  "ph-appointment-booking"
  "ph-order-intake"
  "ph-delivery-coordination"
  "ph-business-hours-and-holidays"
)
for skill in "${SKILLS[@]}"; do
  if [[ -d "${REPO_DIR}/skills/${skill}" ]]; then
    rm -rf "${SKILLS_DIR}/${skill}"
    cp -r "${REPO_DIR}/skills/${skill}" "${SKILLS_DIR}/"
    echo "  ✓ ${skill}"
  else
    echo "  ✗ ${skill} — source folder missing in repo, skipping" >&2
  fi
done

# --- 4. Drop USER.md and MEMORY.md starters (do NOT overwrite if they exist) ---
echo "==> Installing starter files..."
if [[ ! -f "${HERMES_DIR}/USER.md" ]]; then
  cp "${REPO_DIR}/config/USER.md.template" "${HERMES_DIR}/USER.md"
  echo "  ✓ USER.md"
else
  echo "  - USER.md already exists, skipping"
fi
if [[ ! -f "${HERMES_DIR}/MEMORY.md" ]]; then
  cp "${REPO_DIR}/config/MEMORY.md.template" "${HERMES_DIR}/MEMORY.md"
  echo "  ✓ MEMORY.md"
else
  echo "  - MEMORY.md already exists, skipping"
fi

# --- 5. Install config.yaml ---
echo "==> Installing config.yaml..."
if [[ -f "${HERMES_DIR}/config.yaml" ]]; then
  cp "${HERMES_DIR}/config.yaml" "${HERMES_DIR}/config.yaml.bak.$(date +%s)"
  echo "  (backed up existing config.yaml)"
fi
cp "${REPO_DIR}/config/config.yaml" "${HERMES_DIR}/config.yaml"
echo "  ✓ config.yaml"

# --- 6. Verification ---
echo ""
echo "==> Verification"
echo ""
echo "--- hermes doctor ---"
hermes doctor || true
echo ""
echo "--- hermes plugins list (enabled only) ---"
hermes plugins list | grep -E '\[✓\]' || true
echo ""
echo "--- hermes skills list ---"
hermes skills list || true
echo ""
echo "==> Done."
echo ""
echo "Next steps before snapshot-to-template:"
echo "  - Fill ${HERMES_DIR}/USER.md placeholders OR leave for tenant onboarding"
echo "  - Clear runtime state:  hermes sessions clear && rm -rf ${HERMES_DIR}/logs/* ${HERMES_DIR}/cache/*"
echo "  - Run template-prep:    SSH host keys, machine-id, cloud-init clean, bash history, apt cache"
echo "  - On NEST (root):       qm shutdown 100 && qm template 100"
