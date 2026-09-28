#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

case "${1:-}" in
  build)
    ansible-playbook -i 'localhost,' ansible/build.yml --tags ci
    ;;
  deploy)
    image="${MIXMASTER_IMAGE:?Set MIXMASTER_IMAGE to the immutable image to deploy}"
    if [[ ! "$image" =~ ^registry\.ttd/mixmaster-ai/mixmaster-ai:h-[a-f0-9]{12,64}$ ]]; then
      echo "MIXMASTER_IMAGE must be an immutable MixMaster AI h-* image" >&2
      exit 2
    fi
    ssh root@ttd-stage 'mkdir -p /opt/mixmaster-ai && cp /opt/mixmaster-ai/docker-compose.yml /opt/mixmaster-ai/docker-compose.rollback.yml'
    scp docker-compose.yml root@ttd-stage:/opt/mixmaster-ai/docker-compose.yml
    ssh root@ttd-stage "cd /opt/mixmaster-ai && MIXMASTER_IMAGE='$image' docker compose pull && MIXMASTER_IMAGE='$image' docker compose up -d --no-build"
    ;;
  *)
    echo "Usage: MIXMASTER_IMAGE=registry.ttd/mixmaster-ai/mixmaster-ai:h-... $0 {build|deploy}" >&2
    exit 2
    ;;
esac
