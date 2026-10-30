variable "project" {
    description = "project name"
    type = string
}

variable "environment" {
    description = "environment name"
    type = string
}

variable "vpc_id" {
    description = "ID of the VPC"
    type = string
}

#Allowing specific CIDR to SSH into bastion
variable "allowed_ssh_cidrs"{
    description = "CIDR block allowed to SSH into bastion"
    type = list(string)
}

#VPC CIDR to allow internal traffic within VPC
variable "vpc_cidr" {
    description = "VPC CIDR used for internal only SG rules (node-node, control plane-node and future pod-pod communication)"
    type = string
}

