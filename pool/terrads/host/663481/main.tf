resource "aws_security_group" "vpc_link_sg" {
  name_prefix = "${var.project_name}-vpc-link"
  vpc_id      = data.aws_vpc.this.id
}

resource "aws_security_group_rule" "egress_vpc_link_to_lb" {
  type                     = "egress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  security_group_id        = aws_security_group.vpc_link_sg.id
  source_security_group_id = aws_security_group.lb_sg.id
}

resource "aws_security_group" "lb_sg" {
  name_prefix = "${var.project_name}-vpc-link-lb"
  vpc_id      = data.aws_vpc.this.id
  description = "Security group for internal ALB/NLB accessible via VPC Link"
}

resource "aws_security_group_rule" "ingress_ecs_to_lb_return" {
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  security_group_id        = aws_security_group.lb_sg.id
  source_security_group_id = aws_security_group.ecs_sg.id
}

resource "aws_security_group_rule" "ingress_ecs_ephemeral_to_lb" {
  type                     = "ingress"
  from_port                = 1024
  to_port                  = 65535
  protocol                 = "tcp"
  security_group_id        = aws_security_group.lb_sg.id
  source_security_group_id = aws_security_group.ecs_sg.id
}

resource "aws_security_group_rule" "ingress_vpc_link_to_lb" {
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  security_group_id        = aws_security_group.lb_sg.id
  source_security_group_id = aws_security_group.vpc_link_sg.id
}

resource "aws_security_group_rule" "egress_lb_to_ecs" {
  type                     = "egress"
  from_port                = var.container_port
  to_port                  = var.container_port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.lb_sg.id
  source_security_group_id = aws_security_group.ecs_sg.id
}

resource "aws_security_group" "ecs_sg" {
  name_prefix = "${var.project_name}-ecs-fargate"
  vpc_id      = data.aws_vpc.this.id
  description = "ECS Fargate tasks"
}

resource "aws_security_group_rule" "ingress_lb_to_ecs" {
  type                     = "ingress"
  from_port                = var.container_port
  to_port                  = var.container_port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ecs_sg.id
  source_security_group_id = aws_security_group.lb_sg.id
}

resource "aws_security_group_rule" "egress_ecs_to_internet" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.ecs_sg.id
}

resource "aws_security_group" "vpc_endpoint" {
  name        = "${var.project_name}-vpc-endpoint-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = data.aws_vpc.this.id
}

resource "aws_security_group_rule" "ingress_vpc_to_https" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = [data.aws_vpc.this.cidr_block]
  security_group_id = aws_security_group.vpc_endpoint.id
}

resource "aws_security_group_rule" "egress_vpc_to_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = [data.aws_vpc.this.cidr_block]
  security_group_id = aws_security_group.vpc_endpoint.id
}
