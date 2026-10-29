# Define the provider
provider "aws" {
  region = "us-east-2" # Replace with your desired AWS region
}

# Create a VPC
resource "aws_vpc" "gp_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "gp-vpc"
  }
}

# Create a subnet
resource "aws_subnet" "gp_subnet" {
  vpc_id     = aws_vpc.gp_vpc.id
  cidr_block = "10.0.1.0/24"

  tags = {
    Name = "gp-subnet"
  }
}

# Create a security group
resource "aws_security_group" "gp_sg" {
  name   = "gpSecurityGroup"
  vpc_id = aws_vpc.gp_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Replace with your desired IP range
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"]
  }

  tags = {
    Name = "gpSecurityGroup"
  }
}



# Create coordinator EC2 instance
resource "aws_instance" "gp_instances-cdw" {
  for_each = var.instances
  ami       	= each.value.ami # Amazon Linux 2 AMI
  instance_type = each.value.instance_type             # Adjust instance type as needed
  subnet_id                   = aws_subnet.gp_subnet.id
  vpc_security_group_ids      = [aws_security_group.gp_sg.id]
  associate_public_ip_address = true

  root_block_device {
    volume_type = "gp2"
    volume_size = each.value.volumeSize # Adjust volume size as needed
  }

  # key pair name for ec2 instances
   key_name = var.key_name

  tags = {
    Name = each.value.name
  }
}

# Create segments EC2 instance
resource "aws_instance" "gp_instances-sdw" {

  count = var.count_sdw
  ami       	= var.instances-sdw[0].ami # Amazon Linux 2 AMI
  instance_type = var.instances-sdw[0].instance_type            # Adjust instance type as needed
  subnet_id                   = aws_subnet.gp_subnet.id
  vpc_security_group_ids      = [aws_security_group.gp_sg.id]
  associate_public_ip_address = true

  root_block_device {
    volume_type = "gp2"
    volume_size = var.instances-sdw[0].volumeSize # Adjust volume size as needed
  }

  # key pair name for ec2 instances
   key_name = var.key_name

  tags = {
    Name = "${var.instances-sdw[0].name}${count.index}" 
  }
}