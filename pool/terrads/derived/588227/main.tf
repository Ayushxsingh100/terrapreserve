#Provider

provider "aws" {
  region = "us-east-1"
}


#VPC

resource "aws_vpc" "my_vpc" {
  cidr_block           = "10.0.0.0/16" #cidr block for VPC
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "my-vpc"
  }
}


#Public Subnet 1

resource "aws_subnet" "public_subnet_1" {
  vpc_id                  = aws_vpc.my_vpc.id # Associate with the created VPC
  cidr_block              = "10.0.1.0/24"     # cidr block for public subnet
  map_public_ip_on_launch = true              # Assign public IPs to instances
  availability_zone       = "us-east-1a"

  tags = {
    Name = "Public Subnet 1"
  }
}

#Public Subnet 2

resource "aws_subnet" "public_subnet_2" {
  vpc_id                  = aws_vpc.my_vpc.id
  cidr_block              = "10.0.3.0/24"
  availability_zone       = "us-east-1b"
  map_public_ip_on_launch = true

  tags = {
    Name = "Public Subnet 2"
  }
}

#Private Subnet

resource "aws_subnet" "private_subnet" {
  vpc_id            = aws_vpc.my_vpc.id # Associate with the created VPC
  cidr_block        = "10.0.2.0/24"     # CIDR block for private subnet
  availability_zone = "us-east-1b"      # Specify the availability zone

  tags = {
    Name = "private-subnet"
  }
}


#Internet Gateway

resource "aws_internet_gateway" "my_igw" {
  vpc_id = aws_vpc.my_vpc.id # Associate with the created VPC
  tags = {
    Name = "my-igw"
  }
}


#Route Table for Public Subnet

resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.my_vpc.id # Associate with the created VPC
  route {
    cidr_block = "0.0.0.0/0"                    # Allow all outbout traffic
    gateway_id = aws_internet_gateway.my_igw.id # Directs traffic through the IGW
  }

  tags = {
    Name = "public-route-table"
  }

}


#Route table association

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public_subnet_1.id         # Associate the public subnet
  route_table_id = aws_route_table.public_route_table.id # Associate with the route table
}


#Security Group for Web Server
resource "aws_security_group" "web_sg" {
  vpc_id = aws_vpc.my_vpc.id

  ingress {
    from_port   = 80 # Allow HTTP traffic
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allow traffic from anywhere
  }
  ingress {
    from_port   = 22 # Allow SSH traffic
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["103.54.105.98/32"] # Restrict to your public IP
  }
  egress {
    from_port   = 0 # Allow all outbound traffic
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "web-sg"
  }
}


#Launch EC2 Instance (Web Tier)

resource "aws_instance" "web_server" {
  ami                    = "ami-0e54eba7c51c234f6" # Specify the AMI to use (Amazon Linux 2)
  instance_type          = "t2.micro"
  subnet_id              = aws_subnet.public_subnet_1.id  # Launch in the public subnet
  vpc_security_group_ids = [aws_security_group.web_sg.id] # Associate the security group
  tags = {
    Name = "web-server"
  }
}


#Security Group for Database

resource "aws_security_group" "db_sg" {
  vpc_id = aws_vpc.my_vpc.id # Associate with the created VPC
  ingress {
    from_port   = 3306 # Allow MySQL traffic
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [aws_subnet.private_subnet.cidr_block] # Allow traffic only from the private subnet
  }
  egress {
    from_port   = 0 # Allow all outbound traffic
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "db-sg"
  }
}


#RDS Instance Creation

resource "aws_db_instance" "my_db" {
  allocated_storage      = 20                                          # Specify the storage size
  storage_type           = "gp3"                                       # Specify the storage type
  engine                 = "mysql"                                     # Specify the database engine
  engine_version         = "8.0.35"                                    # Specify the engine version
  instance_class         = "db.t3.micro"                               # Specify the instance type
  username               = "admin"                                     # Database username
  password               = var.db_password                                  # Database password
  db_subnet_group_name   = aws_db_subnet_group.my_db_subnet_group.name # Associate the DB subnet group
  vpc_security_group_ids = [aws_security_group.db_sg.id]               # Associate the security group
  tags = {
    Name = "my-db"
  }
}


resource "aws_db_subnet_group" "my_db_subnet_group" {
  name       = "my-db-subnet-group"
  subnet_ids = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]

  tags = {
    Name = "my-db-subnet-group"
  }
}
