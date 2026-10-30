provider "aws" {
  region = "eu-west-3"
}

resource "aws_security_group" "this" {
  vpc_id = "vpc-05a348e6827173c72"

  ingress {
    from_port   = "0"
    to_port     = "22"
    protocol    = "TCP"
    cidr_blocks = ["176.174.76.134/32"]
  }

  ingress {
    from_port   = "0"
    to_port     = "80"
    protocol    = "TCP"
    cidr_blocks = ["176.174.76.134/32"]
  }

  ingress {
    from_port   = "-1"
    to_port     = "-1"
    protocol    = "icmp"
    cidr_blocks = ["176.174.76.134/32"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

}

resource "aws_instance" "this" {
  ami                    = "ami-032c8dff9a658a260"
  instance_type          = "t3.micro"
  subnet_id              = "subnet-0464f53eae6711dc7"
  vpc_security_group_ids = [aws_security_group.this.id]
  monitoring             = true
  key_name               = "demo"

  root_block_device {
    delete_on_termination = true
    volume_size           = 15
    encrypted             = false
  }

}
