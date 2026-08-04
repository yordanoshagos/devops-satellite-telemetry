locals {
  family   = "${var.name_prefix}${var.name}"
  log_name = "/ecs/${local.family}"

  effective_ingress_sg_ids = compact(concat(
    var.ingress_source_sg_ids,
    var.enable_alb && var.alb_security_group_id != null ? [var.alb_security_group_id] : [],
  ))
}

resource "aws_cloudwatch_log_group" "this" {
  name              = local.log_name
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_security_group" "this" {
  name        = "${local.family}-sg"
  description = "SG for ECS service ${var.name}"
  vpc_id      = var.vpc_id
  tags        = var.tags
}

resource "aws_vpc_security_group_ingress_rule" "from_sg" {
  for_each = toset(local.effective_ingress_sg_ids)

  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = each.value
  ip_protocol                  = "tcp"
  from_port                    = var.container_port
  to_port                      = var.container_port
  description                  = "Allow tcp/${var.container_port} from ${each.value}"
  tags                         = var.tags
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.this.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
  description       = "Egress to Internet (NAT) for ECR / CloudWatch"
  tags              = var.tags
}

resource "aws_ecs_task_definition" "this" {
  family                   = local.family
  cpu                      = var.cpu
  memory                   = var.memory
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = var.name
      image     = var.image
      essential = true

      portMappings = [
        {
          name          = var.service_connect_name
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
          appProtocol   = "http"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.this.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = var.name
        }
      }
    }
  ])

  tags = var.tags
}

data "aws_region" "current" {}

resource "aws_ecs_service" "this" {
  name             = var.name
  cluster          = var.cluster_arn
  task_definition  = aws_ecs_task_definition.this.arn
  desired_count    = var.desired_count
  launch_type      = "FARGATE"
  platform_version = "LATEST"
  propagate_tags   = "SERVICE"

  enable_execute_command = var.enable_execute_command

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.this.id]
    assign_public_ip = false
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  service_connect_configuration {
    enabled   = true
    namespace = var.service_connect_namespace_arn

    service {
      port_name      = var.service_connect_name
      discovery_name = var.service_connect_name

      client_alias {
        port     = var.container_port
        dns_name = var.service_connect_name
      }
    }
  }

  dynamic "load_balancer" {
    for_each = var.enable_alb ? [1] : []

    content {
      target_group_arn = var.alb_target_group_arn
      container_name   = var.name
      container_port   = var.container_port
    }
  }

  lifecycle {
    precondition {
      condition     = !var.enable_alb || var.alb_target_group_arn != null
      error_message = "alb_target_group_arn must be set when enable_alb = true."
    }
  }

  tags       = var.tags
  depends_on = [aws_vpc_security_group_ingress_rule.from_sg]
}
