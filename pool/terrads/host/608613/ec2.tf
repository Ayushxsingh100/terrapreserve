provider "aws" {
  region = "us-west-2"
}

resource "aws_security_group" "ssh_traffic" {
  name        = "ssh_traffic"
  description = "Allow SSH inbound traffic"
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    git_commit           = "f6e52ab51890c520d5451262a89549f1f41702c4"
    git_file             = "terraform/simple_instance/ec2.tf"
    git_last_modified_at = "2021-11-17 11:08:25"
    git_last_modified_by = "62098145+GuyNoy@users.noreply.github.com"
    git_modifiers        = "62098145+GuyNoy"
    git_org              = "GuyNoy"
    git_repo             = "terragoat"
    yor_trace            = "0edfdae8-fc8a-4121-8384-75e8d2425675"
  }
}

resource "aws_instance" "web_server_instance" {
  ami             = data.aws_ami.ubuntu.id
  instance_type   = "t2.micro"
  security_groups = ["${aws_security_group.ssh_traffic.name}"]
  tags = {
    Name                 = "bc_workshop_ec2"
    git_commit           = "f6e52ab51890c520d5451262a89549f1f41702c4"
    git_file             = "terraform/simple_instance/ec2.tf"
    git_last_modified_at = "2021-11-17 11:08:25"
    git_last_modified_by = "62098145+GuyNoy@users.noreply.github.com"
    git_modifiers        = "62098145+GuyNoy"
    git_org              = "GuyNoy"
    git_repo             = "terragoat"
    yor_trace            = "90a87a35-1a47-4870-9fe8-311ab27a4ea3"
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}
