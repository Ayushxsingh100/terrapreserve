variable "project_name" {
  type        = string
  description = "Project name for tagging"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID"
}

variable "my_ip" {
  type        = string
  description = "Client's static IP address for SSH access to EC2 (in CIDR format)"
  default     = "0.0.0.0/0"
}
