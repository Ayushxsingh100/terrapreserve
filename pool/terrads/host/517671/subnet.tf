resource "aws_subnet" "novasubnet" {
    vpc_id = aws_vpc.novavpc.id
    cidr_block = var.subnet_cidr_ranges[count.index]
    availability_zone = "us-east-1a"
    count = length(var.subnet_cidr_ranges) 
    lifecycle{
       prevent_destroy = true
    } 
}