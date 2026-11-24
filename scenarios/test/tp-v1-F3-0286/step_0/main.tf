

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
  ami                         = var.tp_ds_aws_ami_avx_ctrl.id
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