provider "aws" {
  region = "us-west-2"  # Change this to your desired region
}

# resource "aws_key_pair" "ts-pcluster-keypair" {
  # key_name   = "ts-pcluster-keypair"
  # public_key = file("id_rsa.pub")  # Path to your public key file
# }


resource "aws_security_group" "ts_pcluster_sg_v1" {
  name_prefix = "ts-pcluster-sg-v1"
  description = "Security group for ts-pcluster"

  vpc_id = "vpc-0055752230db6161d"  # Replace with your VPC ID

  egress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ts-pcluster-sg-v1"
  }
}

