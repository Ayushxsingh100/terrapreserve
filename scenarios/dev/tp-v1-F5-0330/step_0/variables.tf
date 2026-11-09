variable "cidr_block" {
  type        = string
  description = "VPC CIDR block"
}
variable "region" {
  type        = string
  description = "AWS region to deploy the resources."
}
variable "vpc_name" {
  type        = string
  description = "VPC Name"
}
variable "enable_dns_support" {
  type        = bool
  default     = false
  description = "A boolean flag to enable/disable DNS support in the VPC."
}
variable "enable_dns_hostnames" {
  type        = bool
  default     = false
  description = "A boolean flag to enable/disable DNS hostnames in the VPC"
}
variable "tags" {
  type        = map(string)
  description = "VPC Tags"
}
variable "subnets" {
  type = list(object({
    name     = string
    new_bits = number
    az       = string
  }))
  description = "Subnet information necessary to create all the subnets. Please check [cidrsubnets](https://www.terraform.io/language/functions/cidrsubnets) for more info on `new_bits`. The `region` variable is used to associate the desired AZ. Usage : `join(\"\",[\"us-east-1\", \"a\"])`. Example: [values.hcl](https://github.com/SP-UT/vpc/blob/main/values.hcl#L15)"
}
