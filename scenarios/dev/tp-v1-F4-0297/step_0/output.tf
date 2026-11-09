output "vpc-id" {
    value = aws_vpc.main.id
  
}

locals {
  #to format the subnet ids which may be multiples in format of subnet_name = {id=, az=}
public_subnet_output = {
    for key , config in local.public_subnet : key => {
        subnet_id = aws_subnet.main[key]. id
        az = aws_subnet.main[key]. availability_zone
    }
}

private_subnet_output = {
    for key , config in local.private_subnet : key => {
        subnet_id = aws_subnet.main[key]. id
        az = aws_subnet.main[key]. availability_zone
    }
}

}
output "public-subnet-ids" {

  value = local.public_subnet_output
}
output "private-subnet-ids" {

  value = local.private_subnet_output
}
