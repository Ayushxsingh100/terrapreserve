variable "name_prefix" {
  type = string
}
variable "sg_names" { # A map of security group names, allows choosing names for the code 
  type = map(string)
  default = {
    "web_alb" = "web-alb-sg"
    "web"     = "web-sg"
    "app_alb" = "app-alb-sg"
    "app"     = "app-sg"
    "data"    = "data-sg"
  }
}

variable "sg_ports" {      # Port numbers, used in dynamic blocks 
  type = map(list(number)) # A map, a list, and numbers 
  default = {
    http     = [80]
    web_alb  = [80, 443]
    database = [3306]
  }
}

variable "vpc_id" {
  type = string
} # The VPC from the VPC module, it will be used in security groups resources 
