locals {
  name       = "${replace(var.vpc_id, "/[^a-zA-Z0-9_\\-\\.]/", "")}-${var.label}"
  #subnet_ids = concat(var.subnet_ids_pri, var.subnet_ids_pub) - single SN approach
  #subnet_ids = var.subnets_ids
  #  sunet_len           = length(local.subnet_ids)
  # sunet_len           = var.subnet_count_private + var.subnet_count_public - single SN approach
  sunet_len           = length(var.subnets_ids)
  base_security_group = var.base_security_group != null ? var.base_security_group : data.aws_security_group.newsg.id
  ssh_security_group_rule = var.allow_ssh_from != "" ? [{
    name        = "ssh-i"
    type        = "ingress"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allow_ssh_from
    }, /*{
    name        = "ssh-internal"
    type        = "ingress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
#    cidr_blocks = cidrsubnet(data.aws_vpc.swe_vpc.cidr_block, 4, 1)
     cidr_blocks = var.cidr_block
    },*/ {
    name        = "all-e"
    type        = "egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = var.allow_ssh_from
  }] : []
  security_group_rules = concat(local.ssh_security_group_rule, var.security_group_rules)
}

data "aws_vpc" "swe_vpc" {
  id = var.vpc_id
}

output "ciders" {
  value = data.aws_vpc.swe_vpc.cidr_block
}

resource "aws_security_group" "ec2instance" {
  name   = "${var.name_prefix}-inst-sg-group"
  vpc_id = var.vpc_id

  tags = {
    Name = "${var.name_prefix}-inst-sg-group"
  }
}

data "aws_security_group" "newsg" {
  id = aws_security_group.ec2instance.id
}


resource "aws_security_group_rule" "addSGrule" {

  count             = length(local.security_group_rules)
  security_group_id = local.base_security_group
  type              = local.security_group_rules[count.index]["type"]
  from_port         = lookup(local.security_group_rules[count.index], "from_port", null)
  to_port           = lookup(local.security_group_rules[count.index], "to_port", null)
  protocol          = lookup(local.security_group_rules[count.index], "protocol", null)
  cidr_blocks       = lookup(local.security_group_rules[count.index], "cidr_blocks", null)
  #  ip_version        = lookup(local.security_group_rules[count.index], "ip_version", null)

}

resource "aws_instance" "ec2_instance" {
  ami                         = var.ami_id
  instance_type               = var.instance_type
  count                       = local.sunet_len
#  subnet_id                   = element(local.subnet_ids, count.index) - single SN approach
#  subnet_id                   = local.subnet_ids
  subnet_id                   = var.subnets_ids[count.index]
  monitoring                  = var.pri_instance_monitoring
  user_data                   = var.init_script != "" ? var.init_script : file("${path.module}/scripts/init-script-ubuntu.sh")
  vpc_security_group_ids      = ["${aws_security_group.ec2instance.id}"]
  key_name                    = var.ssh_key
  associate_public_ip_address = var.publicIP
  root_block_device {
    delete_on_termination = true
    encrypted             = var.root_block_device_encrypted
    kms_key_id            = var.kms_key_id
    volume_size           = var.root_volume_size
    volume_type           = var.root_volume_type
  }

  tags = {
    "Name"    = "${format("%s-%s-%02s", var.name_prefix, var.label, count.index + 1)}"
    "project" = "swe"
  }
}

