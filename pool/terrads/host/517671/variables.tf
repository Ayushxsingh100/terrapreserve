variable "vpd_cidr" {
    type = string
    default = "10.20.0.0/20"
}

variable "subnet_cidr_ranges" {
    type = list (string)
    default = ["10.20.1.0/25", "10.20.1.128/25", "10.20.2.0/25"]
}