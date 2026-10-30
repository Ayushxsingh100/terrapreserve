locals {

  public_subnet_count = [

    for key, details in var.subnet_config : key if details.public == true
  ]
}

# using the data source in order to fetch the availability zones using `aws_availability_zones` data source
data "aws_availability_zones" "available" {

  # define the state as available
  state = "available"
}


# define the child module vpc in order to provision the AWS VPC through this module
resource "aws_vpc" "this" {

  cidr_block = var.vpc_config.cidr_block

  tags = {

    Name = var.vpc_config.name
    # define the name of the vpc as vpc_config in this case

  }


}

resource "aws_subnet" "this" {

  for_each = var.subnet_config
  # define the  for_each loop for the subnet_config object in this case

  vpc_id = aws_vpc.this.id
  # referencing  to vpc id configuration in this case as vpc_id

  cidr_block = each.value.cidr_block
  # define the cidr-block with respect to the subnet_config object that we have defined

  # (Optional) AZ for the subnet
  availability_zone = each.value.azs

  tags = {

    Name = each.key
    # define the name of the vpc as vpc_config in this case


  }

  # define the pre-condition block where we have defined the aws_availability_zones data source and we are checing the az provided reside inside it or not
  lifecycle {

    precondition {

      condition = contains(data.aws_availability_zones.available.names, each.value.azs)
      # define the condition as contains(aws_availability_zones.available.names, each.value.az) in this case
      # which will check whether the az provided in the subnet_config object is present in the aws_availability_zones.available.names or not

      error_message = <<-EOT
            The Provided AZ ${each.value.azs} inside Subnet ${each.key} is incorrect
            Inside the Region ${data.aws_availability_zones.available.id} below are the available AZ
            The available AZ in the region are:= [${join(",", data.aws_availability_zones.available.names)}]
            EOT
      # define the error message when the condition get failed in this case
    }
  }

}


resource "aws_internet_gateway" "this" {

  count = length(local.public_subnet_count) > 0 ? 1 : 0
  # here we will be decide based on the count of the public subnet if the public subnet is greater than 1 then create the igw else ignore it
  # if the length(local.public_subnet_count) > 1 as well then also we will be getting only 1 igw
  # for the map of object also we can count the length as well

  vpc_id = aws_vpc.this.id
  # define the vpc_id as aws_vpc.this.id in this case

  # define the tags for the igw
  tags = {
    Name = "${var.vpc_config.name}-igw"
  }


}


# here we want to create the aws_route_table terraform resource for the public route table
resource "aws_route_table" "this" {

  for_each = { for key, value in var.subnet_config : key => value if value.public == true }
  # using the for_each loop in order to iterate over those subnet where the pubic as true being mentioned

  vpc_id = aws_vpc.this.id
  # referencing to the vpc id in here

  # define the route inside the route block of the aws_route_table resource
  route {

    cidr_block = "0.0.0.0/0"
    # providing the destination cidr_block for the ingress

    gateway_id = aws_internet_gateway.this[0].id
    # as here we are using the count hence using the index in order to access the igw
    # associating the route with the internet Gateway in this case

  }


}

# then we will associate the aws_route_table with the aws_subnet using the aws_route_table_association resource
resource "aws_route_table_association" "this" {

  for_each = { for key, value in var.subnet_config : key => value if value.public == true }
  # using the for_each loop in order to iterate over those subnet where the pubic as true being mentioned

  subnet_id = aws_subnet.this[each.key].id
  # associating the route with the subnet in this case

  route_table_id = aws_route_table.this[each.key].id
  # associating the route with the aws_route_table in this case

}