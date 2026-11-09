# # create ec2 instance
# resource "aws_instance" "azure" {
#   ami                         = data.aws_ami.ubuntu.id
#   instance_type               = "t3.nano"
#   associate_public_ip_address = true
#   key_name                    = aws_key_pair.ssh_access_key.key_name
#   subnet_id                   = aws_subnet.main.id
#   security_groups = [aws_security_group.instance_sg.id]
#   user_data_replace_on_change = true
#   user_data                   = file("${path.module}/userdata.sh")

#   tags = {
#     "Name" = "Azure-Instance"
#   }
# }

# Create a VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "celine-vpc"
  }
}

resource "aws_subnet" "main" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name = "azure-subnet"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "azure-gateway"
  }
}

resource "aws_route_table" "example" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0" #allow all
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "azure-route-table"
  }
}

resource "aws_route_table_association" "a" {
  subnet_id      = aws_subnet.main.id
  route_table_id = aws_route_table.example.id
}

# # query AWS for the latest Ubunutu AMI
# data "aws_ami" "ubuntu" {
#   most_recent = true

#   filter {
#     name   = "name"
#     values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
#   }

#   filter {
#     name   = "virtualization-type"
#     values = ["hvm"]
#   }

#   owners = ["099720109477"] # Canonical
# }

# # create an SSH access key
# resource "aws_key_pair" "ssh_access_key" {
#   key_name   = "~/.ssh/twingate_id_rsa"
#   public_key = file("~/.ssh/twingate_id_rsa.pub")
# }

# # tripevibe connector security group
# resource "aws_security_group" "instance_sg" {
#   name        = "instance-sg"
#   description = "allow the tripevibe instance outbound internet access"
#   vpc_id      = aws_vpc.main.id

#   ingress {
#     from_port   = 0
#     to_port     = 1000
#     protocol    = "tcp"
#     cidr_blocks = local.cidr_blocks
#   }

#   egress {
#     from_port   = local.https_port
#     to_port     = local.https_port
#     protocol    = "tcp"
#     cidr_blocks = local.cidr_blocks
#   }

#   egress {
#     from_port   = local.http_port
#     to_port     = local.http_port
#     protocol    = "tcp"
#     cidr_blocks = local.cidr_blocks
#   }

#   tags = local.tags
# }

# locals {
#   https_port      = 443
#   port_zero       = 0
#   http_port       = 80
#   cidr_blocks     = ["0.0.0.0/0"]

#   tags = {
#     Track       = "Cloud/DevOps"
#     Environment = "dev"
#   }
# }