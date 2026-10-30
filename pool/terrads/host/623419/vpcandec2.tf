provider "aws" {
  region = "ap-south-1"
}

# CREATE VPC
resource "aws_vpc" "project-vpc" {
    cidr_block = "10.0.0.0/16"
    tags = {
        Name = "ProjectVPC"
    }
}

# CREATE 2 SUBNETS
resource "aws_subnet" "project-public_subent_01" {
    vpc_id = aws_vpc.project-vpc.id
    cidr_block = "10.1.1.0/24"
    map_public_ip_on_launch = "true"
    availability_zone = "ap-south-1a"
    tags = {
      Name = "project-public_subent_01"
    }
}

resource "aws_subnet" "project-public_subent_02" {
    vpc_id = aws_vpc.project-vpc.id
    cidr_block = "10.0.2.0/24"
    map_public_ip_on_launch = "true"
    availability_zone = "ap-south-1b"
    tags = {
      Name = "project-public_subent_02"
    }
}


# CREATE INTERNET GATEWAY AND ASSOCIATE TO VPC
resource "aws_internet_gateway" "project-igw" {
    vpc_id = aws_vpc.project-vpc.id
    tags = {
      Name = "Project-IGW"
    }
}

// CREATE A ROUTE TABLE
resource "aws_route_table" "project-public-rt" {
    vpc_id = aws_vpc.project-vpc.id
    route {
        cidr_block = "0.0.0.0/0"
        gateway_id = aws_internet_gateway.project-igw.id
    }
    tags = {
      Name = "Project-RT"
    }
}

# ASSOCIATE ROUTE TABLE TO MY SUBNET

resource "aws_route_table_association" "project-subnet-1" {
    subnet_id = aws_subnet.project-public_subent_01.id
    route_table_id = aws_route_table.project-public-rt.id
}

resource "aws_route_table_association" "project-subent-2" {
    subnet_id = aws_subnet.project-public_subent_02.id
    route_table_id = aws_route_table.project-public-rt.id
}


# CREATE SECURITY GROUP
resource "aws_security_group" "project-sg" {
  name = "project-sg"
  description = "Providing SSH Access"


  ingress {
    description = "SSH Access"
    from_port = 22
    to_port = 22
    protocol = "SSH"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "SSH Access"
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
}



# CREATING EC2
resource "aws_instance" "demo-server" {
    ami = "ami-0e35ddab05955cf57"
    instance_type = "t2.medium"
    key_name = "kubernetes"
    subnet_id = aws_subnet.project-public_subent_01.id
    for_each = toset(["Ansible", "Jenkins", "Docker"])
    tags = {
        Name = "${each.key}"
    }
    # security_groups = [ "project-sg" ]
    vpc_security_group_ids = [aws_security_group.project-sg.id]
}
