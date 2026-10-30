data "aws_vpc" "vpc_default" {
    default = true
}
resource "aws_security_group" "allow_ports" {
  name        = "exemplo-sg"
  description = "SG de Exemplo via Terraform"
  vpc_id      = data.aws_vpc.vpc_default.id
  ingress {
    from_port        = 8200
    to_port          = 8200
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }
  egress {
    from_port        = 8200
    to_port          = 8200
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }
  tags = {
    Name = "exemplo-sg"
  }
}