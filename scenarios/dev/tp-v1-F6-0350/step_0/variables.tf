variable "aws_security_group_name" {
  description = "AWS security group name"
  default     = "ecs-sg"
  type        = string
}
variable "aws_vpc_id" {
  description = "vpc id"
  type        = string
}