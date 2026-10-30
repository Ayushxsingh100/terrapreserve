resource "aws_instance" "ec2_pub" {
  ami                    = var.compute_ami_id
  instance_type          = var.compute_instance_type
  subnet_id              = var.network_subnet_pub_id
  vpc_security_group_ids = [aws_security_group.sg_pub.id]
  key_name               = var.compute_key_name
  tags = {
    Name = "ec2_pub"
  }
}

resource "aws_instance" "ec2_priv" {
  ami                    = var.compute_ami_id
  instance_type          = var.compute_instance_type
  subnet_id              = var.network_subnet_priv_id
  vpc_security_group_ids = [aws_security_group.sg_priv.id]
  key_name               = var.compute_key_name
  tags = {
    Name = "ec2_priv"
  }
}

resource "aws_security_group" "sg_pub" {
  vpc_id = var.network_vpc_pub_id
  egress {
    from_port   = "0"
    to_port     = "0"
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = "0"
    to_port     = "0"
    protocol    = "-1"
    cidr_blocks = ["${var.network_vpc_pub_cidr_block}"]
  }
  ingress {
    from_port   = "0"
    to_port     = "0"
    protocol    = "-1"
    cidr_blocks = ["${var.network_vpc_priv_cidr_block}"]
  }
  ingress {
    from_port   = "3389"
    to_port     = "3389"
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = "22"
    to_port     = "22"
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = "-1"
    to_port     = "-1"
    protocol    = "icmp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "sg_priv" {
  vpc_id = var.network_vpc_priv_id
  egress {
    from_port   = "0"
    to_port     = "0"
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = "0"
    to_port     = "0"
    protocol    = "-1"
    cidr_blocks = ["${var.network_vpc_pub_cidr_block}"]
  }
  ingress {
    from_port   = "0"
    to_port     = "0"
    protocol    = "-1"
    cidr_blocks = ["${var.network_vpc_priv_cidr_block}"]
  }
}
