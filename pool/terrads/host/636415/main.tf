# Configure the AWS Provider
provider "aws" {
  region  = "us-east-1"

}

# Configure the VPC 
resource "aws_vpc" "test" {
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "test"
  }
}

# Configure the subnet
resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.test.id
  cidr_block = "10.0.1.0/24"
  
  # Fixed: map_public_ip_on_launch should be outside tags
  map_public_ip_on_launch = true
  
  tags = {
    Name = "public-subnet"
  }
}

# Configure the internet gateway
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.test.id
  tags = {
    Name = "main-gw"
  }
}

# Configure the route table 
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.test.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "public-rt"
  }
}

# Configure route table association
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Configure EC2 instance
resource "aws_instance" "terraform" {
  ami           = "ami-09e6f87a47903347c"  
  instance_type = "t2.micro"
  subnet_id     = aws_subnet.public.id  # Added subnet association

  tags = {
    Name = "HelloWorld"
  }
}
