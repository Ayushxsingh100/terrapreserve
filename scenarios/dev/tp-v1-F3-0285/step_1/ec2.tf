resource "aws_instance" "ec2_bat" {
  count = var.bat_count
  ami = var.ec2_ami
  key_name = var.key
  instance_type = var.bat_type
  credit_specification {
    cpu_credits = "standard"
  }
  ebs_block_device {
    device_name = "/dev/xvda"
    volume_size = 30
    volume_type = "gp3"
    encrypted = true
    snapshot_id = var.snapshot_id
    tags = {
      Name    = "${var.bat_tag}0${count.index+1}"
    }
  }
  vpc_security_group_ids = [aws_security_group.bat.id]
  subnet_id     = var.azs[count.index % 3]
  disable_api_termination = var.protect_enable
  tags = {
    Name    = "${var.bat_tag}0${count.index+1}"
  }
}

resource "aws_security_group" "bat" {
  name        = var.bat_tag
  description = "${var.bat_tag} sg"
  vpc_id = var.vpc_id

  ingress {
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [var.admin_sg]
    description     = "ssh"
  }
  ingress {
    from_port       = 10050
    to_port         = 10051
    protocol        = "tcp"
    security_groups = [var.admin_sg]
    description     = "zabbix"
  }
  ingress {
    from_port       = 873
    to_port         = 873
    protocol        = "tcp"
    security_groups = [var.web_sg]
    description     = "sync web2bat"
  }
  ingress {
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    cidr_blocks     = ["0.0.0.0/0"]
    description     = ""
  }
  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"]
  }
  tags = {
    Name = var.bat_tag
  }
  lifecycle {
      create_before_destroy = true
  }
}

output "ec2_bat" {
  value = aws_instance.ec2_bat.*.private_ip
}
output "bat_sg" {
  value = aws_security_group.bat.id
}
output "bat_id" {
  value = aws_instance.ec2_bat.*.id
}