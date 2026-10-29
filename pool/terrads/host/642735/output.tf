#VPC 
output "vpc-id" {
    value = aws_vpc.main.id
}


locals {
  public_subnet_output= {
    for key, config in local.public_subnet : key => {
        public_subnet = aws_subnet.main[key].id
        az = aws_subnet.main[key].availability_zone
    }
  }

  private_subnet_output= {
    for key, config in local.private_subnet : key => {
        private_subnet = aws_subnet.main[key].id
        az            = aws_subnet.main[key].availability_zone
    }
  }
}



# Subnet
output "public_subnet" {
    value = local.public_subnet_output
}


output "private_subnet" {
    value = local.private_subnet_output
  
}