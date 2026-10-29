provider "aws" {
}

# create the VPC
data "aws_vpc" "My_VPC" {
  default = true
} # end resource

# Create the Security Group
resource "aws_security_group" "My_VPC_Security_Group" {
  vpc_id      = data.aws_vpc.My_VPC.id
  name        = var.security_group_name
  description = var.security_group_name

  # allow ingress of port 22
  ingress {
    cidr_blocks = var.ingressCIDRblock
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
  }

  # allow egress of all ports
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name        = var.security_group_name
    Description = var.security_group_name
  }
} # end resource

