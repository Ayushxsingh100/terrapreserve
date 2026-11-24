#In case multiple instance needs to be created using same configuration
variable "instance_names" {
    description = "List of EC2 instance names"
    type        = list(string)
    default =["web-instance", "app-instance", "db-instance", "bastin-host"]
}