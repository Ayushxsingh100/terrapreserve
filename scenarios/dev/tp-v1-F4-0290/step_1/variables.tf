#################
# Security group
#################
variable "create" {
  description = "Whether to create security group and all rules"
  type        = bool
  default     = true
}

variable "create_sg" {
  description = "Whether to create security group"
  type        = bool
  default     = true
}

variable "security_group_id" {
  description = "ID of existing security group whose rules we will manage"
  type        = string
  default     = null
}

variable "vpc_id" {
  description = "ID of the VPC where to create security group"
  type        = string
  default     = null
}

variable "name" {
  description = "Name of security group - not required if create_group is false"
  type        = string
  default     = null
}

variable "use_name_prefix" {
  description = "Whether to use name_prefix or fixed name. Should be true to able to update security group name after initial creation"
  type        = bool
  default     = true
}

variable "description" {
  description = "Description of security group"
  type        = string
  default     = "Security Group managed by Terraform"
}

variable "revoke_rules_on_delete" {
  description = "Instruct Terraform to revoke all of the Security Groups attached ingress and egress rules before deleting the rule itself. Enable for EMR."
  type        = bool
  default     = false
}

variable "tags" {
  description = "A mapping of tags to assign to security group"
  type        = map(string)
  default     = {}
}

##########
# Ingress
##########
variable "ingress_rules" {
  description = "List of ingress rules to create by name"
  type        = list(string)
  default     = []
}

variable "ingress_with_self" {
  description = "List of ingress rules to create where 'self' is defined"
  type        = list(map(string))
  default     = []
}

variable "ingress_with_cidr_blocks" {
  description = "List of ingress rules to create where 'cidr_blocks' is used"
  type        = list(map(string))
  default     = []
}

variable "ingress_with_ipv6_cidr_blocks" {
  description = "List of ingress rules to create where 'ipv6_cidr_blocks' is used"
  type        = list(map(string))
  default     = []
}

variable "ingress_with_source_security_group_id" {
  description = "List of ingress rules to create where 'source_security_group_id' is used"
  type        = list(map(string))
  default     = []
}

variable "ingress_cidr_blocks" {
  description = "List of IPv4 CIDR ranges to use on all ingress rules"
  type        = list(string)
  default     = []
}

variable "ingress_ipv6_cidr_blocks" {
  description = "List of IPv6 CIDR ranges to use on all ingress rules"
  type        = list(string)
  default     = []
}

variable "ingress_prefix_list_ids" {
  description = "List of prefix list IDs (for allowing access to VPC endpoints) to use on all ingress rules"
  type        = list(string)
  default     = []
}

########
# Egress
#########
variable "egress_rules" {
  description = "List of egress rules to create by name"
  type        = list(string)
  default     = []
}

variable "egress_with_self" {
  description = "List of egress rules to create where 'self' is defined"
  type        = list(map(string))
  default     = []
}

variable "egress_with_cidr_blocks" {
  description = "List of egress rules to create where 'cidr_blocks' is used"
  type        = list(map(string))
  default     = []
}

variable "egress_with_ipv6_cidr_blocks" {
  description = "List of egress rules to create where 'ipv6_cidr_blocks' is used"
  type        = list(map(string))
  default     = []
}

variable "egress_with_source_security_group_id" {
  description = "List of egress rules to create where 'source_security_group_id' is used"
  type        = list(map(string))
  default     = []
}

