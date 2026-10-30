resource "aws_instance" "zk1" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.medium"
  subnet_id     = aws_subnet.public-1a.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 100 # in GB
    volume_type = "gp3"
    encrypted   = true
  }
  associate_public_ip_address = true
  tags = {
    Name = "demo-zk1"
  }
}

resource "aws_instance" "zk2" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.medium"
  subnet_id     = aws_subnet.public-1b.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 100 # in GB
    volume_type = "gp3"
    encrypted   = true
  }

  associate_public_ip_address = true
  tags = {
    Name = "demo-zk2"
  }
}

resource "aws_instance" "zk3" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.medium"
  subnet_id     = aws_subnet.public-1c.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 100 # in GB
    volume_type = "gp3"
    encrypted   = true
  }

  associate_public_ip_address = true
  tags = {
    Name = "demo-zk3"
  }
}

resource "aws_instance" "kafka1" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.xlarge"
  subnet_id     = aws_subnet.public-1a.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 300 # in GB
    volume_type = "gp3"
    encrypted   = true
  }

  associate_public_ip_address = true
  tags = {
    Name = "demo-kafka1"
  }
}
resource "aws_instance" "kafka2" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.xlarge"
  subnet_id     = aws_subnet.public-1b.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 300 # in GB
    volume_type = "gp3"
    encrypted   = true
  }

  associate_public_ip_address = true
  tags = {
    Name = "demo-kafka2"
  }
}
resource "aws_instance" "kafka3" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.xlarge"
  subnet_id     = aws_subnet.public-1c.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 300 # in GB
    volume_type = "gp3"
    encrypted   = true
  }

  associate_public_ip_address = true
  tags = {
    Name = "demo-kafka3"
  }
}
resource "aws_instance" "connect1" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.xlarge"
  subnet_id     = aws_subnet.public-1a.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 300 # in GB
    volume_type = "gp3"
    encrypted   = true
  }

  associate_public_ip_address = true
  tags = {
    Name = "demo-connect1"
  }
}
resource "aws_instance" "connect2" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.xlarge"
  subnet_id     = aws_subnet.public-1b.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 300 # in GB
    volume_type = "gp3"
    encrypted   = true
  }

  associate_public_ip_address = true
  tags = {
    Name = "demo-connect2"
  }
}

resource "aws_instance" "sr1" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.large"
  subnet_id     = aws_subnet.public-1a.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 100 # in GB
    volume_type = "gp3"
    encrypted   = true
  }

  associate_public_ip_address = true
  tags = {
    Name = "demo-sr1"
  }
}
resource "aws_instance" "sr2" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.large"
  subnet_id     = aws_subnet.public-1b.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 300 # in GB
    volume_type = "gp3"
    encrypted   = true
  }

  associate_public_ip_address = true
  tags = {
    Name = "demo-sr2"
  }
}
resource "aws_instance" "ksql1" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.xlarge"
  subnet_id     = aws_subnet.public-1a.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 300 # in GB
    volume_type = "gp3"
    encrypted   = true
  }

  associate_public_ip_address = true
  tags = {
    Name = "demo-ksql1"
  }
}
resource "aws_instance" "ksql2" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.xlarge"
  subnet_id     = aws_subnet.public-1b.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 300 # in GB
    volume_type = "gp3"
    encrypted   = true
  }

  associate_public_ip_address = true
  tags = {
    Name = "demo-ksql2"
  }
}
resource "aws_instance" "c3" {
  ami           = "ami-0672fd5b9210aa093"
  instance_type = "t2.xlarge"
  subnet_id     = aws_subnet.public-1c.id
  key_name      = "shwu-keypair"
  vpc_security_group_ids = [
    aws_security_group.demo-vpc-security-group.id
  ]

  root_block_device {
    volume_size = 300 # in GB
    volume_type = "gp3"
    encrypted   = true
  }

  associate_public_ip_address = true
  tags = {
    Name = "demo-c3"
  }
}
output "zk_hosts" {
  value = [
    aws_instance.zk1.public_dns,
    aws_instance.zk2.public_dns,
    aws_instance.zk3.public_dns
  ]
}
output "kafka_hosts" {
  value = [
    aws_instance.kafka1.public_dns,
    aws_instance.kafka2.public_dns,
    aws_instance.kafka3.public_dns
  ]
}
output "connect_hosts" {
  value = [
    aws_instance.connect1.public_dns,
    aws_instance.connect2.public_dns
  ]
}
output "ksql_hosts" {
  value = [
    aws_instance.ksql1.public_dns,
    aws_instance.ksql2.public_dns
  ]
}
output "sr_hosts" {
  value = [
    aws_instance.sr1.public_dns,
    aws_instance.sr2.public_dns
  ]
}
output "c3_hosts" {
  value = [
    aws_instance.c3.public_dns
  ]
}
