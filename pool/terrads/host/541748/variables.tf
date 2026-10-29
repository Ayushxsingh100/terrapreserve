variable "project_name" {
  description = "AWS Project Name"
  type        = string
  default     = "terraform-aws-free-tier-example"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
  default     = ""
}
