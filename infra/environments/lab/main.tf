module "network" {
  source = "../../modules/network"

  tags = var.tags
}

module "platform" {
  source = "../../modules/ecs-platform"

  # group10.internal (the module default) already belongs to the console-based
  # ecs-fargate-lab's live Service Connect namespace. Reusing it here fails with
  # NamespaceAlreadyExists, and even if imported, the next `terraform destroy` on
  # this workload would delete a namespace the console lab still depends on.
  service_connect_namespace = "group10-iac.internal"

  tags = var.tags
}

module "alb" {
  source = "../../modules/alb"

  vpc_id            = module.network.vpc_id
  public_subnet_ids = module.network.public_subnet_ids
  container_port    = 3001

  tags = var.tags
}

# ECR lives here, not inside ecs-service: ecs-service's own README already
# documents "Does not create: ... ECR repositories", and a service module
# shouldn't own artifact storage. Note: since these repos live in the
# workload stack (not bootstrap), destroying this stack between demo
# cycles destroys pushed images too, so force_destroy is on to keep that
# workflow simple.
#
# Named devops-g10-iac-<app>, not devops-g10-<app>: the latter already belongs
# to the console-based ecs-fargate-lab's live ECR repos (real pushed images,
# still in use). Reusing those names collides on create, and importing them
# would put live console-lab artifacts inside this workload's destroy path.
resource "aws_ecr_repository" "ground_station_api" {
  name                 = "devops-g10-iac-ground-station-api"
  image_tag_mutability = "IMMUTABLE" # enforces decision card 4 (immutable image SHA) at the registry level
  force_delete         = true

  tags = merge(var.tags, { Owner = "service-a-owner" })
}

resource "aws_ecr_repository" "telemetry_parser" {
  name                 = "devops-g10-iac-telemetry-parser"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  tags = merge(var.tags, { Owner = "service-b-owner" })
}

resource "aws_ecr_repository" "anomaly_detector" {
  name                 = "devops-g10-iac-anomaly-detector"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  tags = merge(var.tags, { Owner = "service-c-owner" })
}

module "service_a" {
  source = "../../modules/ecs-service"

  # devops-g10-iac-, not the module's devops-g10- default: that prefix drives
  # the task-def family, log-group, and SG names, which already exist for
  # the console-based ecs-fargate-lab under devops-g10-<app>. See the ECR
  # comment above for the same collision reasoning.
  name_prefix          = "devops-g10-iac-"
  name                 = "ground-station-api"
  service_connect_name = "service-a"
  container_port       = 3001
  desired_count        = 2

  image = "${aws_ecr_repository.ground_station_api.repository_url}:sha-${var.image_sha_ground_station_api}"

  cluster_arn                   = module.platform.cluster_arn
  service_connect_namespace_arn = module.platform.service_connect_namespace_arn
  task_execution_role_arn       = module.platform.execution_role_arn
  task_role_arn                 = module.platform.task_role_arn

  private_subnet_ids = module.network.private_subnet_ids
  vpc_id             = module.network.vpc_id

  enable_alb            = true
  alb_target_group_arn  = module.alb.target_group_arn
  alb_security_group_id = module.alb.alb_sg_id

  tags = merge(var.tags, { Owner = "service-a-owner" })
}

module "service_b" {
  source = "../../modules/ecs-service"

  name_prefix          = "devops-g10-iac-"
  name                 = "telemetry-parser"
  service_connect_name = "service-b"
  container_port       = 3002
  desired_count        = 1

  image = "${aws_ecr_repository.telemetry_parser.repository_url}:sha-${var.image_sha_telemetry_parser}"

  cluster_arn                   = module.platform.cluster_arn
  service_connect_namespace_arn = module.platform.service_connect_namespace_arn
  task_execution_role_arn       = module.platform.execution_role_arn
  task_role_arn                 = module.platform.task_role_arn

  private_subnet_ids = module.network.private_subnet_ids
  vpc_id             = module.network.vpc_id

  # A -> B, per docs/iac-ecs-greenfield-lab/05-sg-matrix-traffic.md
  ingress_source_sg_ids = [module.service_a.security_group_id]

  tags = merge(var.tags, { Owner = "service-b-owner" })
}

module "service_c" {
  source = "../../modules/ecs-service"

  name_prefix          = "devops-g10-iac-"
  name                 = "anomaly-detector"
  service_connect_name = "service-c"
  container_port       = 3003
  desired_count        = 1

  image = "${aws_ecr_repository.anomaly_detector.repository_url}:sha-${var.image_sha_anomaly_detector}"

  cluster_arn                   = module.platform.cluster_arn
  service_connect_namespace_arn = module.platform.service_connect_namespace_arn
  task_execution_role_arn       = module.platform.execution_role_arn
  task_role_arn                 = module.platform.task_role_arn

  private_subnet_ids = module.network.private_subnet_ids
  vpc_id             = module.network.vpc_id

  # B -> C, per docs/iac-ecs-greenfield-lab/05-sg-matrix-traffic.md
  ingress_source_sg_ids = [module.service_b.security_group_id]

  tags = merge(var.tags, { Owner = "service-c-owner" })
}

# Callback edge C -> A on port 3001 (docs/iac-ecs-greenfield-lab/05-sg-matrix-traffic.md).
# Deliberately NOT wired through service_a's ingress_source_sg_ids: that would make
# service_a depend on service_c, while service_c already depends on service_b, which
# depends on service_a — a circular module dependency. Adding it as a standalone rule
# after all three services exist keeps the graph a straight line (A -> B -> C -> this rule).
# Forward A -> C stays denied by the absence of any rule for that pair.
resource "aws_vpc_security_group_ingress_rule" "callback_c_to_a" {
  security_group_id            = module.service_a.security_group_id
  referenced_security_group_id = module.service_c.security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 3001
  to_port                      = 3001
  description                  = "Callback from C to A on 3001 (service C calling service A /callback)"
  tags                         = var.tags
}
