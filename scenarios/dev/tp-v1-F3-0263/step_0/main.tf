##########################################################
# Firewall Configuration
# 1) Create a Security Group for generell firewall rules (aws_security_group.firewall-1) to manage ICMP,SSM,HTTP,HTTPS
# 2) Create a Security Group for EC2 API (aws_security_group.ec2_sg) to allow API traffic only from the ALB
# 3) Restrict EC2 access by allowing inbound HTTP traffic exclusively from the ALB for security 
# 4) Allow outbound traffic to the internet so EC2 can connect to AWS services like S3 and CloudWatch 
# 5) Attach Security Groups to EC2 Network Interfaces (aws_network_interface.network-interface-1) for proper security enforcement
##########################################################

resource "aws_security_group" "firewall-1" {
  vpc_id = var.vpc_id
  name = "${var.prefix}-firewall-1"
  description = "Allow: IN[ICMP, SSM, HTTP, HTTPS], OUT[*]"

  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      protocol    = ingress.value.protocol
      cidr_blocks = contains(ingress.value.cidr_blocks, "0.0.0.0/0") ? var.accessible_from : ingress.value.cidr_blocks
    }
  }
  egress {
     from_port = 80
     to_port = 80
     protocol = "tcp"
     cidr_blocks = ["0.0.0.0/0"] 
    }
  egress {
    from_port = 443
    to_port = 443
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ec2_sg" {
  vpc_id = var.vpc_id
  name   = "ec2-api-security-group"
  description = "Allow traffic from ALB only"

  # Allow outbound HTTPS traffic (for S3, CloudFront, and other AWS services)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # EC2 Instance can communicate privately with all AWS services
}

  tags = {
    Name = "${var.prefix}-EC2-API-SG"
  }
}
# ALB Security Group
resource "aws_security_group" "alb_sg" {
  vpc_id      = var.vpc_id
  name        = "alb-security-group"
  description = "Allow HTTPS/HTTP traffic to ALB"

  ingress {
    from_port   = 80  # Allow HTTP traffic for redirection
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443 # Just allows HTTPS fur further processing
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Allow ALB to send traffic to EC2
resource "aws_security_group_rule" "alb_to_ec2" {
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ec2_sg.id
  source_security_group_id = aws_security_group.alb_sg.id
}

# Allow EC2 to respond to ALB
resource "aws_security_group_rule" "ec2_to_alb" {
  type                     = "egress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  security_group_id        = aws_security_group.alb_sg.id
  source_security_group_id = aws_security_group.ec2_sg.id
}

# SSM Interface Security Group

resource "aws_security_group" "ssm_sg" {
  vpc_id = var.vpc_id
  name   = "SSM-Endpoint-SG"

  # Allow inbound traffic to SSM Interface Endpoint (Only from your vpc)
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]  
  }

  # Allow EC2 instances **within this subnet** to communicate with SSM
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.private_subnet_cidr]  # Restrict outgoing traffic to private-subnet
  }

  tags = {
    Name = "${var.prefix}-SSM-Security-Group"
  }
}
