variable "vpc_id" {
  description = "VPC ID to create the security group in"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH to instances"
  type        = list(string)
  default     = ["154.160.23.253/32"]
}

variable "tags" {
  description = "Tags to apply to the security group"
  type        = map(string)
  default     = {}
}