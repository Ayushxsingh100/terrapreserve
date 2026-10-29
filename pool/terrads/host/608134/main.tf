#------------------------------------------------------------
#  My Terraform
#
#  Made by Alex
#------------------------------------------------------------

provider "aws" {

}

resource "aws_security_group" "my_webserver" {
  name = "My Security Group"


  dynamic "ingress" {
    for_each = ["80", "443", "8080", "1541"]
    content {
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]

    }

  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.10.0.0/16"]

  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "Dynamic Security terraform"
  }
}

resource "aws_instance" "my_server_web" {
  ami                    = "ami-099da3ad959447ffa" #  Amazon_Linux2023
  instance_type          = "t3.micro"
  vpc_security_group_ids = [aws_security_group.my_webserver.id]

  tags = {
    Name  = "Server_Web"
    Owner = "Alex DevOps"
  }
  depends_on = [aws_instance.my_server_db]
}

resource "aws_instance" "my_server_app" {
  ami                    = "ami-099da3ad959447ffa" #  Amazon_Linux2023
  instance_type          = "t3.micro"
  vpc_security_group_ids = [aws_security_group.my_webserver.id]

  tags = {
    Name  = "Server_Application"
    Owner = "Alex DevOps"
  }
  depends_on = [aws_instance.my_server_db]
}

resource "aws_instance" "my_server_db" {
  ami                    = "ami-099da3ad959447ffa" #  Amazon_Linux2023
  instance_type          = "t3.micro"
  vpc_security_group_ids = [aws_security_group.my_webserver.id]

  tags = {
    Name  = "Server_Database"
    Owner = "Alex DevOps"
  }
}


