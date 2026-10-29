# VPC creation 

resource "aws_vpc" "demoVPC" {
  cidr_block       = var.vpc_cidr
  instance_tenancy = var.vpc_tenancy
  enable_dns_hostnames = true

  tags = {
    Name     = "demoVPC"
    Location = "us-east-2"
  }
}

# Public Subnet 

resource "aws_subnet" "publicSN" {
  vpc_id            = aws_vpc.demoVPC.id
  cidr_block        = var.public_sn_cidr
  availability_zone = "us-east-2a"

  tags = {
    Name = "Public Subnet"
  }
}

# Private Subnet

resource "aws_subnet" "privateSN" {
  vpc_id            = aws_vpc.demoVPC.id
  cidr_block        = var.private_sn_cidr
  availability_zone = "us-east-2b"

  tags = {
    Name = "Private Subnet"
  }
}

# Public Route Table

resource "aws_route_table" "publicRT" {
    vpc_id = aws_vpc.demoVPC.id

    route {
    	cidr_block = "0.0.0.0/0"
    	gateway_id = aws_internet_gateway.igw.id
  }

    tags = {
    	Name = "Public Route Table"
  }
}

# Associate Public route table to public subnet

resource "aws_route_table_association" "publicRTA" {
    subnet_id      = aws_subnet.publicSN.id
    route_table_id = aws_route_table.publicRT.id
}

/*
# Private Route Table

resource "aws_route_table" "privateRT" {
    vpc_id = aws_vpc.demoVPC.id

    route {
    	cidr_block = "0.0.0.0/0"
    	nat_gateway_id = aws_nat_gateway.natGW.id
  }

    tags = {
    	Name = "Private Route Table"
  }
}


# Associate Private table to public subnet

resource "aws_route_table_association" "privateRTA" {
    subnet_id      = aws_subnet.privateSN.id
    route_table_id = aws_route_table.privateRT.id
}

*/

# Internet Gateway

resource "aws_internet_gateway" "igw" {
    vpc_id = aws_vpc.demoVPC.id

    tags = {
        Name = "Internet Gateway"
  }
}

# Public Security Group

resource "aws_security_group" "webSG" {
    name        = "public"
    description = "Allow SSH, HTTP traffic"

    ingress {
    	from_port   = 80
    	to_port     = 80
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
  }

    ingress {
    	from_port   = 443
    	to_port     = 443
    	protocol    = "tcp"
    	cidr_blocks = ["0.0.0.0/0"]
  }

    ingress {
    	from_port   = -1
    	to_port     = -1
    	protocol    = "icmp"
    	cidr_blocks = ["0.0.0.0/0"]
  }

    ingress {
    	from_port   = 22
    	to_port     = 22
    	protocol    = "tcp"
    	cidr_blocks = ["0.0.0.0/0"]
  }

  vpc_id = aws_vpc.demoVPC.id

  tags = {
    Name = "webSG"
  }
}

# Private Security Group

resource "aws_security_group" "dbSG" {
    name        = "sg_test_web"
    description = "Allow DB, SSH, ICMP traffic from public subnet in defined VPC"

    ingress {
        from_port   = 3306
        to_port     = 3306
        protocol    = "tcp"
        cidr_blocks = [var.public_sn_cidr]
  }

    ingress {
    	from_port   = -1
	to_port     = -1
	protocol    = "icmp"
    	cidr_blocks = [var.public_sn_cidr]
  } 

    ingress {
    	from_port   = 22
    	to_port     = 22
    	protocol    = "tcp"
    	cidr_blocks = [var.public_sn_cidr]
  }

  vpc_id = aws_vpc.demoVPC.id

    tags = {
        Name = "dbSG"
    }
}


/*
resource "aws_nat_gateway" "natGW" {
    allocation_id = aws_eip.nat.id
    subnet_id     = aws_subnet.publicSN.id
   
    tags = {
        Name = "NAT Gateway"
    }
}


resource "aws_eip" "elasticIP" {
    instance = aws_n
    vpc      = true
}
*/
