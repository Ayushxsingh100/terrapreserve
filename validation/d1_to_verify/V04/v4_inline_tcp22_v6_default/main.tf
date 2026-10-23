resource "aws_security_group" "g" {
  name = "g"

  ingress {
    protocol         = "tcp"
    from_port        = 22
    to_port          = 22
    ipv6_cidr_blocks = ["::/0"]
  }

}
