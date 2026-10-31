// Create security groups that allow all ports needed for Nomad
resource "aws_security_group" "allow_nomad_traffic_sg" {
  name        = "allow_nomad_traffic_sg"
  description = "Allow traffic needed for Nomad"
  vpc_id      = var.aws_vpc_id

  // nomad
  ingress {
    from_port   = "4646"
    to_port     = "4648"
    protocol    = "tcp"
    cidr_blocks = ["${var.nomad_cidr}"]
  }

  ingress {
    from_port   = "4648"
    to_port     = "4648"
    protocol    = "udp"
    cidr_blocks = ["${var.nomad_cidr}"]
  }

  // all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "allow_nomad_traffic"
  }
}

resource "aws_security_group" "allow_nomad_icmp_traffic" {
  name        = "allow_nomad_icmp_traffic_sg"
  description = "Allow traffic needed for Nomad"
  vpc_id      = var.aws_vpc_id

  // Custom ICMP Rule - IPv4 Echo Reply
  ingress {
    from_port   = "0"
    to_port     = "-1"
    protocol    = "icmp"
    cidr_blocks = ["${var.icmp_cidr}"]
  }

  // Custom ICMP Rule - IPv4 Echo Request
  ingress {
    from_port   = "8"
    to_port     = "-1"
    protocol    = "icmp"
    cidr_blocks = ["${var.icmp_cidr}"]
  }

  // all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "allow_nomad_icmp_traffic"
  }
}

resource "aws_security_group" "allow_nomad_ssh_traffic" {
  name        = "allow_nomad_ssh_traffic_sg"
  description = "Allow traffic needed for Nomad"
  vpc_id      = var.aws_vpc_id

  // ssh
  ingress {
    from_port   = "${var.ssh_port}"
    to_port     = "${var.ssh_port}"
    protocol    = "tcp"
    cidr_blocks = ["${var.ssh_cidr}"]
  }

  // all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "allow_nomad_ssh_traffic"
  }
}
