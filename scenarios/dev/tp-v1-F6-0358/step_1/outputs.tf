output "vpc_id" {
  description = "the id of the vpc created by this module"
  value       = aws_vpc.test-vpc.id
}

locals {
  public_subnet_output = {
    for key, config in local.public_subnet_count : key => { # we are using the local which we created in main.tf to get the public subnets only and then we are using that to create a map with key as the subnet name and valueas a object with id and az of that subnet and we are accessing the id and az from the aws_subnet resource from the key of the local.public_subnet_count
      id  = aws_subnet.test-subnet[key].id                  # we are using the local which we created in main.tf to get the public subnets only and then we are using that to get the id of the subnet from the aws_subnet resource 
      azs = aws_subnet.test-subnet[key].availability_zone
    }
  }
}

output "public_subnets" {
  value = local.public_subnet_output
}


