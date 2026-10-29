# variable block for keyname

variable "KeyNameEC2" {
  description = "Enter the keyname for EC2 instance"
  type        = string
}

variable "InstanstanceType" {
    description = "select if t2.micro or t2.nano"
    type = string
    
  
}
variable "region" {
  description = "region to deploy the infrastructure"
  
}
variable "vpc_id" {
  description = "VPC ID of FridayHITT"
  
}

variable "ami_id" {
  description = "ami ID for the EC2 instances"
  
}
#Variable definition for subnets
variable "public_subnet" {
  description = "Public subnet ID"
  
}
variable "private_subet" {
  description = "private subet ID"
  
}



