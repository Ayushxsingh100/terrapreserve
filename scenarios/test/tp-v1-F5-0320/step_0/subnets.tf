resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.krasteki-vpc.id
  cidr_block              = var.public_subnet_1
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = true ## (Optional) Specify true to indicate that instances launched into the subnet should be assigned a public IP address. Default is false ##
  tags = {
    Name = "${var.tag}-public_subnet_1"
  }
}

resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.krasteki-vpc.id
  cidr_block              = var.public_subnet_2
  availability_zone       = "${var.region}b"
  map_public_ip_on_launch = true ## (Optional) Specify true to indicate that instances launched into the subnet should be assigned a public IP address. Default is false ##
  tags = {
    Name = "${var.tag}-public_subnet_2"
  }
}

resource "aws_subnet" "public_3" {
  vpc_id                  = aws_vpc.krasteki-vpc.id
  cidr_block              = var.public_subnet_3
  availability_zone       = "${var.region}c"
  map_public_ip_on_launch = true ## (Optional) Specify true to indicate that instances launched into the subnet should be assigned a public IP address. Default is false ##
  tags = {
    Name = "${var.tag}-public_subnet_3"
  }
}

resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.krasteki-vpc.id
  cidr_block        = var.private_subnet_1
  availability_zone = "${var.region}a"
  tags = {
    Name = "${var.tag}-private_subnet_1"
  }
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.krasteki-vpc.id
  cidr_block        = var.private_subnet_2
  availability_zone = "${var.region}b"
  tags = {
    Name = "${var.tag}-private_subnet_2"
  }
}

resource "aws_subnet" "private_3" {
  vpc_id            = aws_vpc.krasteki-vpc.id
  cidr_block        = var.private_subnet_3
  availability_zone = "${var.region}c"
  tags = {
    Name = "${var.tag}-private_subnet_3"
  }
}