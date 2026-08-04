# Service B (telemetry-parser) inputs — owned by service-b-owner.
#
# Scope (clash rule): this file is the ONLY place service-b-owner writes into
# infra/environments/lab/. Port 3002, desired_count 1, and no-ALB attachment
# are locked in main.tf by the platform owner (see docs/iac-ecs-greenfield-lab
# /06-names-and-tags.md) and must not be duplicated here.
#
# Placeholder SHA: 0000000 is a valid 7-char hex string that satisfies the
# module's :sha-<7..40 hex> validation so terraform plan/validate succeeds
# before an image exists. It intentionally will NOT pull at apply time — the
# release owner replaces it with the real sha-<gitsha> once the image is
# built and pushed to devops-g10-telemetry-parser (see docs/iac-ecs-greenfield
# -lab/09-release-ownership.md).

image_sha_telemetry_parser = "0000000"
