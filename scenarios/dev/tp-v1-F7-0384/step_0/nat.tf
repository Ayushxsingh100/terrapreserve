data "aws_ami" "nat" {
  most_recent = true
  owners      = [local.nat_ami_owner]
  filter {
    name   = "architecture"
    values = [local.nat_ami_arch]
  }
  filter {
    name   = "name"
    values = [local.nat_ami_name]
  }
}

resource "aws_security_group" "nat" {
  name   = "nat-${local.identifier}"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "nat-${local.identifier}"
  }
}

resource "aws_instance" "nat" {
  ami                         = data.aws_ami.nat.id
  instance_type               = local.nat_instance_type
  associate_public_ip_address = true
  ebs_optimized               = true
  subnet_id                   = aws_subnet.public[0].id
  source_dest_check           = false

  vpc_security_group_ids = [aws_security_group.nat.id]

  instance_market_options {
    market_type = "spot"
    spot_options {
      max_price = local.nat_max_spot_price
    }
  }

  tags = {
    Name = "nat-${local.identifier}"
  }
}