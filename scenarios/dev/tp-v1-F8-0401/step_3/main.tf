resource "aws_instance" "my_instance" {
  ami                         = "ami-0fc5d935ebf8bc3bc"
  instance_type               = "t2.micro"
  key_name                    = "lab-key"
  vpc_security_group_ids      = [aws_security_group.allow_ssh.id]
  subnet_id                   = aws_subnet.public.id
  associate_public_ip_address = true
  tags = {
    Name = "ec2-instance-1"
  }
}

output "instance_public_ip" {
  value = aws_instance.my_instance.public_ip
}
