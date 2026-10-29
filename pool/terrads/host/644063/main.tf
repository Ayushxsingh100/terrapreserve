locals {
  enabled = var.create
}

resource "aws_security_group" "pods" {
  count       = local.enabled ? 1 : 0
  name        = "${var.name_prefix}-pods"
  description = "Security group for pod-to-pod communication"
  vpc_id      = var.vpc_id

  ingress {
    description = "All pod-to-pod within VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-pods" })
}
