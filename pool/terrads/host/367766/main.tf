provider "aws" {
  region     = var.region
  #access_key = var.aws_access_key
  #secret_key = var.aws_secret_key
}

data "aws_ami" "avx_ctrl" {
  most_recent = true
  filter {
    name   = "name"
    values = ["*base-ucc-controller-1804-021520-V8*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["679593333241"]
}

resource "aws_security_group" "sg" {
  name   = "${var.instance_name}-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "TCP"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "instance" {
  ami                         = data.aws_ami.avx_ctrl.id
  instance_type               = var.instance_size
  subnet_id                   = var.subnet_id
  associate_public_ip_address = true
  security_groups             = [aws_security_group.sg.id]
  lifecycle {
    ignore_changes = [security_groups]
  }
  tags = {
    Name = var.instance_name
  }
}