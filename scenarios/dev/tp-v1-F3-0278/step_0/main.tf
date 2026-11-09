# modules/security_groups/main.tf

# --- Client VPN Endpoint Security Group ---
# Attached to the Client VPN Endpoint itself. Allows outbound traffic.
# Inbound rules are typically not needed here unless specific management access is required.
resource "aws_security_group" "vpn_endpoint_sg" {
  name        = "${var.project_name}-vpn-endpoint-sg"
  description = "Allow outbound traffic from VPN Endpoint. Inbound handled by VPN auth/routes."
  vpc_id      = var.vpc_id

  ingress {
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = [var.client_vpn_cidr]
}

  # Allow all outbound traffic from the VPN endpoint (adjust if needed)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  tags = {
      Name = "${var.project_name}-vpn-endpoint-sg"
    }
}


# --- ALB Security Group ---
# Allows inbound HTTPS from Client VPN CIDR. Allows outbound to EC2 SG.
resource "aws_security_group" "alb_sg" {
  name        = "${var.project_name}-alb-sg"
  description = "Allow HTTPS from Client VPN CIDR to ALB"
  vpc_id      = var.vpc_id

  # Inbound HTTPS (TLS) from Client VPN Network
  ingress {
    description     = "HTTPS from Client VPN"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    cidr_blocks     = var.public_subnet_cidrs # Allow traffic originating from VPN clients
  }

  # Allow all outbound traffic (needed to reach EC2 instances)
  egress {
    from_port   = var.ec2_app_port
    to_port     = var.ec2_app_port
    protocol    = "tcp"
    cidr_blocks = var.private_subnet_cidrs
  }

  egress {
    from_port   = var.ec2_app_port_health
    to_port     = var.ec2_app_port_health
    protocol    = "tcp"
    cidr_blocks = var.private_subnet_cidrs
  }

  tags ={
      Name = "${var.project_name}-alb-sg"
    }
}

# --- EC2 Instance Security Group ---
# Allows inbound traffic from ALB SG on App Port. Allows outbound to RDS SG and Internet (via NAT).
resource "aws_security_group" "ec2_sg" {
  name        = "${var.project_name}-ec2-sg"
  description = "Allow App traffic from ALB and outbound to RDS/Internet"
  vpc_id      = var.vpc_id

  # Inbound traffic from ALB on the application port
  ingress {
    description     = "Allow traffic from ALB"
    from_port       = var.ec2_app_port
    to_port         = var.ec2_app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id] # Only allow from the ALB SG
  }

  ingress {
    description     = "Allow traffic from ALB for health check"
    from_port       = var.ec2_app_port_health
    to_port         = var.ec2_app_port_health
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id] # Only allow from the ALB SG
  }

  # Allow all outbound traffic (for RDS, Internet via NAT, etc.)
  egress {
  from_port   = 3306 # o el puerto de tu RDS
  to_port     = 3306
  protocol    = "tcp"
  cidr_blocks = var.isolated_subnet_cidrs
}

  tags = {
      Name = "${var.project_name}-ec2-sg"
    }
}

# --- RDS Security Group ---
# Allows inbound MySQL traffic only from EC2 SG.
resource "aws_security_group" "rds_sg" {
  name        = "${var.project_name}-rds-sg"
  description = "Allow MySQL traffic from EC2 instances"
  vpc_id      = var.vpc_id

  # Inbound MySQL traffic from EC2 instances
  ingress {
    description     = "MySQL from EC2 SG"
    from_port       = 3306 # Standard MySQL port
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id] # Only allow from the EC2 SG
  }

  # Outbound traffic is typically not restricted, but can be if needed.
  # Default allows all outbound.

  tags = {
      Name = "${var.project_name}-rds-sg"
    }
}