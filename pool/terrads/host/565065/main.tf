resource "aws_security_group" "ssh_group" {
  name        = "${var.env}-${var.name}-sg - Allow SSH And All Outbound"
  description = "Security group allowing SSH inbound and all outbound traffic"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "server" {
  ami           = var.ami
  instance_type = var.instance_type
  subnet_id     = var.subnet_id
  vpc_security_group_ids = [ aws_security_group.ssh_group.id ]

  tags = {
    Name       = "${var.env}-${var.name}"
    Owner      = var.owner
    Enviroment = var.env
    CostCenter = var.cost_center
  }
}


