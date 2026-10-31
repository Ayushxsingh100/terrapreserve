variable "vpc_id" {
    default = "vpc-02196cbcad7b2ce4a"
}

variable "subnet_id" {
    default = "subnet-00d57b3230c2f09c0"
}

variable "key_name" {
    default = "ssh-awsuse1app01"
}

resource "aws_instance" "ecommerce1" {
  ami           = "ami-032930428bf1abbff"
  instance_type = "t3a.medium"
  key_name = var.key_name
  subnet_id = var.subnet_id
  vpc_security_group_ids = [aws_security_group.permitir_ssh_http.id]
  associate_public_ip_address = true

  tags = {
    Name = "ecommerce1"
    ambiente = "bootcamp"
  }
}

resource "aws_security_group" "permitir_ssh_http" {
  name        = "permitir_ssh"
  description = "Permite SSH e HTTP na instancia EC2"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH to EC2"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP to EC2"
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

  tags = {
    Name = "permitir_ssh"
  }
}


