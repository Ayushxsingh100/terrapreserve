resource "aws_security_group" "mysg" {
  name        = var.sg_name
  description = var.sg_description
  vpc_id      = var.sg_vpc_id

  ingress {
    description = "SSH From my ip"
    from_port   = "22"
    to_port     = "22"
    protocol    = "tcp"
    cidr_blocks = [var.ip]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = var.sg_name
  }

}

output "sg_id" {
  value = aws_security_group.mysg.id
}
