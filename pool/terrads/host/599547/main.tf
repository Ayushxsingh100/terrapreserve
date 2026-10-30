resource "aws_security_group" "allow_ssh_http" {
  name        = "allow_ssh_http"
  description = "Allow SSH and HTTP inbound traffic"
  vpc_id      = var.vpc_id

  # Ingress rule (port 22)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allow SSH from anywhere
  }

  # Ingress rule (port 80)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allow HTTP from anywhere
  }

  # Egress rule outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"          # All protocols
    cidr_blocks = ["0.0.0.0/0"] # Allow all outbound
  }
}

resource "aws_instance" "test" {
  ami                    = var.ami_value
  instance_type          = var.instance_type_value
  subnet_id              = var.subnet_id_value
  key_name               = "igs--1"
  vpc_security_group_ids = [aws_security_group.allow_ssh_http.id]
}