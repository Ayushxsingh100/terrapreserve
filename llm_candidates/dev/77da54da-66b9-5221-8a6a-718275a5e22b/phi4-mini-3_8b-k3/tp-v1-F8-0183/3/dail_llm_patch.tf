resource "aws_security_group" "sg_app-tpl-02" {
  delete {
    ingress = [
      {
        from_port = 22,
        protocol = "tcp",
        cidr_blocks = ["0.0.0.0/0"],
      }
    ]
  }
}
