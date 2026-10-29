variable "vpc_id" {
  description = "VPC의 ID"
  type        = string
}

variable "region_name" {
  description = "Region 이름"
  type        = string
}

variable "security_group" {
  description = "보안그룹들"
  type        = map(object(
    {
      ingress_rules = map(object(
        {
          protocol = string
          from_port = number
          to_port = number
          cidr_blocks = list(string)
        }
      ))
      egress_rules = map(object(
        {
          protocol = string
          from_port = number
          to_port = number
          cidr_blocks = list(string)  
        }
      ))
    }
  ))
}
