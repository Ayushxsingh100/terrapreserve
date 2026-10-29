resource "aws_instance" "this" {
  ami                     = "ami-0c614dee691cbbf37"
  vpc_security_group_ids = [aws_security_group.allow_tls.id ]
  instance_type           = "t2.micro"

  tags = {
    Name = "TERRAFORM-DEMO"
  }
}

resource "aws_security_group" "allow_tls" {
  name = "allow_tls"
  description = "allow TLS inbound traffic and all outbound traffic"
  
    ingress {
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

 egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }


  tags = {
    Name = "allow_tls"
  }
}