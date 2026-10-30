resource "aws_instance" "moscow-time-server" {
  ami             = var.ami_id
  instance_type   = "t2.micro"
  key_name        = var.keypair_name
  security_groups = [aws_security_group.allow-web-ssh.name]

  tags = {
    Name = "Moscow Time Server"
    ControlledBy = "ansible"
  }
}
