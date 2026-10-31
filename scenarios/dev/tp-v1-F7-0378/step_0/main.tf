# --- Security Group ----------------------------------------------------------
resource "aws_security_group" "worker_sg" {
  name        = "${local.snake_case_name}_sg"
  description = "${var.name} Security Group"
  vpc_id      = var.vpc_id
}

resource "aws_security_group_rule" "worker_ssh_ingress" {
  type                     = "ingress"
  description              = "Allow SSH ingress from bastion"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  source_security_group_id = var.bastion_sg_id
  security_group_id        = aws_security_group.worker_sg.id
}

resource "aws_security_group_rule" "worker_egress" {
  type              = "egress"
  description       = "Allow all egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.worker_sg.id
}

# --- EC2 ---------------------------------------------------------------------
resource "aws_instance" "worker" {
  ami                    = var.ami_id
  instance_type          = "t3.micro"
  vpc_security_group_ids = [aws_security_group.worker_sg.id]
  subnet_id              = var.subnet_id

  iam_instance_profile = var.instance_profile_name
  user_data            = templatefile(var.user_data_template, {})

  dynamic "ebs_block_device" {
    for_each = { for block_device in var.block_devices : block_device.name => block_device }

    content {
      device_name = ebs_block_device.key
      snapshot_id = ebs_block_device.value.snapshot_id
      volume_size = ebs_block_device.value.volume_size
    }
  }

  tags = {
    Type = local.snake_case_name
    Name = var.name
  }
}
