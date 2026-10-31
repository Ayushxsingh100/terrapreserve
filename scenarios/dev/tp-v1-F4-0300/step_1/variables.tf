variable aws_build_tags {
  description = "A map of tags to apply to the AWS infrastructure."
  type = map
}
variable name {
  description = "The name of the subnet"
  type = string
  default = "green"
}



variable internet_gateway_id {
  type = string
}

variable "aws_availability_zone" {
  type = string
  default = "ca-central-1"
} 

variable vpc_id {
  type=string
}

variable public_subnets {
    type=string
    default = "10.50.0.0/20"
} 
variable manage_subnets {
    default = "10.50.16.0/20"
}
variable private_subnets {
    default ="10.50.32.0/20"
} 

#############################################
##Address space layout:
##
## 1) Take 10.X.0.0/16 and split it into 4x address space between
##      1) 10.X.0.0/18 (16k hosts per /18)
##      2) 10.X.64.0/18
##      3) 10.X.128.0/18
##      4) 10.X.192.0/18
##
## 2) Take each /18 and split into 4x /20 addresses:
##     1) 10.X.0.0/18:
##   1.1)   10.X.0.0/20 (4k hosts per /20)	
##   1.2)   10.X.16.0/20
##   1.3)   10.X.32.0/20
##   1.4)   10.X.48.0/20
##
#########################################################################
## https://www.davidc.net/sites/default/subnets/subnets.html
###########################################################################
#Subnet address	Netmask	Range of addresses	Useable IPs	Hosts	Divide	Join
####1/4 of the space split into 4 more parts.
#10.X.0.0/20	255.255.240.0	10.0.0.0 - 10.0.15.255	10.0.0.1 - 10.0.15.254	4094	Divide					
#10.X.16.0/20	255.255.240.0	10.0.16.0 - 10.0.31.255	10.0.16.1 - 10.0.31.254	4094	Divide	
#10.X.32.0/20	255.255.240.0	10.0.32.0 - 10.0.47.255	10.0.32.1 - 10.0.47.254	4094	Divide		
#10.X.48.0/20	255.255.240.0	10.0.48.0 - 10.0.63.255	10.0.48.1 - 10.0.63.254	4094	Divide	
#
####2/4 of the space split into 4 more parts.
#10.Y.64.0/18	255.255.192.0	10.0.64.0 - 10.0.127.255	10.0.64.1 - 10.0.127.254	16382	Divide	
#...
####3/4 of the space split into 4 more parts.
#10.Z.128.0/18	255.255.192.0	10.0.128.0 - 10.0.191.255	10.0.128.1 - 10.0.191.254	16382	Divide		
#...
####4/4 of the space split into 4 more parts.
#10.A.192.0/18	255.255.192.0	10.0.192.0 - 10.0.255.255	10.0.192.1 - 10.0.255.254	16382	Divide	
#...