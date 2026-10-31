
variable "instance_type" {
  description="The type of instance to create"
  type      = string
  default   = "t2.micro"
}
variable "instance_ami" {
  description="The AMI to use for the instance"
  type      = string
  default   = "ami-075d35647275e3501" # Amazon Linux
  
}

variable "db_engine_version" {
  description   ="The type of the RDS database engine"
  type          = string
  default       = "5.7"
}

variable "db_allocated_storage" {
  description = "The allocated storage in gigabytes"
  type = number
  default = 20
}