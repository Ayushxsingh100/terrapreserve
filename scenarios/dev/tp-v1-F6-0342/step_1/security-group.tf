

resource "aws_security_group" "allow_tls" {
  name = "allow_tls"
  description = "Allow TLS inbound traffic"

  ingress {
    description = "TLS for VPC inbound"
    cidr_blocks = [ "${var.tp_ds_terraform_remote_state_eip.outputs.public_ip_addr}/32" ]
    from_port = 443
    to_port = 443
    protocol = "tcp"
  }
}