resource "aws_security_group" "data_secgroup-tpl-03" {
  ingress = [
    {
      cidr_blocks = ["0.0.0.0/0"]
      from_port = 22
      protocol = "tcp"
      to_port = 22
    }
  ]
}
