resource "aws_vpc" "novavpc" {
    cidr_block = var.vpd_cidr
    tags = {
      "Name" = "Nova-App-VPC"
    }  
}
