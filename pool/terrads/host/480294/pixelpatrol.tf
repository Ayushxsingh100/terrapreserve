provider "aws" {
  region = "us-east-2"
  profile = "wmmc"
}

resource "aws_security_group" "metalpixelscanner_sg" {
  name        = "metalpixelscanner_sg"
  description = "Security group for metalpixelscanner instance"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["47.233.93.152/32"]
  }
}

resource "aws_instance" "metalpixelscanner" {
  ami           = "ami-0fdb6f3d91cc213d5"
  instance_type = "t3.large"
  key_name = "wmmc_east2"
  vpc_security_group_ids = [aws_security_group.metalpixelscanner_sg.id]
  root_block_device {
    volume_size = 20
  }
  tags = {
    Name = "metalpixelscanner"
  }
}
