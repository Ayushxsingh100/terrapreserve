resource "aws_security_group" "web_secgroup" {
  description = "Application security group for tpl-24"
  name        = "web_secgroup-tpl-24"
  vpc_id      = aws_vpc.network.id

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_instance" "web_instance" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.web_tier.id
  vpc_security_group_ids = [aws_security_group.web_secgroup.id]
}

resource "aws_security_group" "data_secgroup_peer" {
  description = "Dependent client security group"
  name        = "data_secgroup-tpl-24-peer"
  vpc_id      = aws_vpc.network.id
}
