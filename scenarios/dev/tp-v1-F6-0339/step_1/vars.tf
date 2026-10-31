variable "vpc_id" {
  type        = string
  description = "AWS VPC ID"
}

variable "is_lb_sg_ingress" {
  type        = bool
  default     = true
  description = "Apply load balancers ingress rules"

}
variable "is_lb_sg_egress" {
  type        = bool
  default     = true
  description = "Apply load balancers egress rules"

}
variable "is_web_sg_ingress" {
  type        = bool
  default     = false
  description = "Apply web servers ingress rules"

}
variable "is_web_sg_egress" {
  type        = bool
  default     = true
  description = "Apply web servers egress rules"

}
variable "lb_sg_ingress" {
  type = list(object({
    description = string,
    from_port   = number,
    to_port     = number,
    protocol    = string,
    cidrs       = list(string)
  }))

  default = [
    {
      "description" = "Allow HTTP from any",
      "from_port"   = 80,
      "to_port"     = 80,
      "protocol"    = "tcp",
      "cidrs"       = ["0.0.0.0/0"],
    },
    {
      "description" = "Allow HTTPS from any",
      "from_port"   = 443,
      "to_port"     = 443,
      "protocol"    = "tcp",
      "cidrs"       = ["0.0.0.0/0"],
    }
  ]

  description = "Ingress rules for the load balancers Security Group"
}
variable "lb_sg_egress" {
  type = list(object({
    description = string,
    from_port   = number,
    to_port     = number,
    protocol    = string,
    cidrs       = list(string)
  }))

  default = [{
    "description" = "Allow any outbound traffic",
    "from_port"   = 0,
    "to_port"     = 0,
    "protocol"    = "-1",
    "cidrs"       = ["0.0.0.0/0"]
  }]

  description = "Egress rules for the load balancers Security Group"
}
variable "web_sg_ingress" {
  type = list(object({
    description = string,
    from_port   = number,
    to_port     = number,
    protocol    = string,
    cidrs       = list(string)
  }))

  default = [{
    "description" = "",
    "from_port"   = null,
    "to_port"     = null,
    "protocol"    = "",
    "cidrs"       = [],
  }]

  description = "Ingress rules for the web servers Security Group"
}
variable "web_sg_egress" {
  type = list(object({
    description = string,
    from_port   = number,
    to_port     = number,
    protocol    = string,
    cidrs       = list(string)
  }))

  default = [{
    "description" = "Allow any outbound traffic",
    "from_port"   = 0,
    "to_port"     = 0,
    "protocol"    = "-1",
    "cidrs"       = ["0.0.0.0/0"]
  }]

  description = "Egress rules for the web servers Security Group"
}

