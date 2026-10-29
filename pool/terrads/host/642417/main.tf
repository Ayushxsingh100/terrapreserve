# Security Group for Web App
resource "aws_security_group" "webapp" {
  name        = "${var.name_prefix}-webapp-sg"
  description = "Security group for web application server"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Glances monitoring"
    from_port   = 61208
    to_port     = 61208
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH access via bastion (when bastion exists)
  dynamic "ingress" {
    for_each = var.bastion_vpc_cidr != "" ? [1] : []
    content {
      description = "SSH access via bastion"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [var.bastion_vpc_cidr]
    }
  }

  # EMERGENCY: Uncomment the block below for temporary direct SSH access when absolutely needed
  # ingress {
  #   description = "EMERGENCY: Direct SSH access (TEMPORARY ONLY)"
  #   from_port   = 22
  #   to_port     = 22
  #   protocol    = "tcp"
  #   cidr_blocks = [var.my_ip]
  # }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-webapp-sg"
  })
}

# Security Group for Database
resource "aws_security_group" "database" {
  name        = "${var.name_prefix}-database-sg"
  description = "Security group for database server"
  vpc_id      = var.vpc_id

  ingress {
    description     = "MySQL from webapp"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.webapp.id]
  }

  ingress {
    description     = "Redis from webapp"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.webapp.id]
  }

  # SSH access via bastion (when bastion exists)
  dynamic "ingress" {
    for_each = var.bastion_vpc_cidr != "" ? [1] : []
    content {
      description = "SSH access via bastion"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [var.bastion_vpc_cidr]
    }
  }

  # EMERGENCY: Uncomment the block below for temporary direct SSH access when absolutely needed
  # ingress {
  #   description = "EMERGENCY: Direct SSH access (TEMPORARY ONLY)"
  #   from_port   = 22
  #   to_port     = 22
  #   protocol    = "tcp"
  #   cidr_blocks = [var.my_ip]
  # }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-database-sg"
  })
}

# Security Group for Bastion
resource "aws_security_group" "bastion" {
  name        = "${var.name_prefix}-bastion-sg"
  description = "Security group for bastion host"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH from my IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-bastion-sg"
  })
}