output "vpc_id" {
  value = aws_vpc.main.id
}

locals {
    # subnet_name = {id = , az= }
  public_subnet_output = {
    for key,config in local.public_subnet : key => {
    subnet_id = aws_subnet.subnet[key].id
    availability_zone = aws_subnet.subnet[key].availability_zone
    }
  }

  private_subnet_output = {
    for key,config in local.private_subnet : key => {
        subnet_id = aws_subnet.subnet[key].id
        availability_zone = aws_subnet.subnet[key].availability_zone
    }
  }
}

output "public_subnet_id" {
  value = local.public_subnet_output
}

output "private_subnet_id" {
  value = local.private_subnet_output
}