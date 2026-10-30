# Security Groups Module for Nomad Cluster

# SSH Security Group
resource "aws_security_group" "ssh" {
  name_prefix = "${var.name_prefix}-ssh"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ssh-sg"
  })
}

# Nomad Server Security Group
resource "aws_security_group" "nomad_server" {
  name_prefix = "${var.name_prefix}-nomad-server"
  vpc_id      = var.vpc_id

  # Nomad server RPC
  ingress {
    description = "Nomad server RPC"
    from_port   = 4647
    to_port     = 4647
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  # Nomad server HTTP API
  ingress {
    description = "Nomad server HTTP API"
    from_port   = 4646
    to_port     = 4646
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  # Serf WAN
  ingress {
    description = "Serf WAN"
    from_port   = 8302
    to_port     = 8302
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  # Serf LAN
  ingress {
    description = "Serf LAN"
    from_port   = 8301
    to_port     = 8301
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  # Consul RPC
  ingress {
    description = "Consul RPC"
    from_port   = 8300
    to_port     = 8300
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-nomad-server-sg"
  })
}

# Nomad Client Security Group
resource "aws_security_group" "nomad_client" {
  name_prefix = "${var.name_prefix}-nomad-client"
  vpc_id      = var.vpc_id

  # Nomad client HTTP
  ingress {
    description = "Nomad client HTTP"
    from_port   = 4646
    to_port     = 4646
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  # Dynamic ports for tasks
  ingress {
    description = "Dynamic ports for tasks"
    from_port   = 20000
    to_port     = 32000
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  # Dynamic ports for tasks (UDP)
  ingress {
    description = "Dynamic ports for tasks (UDP)"
    from_port   = 20000
    to_port     = 32000
    protocol    = "udp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-nomad-client-sg"
  })
}

# Application Load Balancer Security Group
resource "aws_security_group" "alb" {
  name_prefix = "${var.name_prefix}-alb"
  vpc_id      = var.vpc_id

  # HTTPS
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP (redirect to HTTPS)
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-alb-sg"
  })
}

# Data source for VPC
data "aws_vpc" "main" {
  id = var.vpc_id
}
