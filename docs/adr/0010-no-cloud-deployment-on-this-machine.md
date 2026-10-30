# 0010: Deployment checked by validation, not by running in the cloud

**Status:** Accepted, 2026-10-29. Decided without the owner, under the instruction to finish the project and take decisions where blocked.

## Context
Week 11 asks for a deployment to Kubernetes and AWS with a rollback demonstration. This machine has no cluster, no kind or Helm installed, and no AWS account or credentials. Creating cloud resources would also cost money and needs the owner's account.

## Decision
- Helm chart: linted and rendered with Helm 3.16.2 in a container (`infra/helm/meridian-api`).
- Terraform (ECS Fargate): validated with Terraform 1.9.8 in a container (`infra/terraform/ecs-api`). Not applied. The admin token is a Secrets Manager reference, not a value.
- Prometheus: rules and config validated with promtool 2.54.1 (`infra/docker/`).
- The API image was built and run locally with Docker, and health and chat were checked against it.

## Consequences
- No cloud endpoint exists, so the "public demo URL" acceptance item is not met.
- Rollback is described in `docs/product/LAUNCH.md` (kill-switch and model alias) but has not been run against a live deployment.
