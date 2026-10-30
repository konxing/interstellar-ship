#!/usr/bin/env bash
# Serve the repository root so the viewer can reach ../models/glb over HTTP.
#
#   ./scripts/serve.sh [port]
#
# Then open http://localhost:<port>/viewer/ in a browser.
set -euo pipefail

PORT="${1:-8000}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Serving ${ROOT} at http://localhost:${PORT}/viewer/"
echo "Press Ctrl-C to stop."
cd "${ROOT}"
exec python3 -m http.server "${PORT}" --bind 0.0.0.0
