variable "aws_region" {
    description = "VPC region"
    default = "us-east-2"
}

variable "vpc_cidr" {
    description = "VPC CIDR notation"
    default = "10.0.0.0/16"
}

variable "vpc_tenancy" {
    default = "default"
}

variable "public_sn_cidr" {
    description = "Public Subnet CIDR"
    default = "10.0.1.0/24"
}

variable "private_sn_cidr" {
    description = "Private Subnet CIDR"
    default = "10.0.2.0/24"
}

variable "ami_id" {
    description = "AMI ID for the instance"
    default = "ami-0e01ce4ee18447327" 
}

variable "instance_type" {
    default = "t2.micro"
}

/*
variable "key_path" {
    description = "SSH Pub key"
    default = "~/.ssh/id_rsa.pub"
}
*/