variable "egress_cidr_blocks" {
  description = "List of IPv4 CIDR ranges to use on all egress rules"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "egress_ipv6_cidr_blocks" {
  description = "List of IPv6 CIDR ranges to use on all egress rules"
  type        = list(string)
  default     = ["::/0"]
}

variable "egress_prefix_list_ids" {
  description = "List of prefix list IDs (for allowing access to VPC endpoints) to use on all egress rules"
  type        = list(string)
  default     = []
}


#rules
variable "rules" {
  description = "Map of known security group rules (define as 'name' = ['from port', 'to port', 'protocol', 'description'])"
  type        = map(list(any))

  # Protocols (tcp, udp, icmp, all - are allowed keywords) or numbers (from https://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml):
  # All = -1, IPV4-ICMP = 1, TCP = 6, UDP = 17, IPV6-ICMP = 58
  default = {
    rdp-tcp = [3389, 3389, "tcp", "Remote Desktop"]
    rdp-udp = [3389, 3389, "udp", "Remote Desktop"]
    all-all       = [-1, -1, "-1", "All protocols"]  #engress for SG
    custom-161-udp = [161, 161, "udp", "custom-161-udp"]
    custom-162-udp = [162, 162, "udp", "custom-162-udp"]
    custom-5721-tcp = [5721, 5721, "tcp", "custom-5721-tcp"]
    custom-55721-tcp = [55721, 55721, "tcp", "custom-55721-tcp"]
    custom-8081-tcp = [8081, 8081, "tcp", "custom-8081-tcp"]
    custom-8082-tcp = [8082, 8082, "tcp", "custom-8082-tcp"]
    custom-8888-tcp = [8888, 8888, "tcp", "custom-8888-tcp"]
    custom-1443-tcp = [1443, 1443, "tcp", "custom-1443-tcp"]
    custom-1433-tcp = [1433, 1433, "tcp", "custom-1433-tcp"]
    custom-1434-tcp = [1434, 1434, "tcp", "custom-1434-tcp"]
    custom-24020-tcp = [24020, 24020, "tcp", "custom-24020-tcp"]
    custom-8443-tcp = [8443, 8443, "tcp", "custom-8443-tcp"]
    custom-50000-tcp = [50000, 50000, "tcp", "custom-50000-tcp"]
    
    
    http-80-tcp   = [80, 80, "tcp", "HTTP"]
    https-443-tcp  = [443, 443, "tcp", "HTTPS"]

    ssh-tcp   = [22, 22, "tcp", "ssh"]

    all-tcp       = [-1, -1, "tcp", "all tcp"]
    all-udp       = [-1, -1, "udp", "all udp"]
    
    #for printer
    http-9191-tcp   = [9191, 9191, "tcp", "http-9191-tcp"]
    https-9192-tcp  = [9192, 9192, "tcp", "https-9192-tcp"]
    rpc-9193-tcp  = [9193, 9193, "tcp", "rpc-9193-tcp"]
    #custom-161-udp = [161, 161, "udp", "custom-161-udp"]
    netbios-137-udp = [137, 137, "udp", "netbios-137-udp"]
    netbios-138-udp = [138, 138, "udp", "netbios-138-udp"]
    netbios-139-tcp = [139, 139, "tcp", "netbios-139-tcp"]
    smb-445-tcp = [445, 445, "tcp", "smb-445-tcp"]
    pcut-5114-tcp = [5114, 5114, "tcp", "pcut-5114-tcp"]
    pcut-5114-udp = [5114, 5114, "udp", "pcut-5114-udp"]
    ldap-389-tcp = [389, 389, "tcp", "ldap-389-tcp"]
    ldap-389-udp = [389, 389, "udp", "ldap-389-udp"]
    ldaps-636-tcp = [636, 636, "tcp", "ldaps-636-tcp"]
    ldaps-636-udp = [636, 636, "udp", "ldaps-636-udp"]
    printing-9100-udp = [9100, 9100, "udp", "printing-9100-udp"]
    printing-9100-tcp = [9100, 9100, "tcp", "printing-9100-tcp"]
    printing-515-udp = [515, 515, "udp", "printing-515-udp"]
    printing-515-tcp = [515, 515, "tcp", "printing-515-tcp"]
    #http-80-tcp   = [80, 80, "tcp", "HTTP"]
    #https-443-tcp  = [443, 443, "tcp", "HTTPS"]
    pcutmfp-7627-tcp = [7627, 7627, "tcp", "pcutmfp-7627-tcp"]
    
    oracle-1521-tcp = [1521, 1521, "tcp", "oracle-1521-tcp"]
    mysql-3306-tcp = [3306, 3306, "tcp", "mysql-3306-tcp"]
    postgres-5432-tcp = [5432, 5432, "tcp", "postgres-5432-tcp"]
    #custom-1433-tcp = [1433, 1433, "tcp", "custom-1433-tcp"]
    custom-1450-tcp = [1450, 1450, "tcp", "custom-1450-tcp"]
    
    
    custom-9163-tcp = [9163, 9163, "tcp", "custom-9163-tcp"]
    custom-9164-tcp = [9164, 9164, "tcp", "custom-9164-tcp"]
    dns-53-udp = [53, 53, "udp", "dns-53-udp"]
    mdns-5353-udp = [5353, 5353, "udp", "dns-5353-udp"]
    
  }
}
