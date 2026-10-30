#!/usr/bin/env bash
# Publish the feature branch to GitHub and print ready-to-use PR guidance.
#
#   ./scripts/publish.sh <github-owner> [repo-name]
#
# The repository is expected to already exist on GitHub (created via the GitHub
# integration). This script only adds the remote (if missing) and pushes the
# current feature branch; it never touches main and never force-pushes.
set -euo pipefail

OWNER="${1:?usage: publish.sh <github-owner> [repo-name]}"
REPO="${2:-deep-space-exploration-ship}"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
REMOTE_URL="https://github.com/${OWNER}/${REPO}.git"

if [[ "${BRANCH}" == "main" || "${BRANCH}" == "master" ]]; then
  echo "refusing to publish from ${BRANCH}; switch to the feature branch first" >&2
  exit 1
fi

if git remote get-url origin >/dev/null 2>&1; then
  echo "remote origin already set: $(git remote get-url origin)"
else
  git remote add origin "${REMOTE_URL}"
  echo "added remote origin -> ${REMOTE_URL}"
fi

echo "pushing ${BRANCH} (no force)..."
git push --set-upstream origin "${BRANCH}"

cat <<EOF

Branch pushed. Open a pull request:

  https://github.com/${OWNER}/${REPO}/compare/main...${BRANCH}

Suggested title:
  feat: DSX-01 Kairos Horizon procedural 3D modelling workbench

The full PR body is in docs/PULL_REQUEST.md.
EOF
