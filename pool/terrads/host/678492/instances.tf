data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

data "aws_ami" "windows" {
  most_recent = true
  owners      = ["801119661308"] # Amazon

  filter {
    name   = "name"
    values = ["Windows_Server-2022-English-Full-Base-*"]
  }
}

resource "aws_instance" "wazuh_manager" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "m7i-flex.large"
  subnet_id              = aws_subnet.soc_subnet.id
  vpc_security_group_ids = [aws_security_group.wazuh_sg.id]
  key_name               = "soc-key"

  root_block_device {
    volume_size = 150
    volume_type = "gp3"
  }

  tags = {
    Name = "Wazuh-Manager"
  }
}

resource "aws_instance" "shuffle_soar" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "m7i-flex.large"
  subnet_id              = aws_subnet.soc_subnet.id
  vpc_security_group_ids = [aws_security_group.shuffle_sg.id]
  key_name               = "soc-key"

  root_block_device {
    volume_size = 150
    volume_type = "gp3"
  }

  tags = {
    Name = "Shuffle-SOAR"
  }
}

resource "aws_instance" "linux_web" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "m7i-flex.large"
  subnet_id              = aws_subnet.soc_subnet.id
  vpc_security_group_ids = [aws_security_group.client_sg.id]
  key_name               = "soc-key"

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
  }

  tags = {
    Name = "Linux-Web-Client"
  }
}

resource "aws_instance" "linux_ftp" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "m7i-flex.large"
  subnet_id              = aws_subnet.soc_subnet.id
  vpc_security_group_ids = [aws_security_group.client_sg.id]
  key_name               = "soc-key"

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
  }

  tags = {
    Name = "Linux-FTP-Client"
  }
}

resource "aws_instance" "windows_web" {
  ami                    = data.aws_ami.windows.id
  instance_type          = "m7i-flex.large"
  subnet_id              = aws_subnet.soc_subnet.id
  vpc_security_group_ids = [aws_security_group.client_sg.id]
  key_name               = "soc-key"

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
  }

  tags = {
    Name = "Windows-Web-Client"
  }
}

output "wazuh_ip" {
  value = aws_instance.wazuh_manager.public_ip
}

output "shuffle_ip" {
  value = aws_instance.shuffle_soar.public_ip
}

output "linux_web_ip" {
  value = aws_instance.linux_web.public_ip
}

output "linux_ftp_ip" {
  value = aws_instance.linux_ftp.public_ip
}

output "windows_web_ip" {
  value = aws_instance.windows_web.public_ip
}
