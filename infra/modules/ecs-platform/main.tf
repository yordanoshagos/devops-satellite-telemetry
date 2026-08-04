resource "aws_service_discovery_http_namespace" "this" {
  name = var.service_connect_namespace
  tags = var.tags
}

resource "aws_ecs_cluster" "this" {
  name = var.cluster_name

  service_connect_defaults {
    namespace = aws_service_discovery_http_namespace.this.arn
  }

  tags = var.tags
}
