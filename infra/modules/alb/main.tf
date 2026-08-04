# Internet-facing ALB for Service A only.
# Target registration happens later via modules/ecs-service (enable_alb + target_group_arn).

resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}alb-sg"
  description = "ALB SG: allow HTTP from internet; app ports stay closed to 0.0.0.0/0"
  vpc_id      = var.vpc_id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}alb-sg"
  })
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "Internet HTTP to ALB listener"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}alb-ingress-80"
  })
}

resource "aws_vpc_security_group_egress_rule" "alb_all" {
  security_group_id = aws_security_group.alb.id
  description       = "Allow ALB to reach targets (Service A on container_port via SG refs on A)"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}alb-egress-all"
  })
}

resource "aws_lb_target_group" "service_a" {
  name        = "${var.name_prefix}tg"
  port        = var.container_port
  protocol    = "HTTP"
  target_type = "ip" # required for Fargate awsvpc — do not change to instance
  vpc_id      = var.vpc_id

  health_check {
    enabled             = true
    path                = var.health_check_path
    port                = "traffic-port"
    protocol            = "HTTP"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}tg"
  })

  lifecycle {
    precondition {
      condition     = length(var.public_subnet_ids) >= 2
      error_message = "ALB target group wiring requires the ALB to span at least two public subnets."
    }
  }
}

resource "aws_lb" "this" {
  name               = "${var.name_prefix}alb"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  tags = merge(var.tags, {
    Name = "${var.name_prefix}alb"
  })
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.service_a.arn
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}alb-listener-80"
  })
}
