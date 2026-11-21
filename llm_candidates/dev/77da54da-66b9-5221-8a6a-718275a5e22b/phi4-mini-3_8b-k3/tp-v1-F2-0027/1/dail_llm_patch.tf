resource "aws_security_group" "web_secgroup-tpl-03" {
  ingress = [{
    from_port = 22,
    protocol = "tcp",
    to_port = 22,
    cidr_blocks = ["0.0.0.0/0"]
  }]
}
