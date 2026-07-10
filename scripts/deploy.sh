#!/usr/bin/env bash
# =============================================================================
# deploy.sh - Deploy a published image tag using docker-compose.prod.yml
# =============================================================================
# Usage:
#   export DOCKERHUB_USERNAME=<dockerhub-username>
#   # APP_NAME defaults to "devops-satellite-telemetry" (the repo name that CI
#   # publishes under); override only if you fork the repo under a new name.
#   ./scripts/deploy.sh sha-<7-40 hex commit hash>
#
# Example:
#   ./scripts/deploy.sh sha-a1b2c3d
# =============================================================================

set -euo pipefail

DEFAULT_APP_NAME="devops-satellite-telemetry"

IMAGE_TAG="${1:-}"

if [ -z "$IMAGE_TAG" ]; then
    echo "Usage: ./scripts/deploy.sh sha-<7-40 hex commit hash>"
    echo "Example: ./scripts/deploy.sh sha-a1b2c3d"
    exit 1
fi

if [ "$IMAGE_TAG" = "latest" ]; then
    echo "Refusing to deploy tag 'latest' - deployments must be pinned to a commit."
    echo "Usage: ./scripts/deploy.sh sha-<7-40 hex commit hash>"
    exit 1
fi

if ! [[ "$IMAGE_TAG" =~ ^sha-[0-9a-f]{7,40}$ ]]; then
    echo "Invalid IMAGE_TAG: '$IMAGE_TAG'"
    echo "Must match: ^sha-[0-9a-f]{7,40}$   (e.g. sha-a1b2c3d)"
    exit 1
fi

if [ -z "${DOCKERHUB_USERNAME:-}" ]; then
    echo "Missing DOCKERHUB_USERNAME"
    echo "  export DOCKERHUB_USERNAME=<dockerhub-username>"
    exit 1
fi

export IMAGE_TAG
export APP_NAME="${APP_NAME:-$DEFAULT_APP_NAME}"
export DOCKERHUB_USERNAME

echo "Deploying ${APP_NAME} using image tag: ${IMAGE_TAG}"

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans --wait --wait-timeout 90
docker compose -f docker-compose.prod.yml ps