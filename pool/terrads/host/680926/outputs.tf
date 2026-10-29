locals{
    output_public_subnets = {
        for key in keys(local.public_subnets) : key => {
            subnet_id = aws_subnet.name[key].id
            availability_zone = aws_subnet.name[key].availability_zone
        }
    }

    output_private_subnets = {
        for key in keys(local.private_subnets) : key => {
            subnet_id = aws_subnet.name[key].id
            availability_zone = aws_subnet.name[key].availability_zone
        }
    }
}

output "vpc_id" {
    description = "The AWS created VPC ID"
    value = aws_vpc.vpc.id
}


output "public_subnets" {
    description = "The ID and Availability Zone Of Public Subnets"
    value = local.output_public_subnets
}

output "private_subnets" {
    description = "The ID and Availability Zone Of Private Subnets"
    value = local.output_private_subnets
}