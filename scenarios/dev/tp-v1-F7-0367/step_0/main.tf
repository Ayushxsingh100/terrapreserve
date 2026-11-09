



# code to update SG ingress correctly

resource "aws_security_group_rule" "allow_app" {
  type        = "ingress"
  from_port   = 30011
  to_port     = 30011
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
  security_group_id = var.tp_ds_aws_security_group_selected.id
}

output node_public_ip {
  value = "${var.tp_ds_aws_instance_node_vm.public_ip}"
}

output bigip_private {
  value="${var.tp_ds_aws_instance_bigip.private_ip}"
}

output bigip_public_ip {
  value="${var.tp_ds_aws_instance_bigip.public_ip}"
}
