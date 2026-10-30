# the dynamic blck is basically used for to avoid repation things like port opening ingrees again and agin 

resource "aws_instance" "MyDynamic" {
  ami = var.ami
  instance_type = var.instance_type
  vpc_security_group_ids = [aws_security_group.MySG.id]
  key_name = "demokey"

  tags = {
    Name = "MyDynamic"
  }
}

locals {
  ingrees_rule = [{
    port = 80
    description = "HTTP"
  },
  {
    port = 443
    description = "HTTPS"
  },
  {
    port = 22
    description = "SSH"
  }]
}


resource "aws_security_group" "MySG" {
  description = "Allow TLS inbound traffic"

  dynamic "ingress" {
    for_each = local.ingrees_rule
    content {
      description = ingress.value.description
      from_port = ingress.value.port
      to_port = ingress.value.port
      protocol = "tcp"
      cidr_blocks = ["0.0.0.0/0"]

    }
  }
  egress  {
    description = "for outbound"
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  } 
}