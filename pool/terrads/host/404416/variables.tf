variable "allow_ssh_from" {
  type        = list(any)
  description = "An IP address, a CIDR block, or a single security group identifier to allow incoming SSH connection to the virtual server"
  default     = ["0.0.0.0/0"]
  #   default     = []
}

variable "allow_acl_from" {
  #  type        = list(any)
  type        = string
  description = "An IP address, a CIDR block, or a single security group identifier to allow incoming SSH connection to the virtual server"
  #  default     = ["0.0.0.0/0"]
  default = "0.0.0.0/0"
}

variable "init_script" {
  type        = string
  default     = ""
  description = "User data to provide when launching the instance."
}

variable "base_security_group" {
  type        = string
  description = "ID of the base security group(SG) to use for the ec2 instance. If not provided a new SG  will be created."
  default     = null
}

variable "defacl_id" {
  type        = string
  description = "ID of the base security group(SG) to use for the ec2 instance. If not provided a new SG  will be created."
  default     = ""
  #  default = "sg-05637f6e2caa0bef0"
}



variable "base_acl_group" {
  type        = string
  description = "ID of the base ACL to use for the ec2 instance. If not provided a new ACL  will be created."
  default     = null
}


variable "access_key" {
  type    = string
  default = ""
}

variable "secret_key" {
  type    = string
  default = ""
}


variable "publickey" {
  type        = string
  default     = ""
  description = "EC2 Instance Public Key"
}


variable "vpc_cidr" {
  default = "10.20.0.0/16"
}

#- single SN approach

variable "subnets_ids" {
  type    = list(string)
  default = []
}

variable "name_prefix" {
  type        = string
  description = "Prefix to be added to the names of resources which are being provisioned"
  default     = "swe"
}

variable "kms_key_id" {
  type        = string
  description = "KMS ID"
  default     = ""
}

variable "pri_instance_monitoring" {
  type        = bool
  default     = false
  description = "Enable  EC2 private instance advance monitoring"
}

variable "pub_instance_monitoring" {
  type        = bool
  default     = true
  description = "Enable EC2 public instance advance monitoring"
}

variable "ssh_key" {
  type    = string
  default = ""
  #  default     = "sivasaivm-pub"
  description = "AWS EC2 Instance Public Key"
}

variable "ami_id" {
  type        = string
  description = "AMI ID for bastion host"
  default     = "ami-03fa4afc89e4a8a09"
  #  default = "ami-0573b70afecda915d"
}

variable "subnets_count" {
  type    = number
  default = 0
}

variable "public_key" {
  type    = string
  default = ""
}

variable "private_key" {
  type    = string
  default = ""
}

variable "rsa_bits" {
  type    = number
  default = 4096
}

variable "instance_type" {
  type        = string
  description = "EC2 Instance Type"
  default     = "t3.large"
}

#used by VPC,Subnet & EC2 Module #
variable "vpc_id" {
  type        = string
  description = "The id of the existing VPC instance"
  default     = ""
}


variable "label" {
  type        = string
  description = "The label for the server instance"
  default     = "server"
}


variable "root_volume_type" {
  type        = string
  description = "Type of root volume. Can be standard, gp2 or io1"
  default     = "gp2"
}

variable "root_volume_size" {
  type        = number
  description = "Size of the root volume in gigabytes"
  default     = 10
}

variable "root_block_device_encrypted" {
  type        = bool
  default     = true
  description = "Whether to encrypt the root block device"
}


variable "publicIP" {
  type        = bool
  default     = false
  description = "Whether to attach a public IP to EC2 instance"
}

variable "cidr_blocks" {
  type        = list(any)
  default     = ["0.0.0.0/0"]
  description = "SG CIDR"
}


######Other options which can be used###

variable "security_groups" {
  description = "A list of Security Group IDs to associate with EC2 instance."
  type        = list(string)
  default     = []
}

variable "security_group_rules" {
  type = list(object({
    name        = string,
    type        = string,
    protocol    = string,
    from_port   = number,
    to_port     = number,
    cidr_blocks = optional(string),
    ip_version  = optional(string),
  }))
  description = "List of security group rules to set on the bastion security group in addition to the SSH rules"
  default     = []
}


variable "acl_group_rules" {
  type = list(object({
    rule_number = number,
    egress      = bool,
    protocol    = string,
    rule_action = string,
    cidr_block  = optional(string),
    from_port   = number,
    to_port     = number,
  }))
  description = "List of security group rules to set on the bastion security group in addition to the SSH rules"
  default     = []
}
