variable "create" {
  description = "Whether to create node security groups"
  type        = bool
  default     = false
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for security group names"
  type        = string
  default     = "eks-nodes"
}

variable "tags" {
  description = "Tags to apply"
  type        = map(string)
  default     = {}
}
