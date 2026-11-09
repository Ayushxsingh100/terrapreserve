variable "vpc_id" {
  type        = string
  description = "ID for vpc"
}
variable "alb_sg_name" {
  type        = string
  description = "name for Application load balancer"
  default     = "alb_sg_name"
}
