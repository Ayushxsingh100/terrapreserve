# ----
# General
# ----

variable "enabled" {
  description = "Set to false to prevent the module from creating any resources"
  type        = bool
  default     = true
}

variable "name" {
  description = "Name for the security group"
  type        = string
}

variable "description" {
  description = "Description for the security group"
  type        = string
  default     = "Security group managed by Terraform"
}

variable "vpc_id" {
  description = "ID of the VPC where security group will be created"
  type        = string
}


variable "tags" {
  description = "Tags/labels to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "networktags_name" {
  description = "Name of the network tags key used for security group classification"
  type        = string
  default     = "NetworkTags"
}

variable "networktags_value" {
  description = "Value for the network tags key"
  type        = string
}

# ----
# Ingress Rules
# ----

variable "ingress_rules" {
  description = "List of ingress rules"
  type = list(object({
    description      = optional(string)
    from_port        = number
    to_port          = number
    protocol         = string
    cidr_blocks      = optional(list(string))
    ipv6_cidr_blocks = optional(list(string))
    security_groups  = optional(list(string))
    self             = optional(bool)
  }))
  default = []
}

variable "ingress_named_rules" {
  description = "List of ingress rules using named rule references"
  type = list(object({
    named_rule       = string
    cidr_blocks      = optional(list(string))
    ipv6_cidr_blocks = optional(list(string))
  }))
  default = []
}

# ----
# Egress Rules
# ----

variable "egress_rules" {
  description = "List of egress rules"
  type = list(object({
    description      = optional(string)
    from_port        = number
    to_port          = number
    protocol         = string
    cidr_blocks      = optional(list(string))
    ipv6_cidr_blocks = optional(list(string))
    security_groups  = optional(list(string))
    self             = optional(bool)
  }))
  default = []
}

variable "egress_named_rules" {
  description = "List of egress rules using named rule references"
  type = list(object({
    named_rule       = string
    cidr_blocks      = optional(list(string))
    ipv6_cidr_blocks = optional(list(string))
  }))
  default = []
}

# ----
# Named Rules
# ----

variable "named_rules" {
  description = "Map of named rules with port ranges and protocols"
  type = map(object({
    from_port   = number
    to_port     = number
    protocol    = string
    description = string
  }))
  default = {
    http = {
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      description = "HTTP"
    }
    http-8080 = {
      from_port   = 8080
      to_port     = 8080
      protocol    = "tcp"
      description = "HTTP"
    }
    https = {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      description = "HTTPS"
    }
    https-8443 = {
      from_port   = 8443
      to_port     = 8443
      protocol    = "tcp"
      description = "HTTPS"
    }
    mysql = {
      from_port   = 3306
      to_port     = 3306
      protocol    = "tcp"
      description = "MySQL/Aurora"
    }
    postgres = {
      from_port   = 5432
      to_port     = 5432
      protocol    = "tcp"
      description = "PostgreSQL"
    }
    oracle = {
      from_port   = 1521
      to_port     = 1521
      protocol    = "tcp"
      description = "Oracle"
    }
    mssql = {
      from_port   = 1433
      to_port     = 1433
      protocol    = "tcp"
      description = "Microsoft SQL Server"
    }
    mariadb = {
      from_port   = 3306
      to_port     = 3306
      protocol    = "tcp"
      description = "MariaDB"
    }
    db2 = {
      from_port   = 50000
      to_port     = 50000
      protocol    = "tcp"
      description = "IBM Db2"
    }
    redis = {
      from_port   = 6379
      to_port     = 6379
      protocol    = "tcp"
      description = "Redis"
    }
    memcached = {
      from_port   = 11211
      to_port     = 11211
      protocol    = "tcp"
      description = "Memcached"
    }
    neptune = {
      from_port   = 8182
      to_port     = 8182
      protocol    = "tcp"
      description = "Neptune"
    }
    redshift = {
      from_port   = 5439
      to_port     = 5439
      protocol    = "tcp"
      description = "Redshift"
    }
    timestream = {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      description = "Timestream"
    }
    documentdb = {
      from_port   = 27017
      to_port     = 27017
      protocol    = "tcp"
      description = "DocumentDB"
    }
    qldb = {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      description = "QLDB"
    }
    dynamodb = {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      description = "DynamoDB"
    }
    activemq = {
      from_port   = 61617
      to_port     = 61617
      protocol    = "tcp"
      description = "ActiveMQ"
    }
    activemq-web = {
      from_port   = 8162
      to_port     = 8162
      protocol    = "tcp"
      description = "ActiveMQ Web Console"
    }
    rabbitmq = {
      from_port   = 5672
      to_port     = 5672
      protocol    = "tcp"
      description = "RabbitMQ"
    }
    rabbitmq-web = {
      from_port   = 15672
      to_port     = 15672
      protocol    = "tcp"
      description = "RabbitMQ Web Console"
    }
    opensearch = {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      description = "OpenSearch"
    }
    opensearch-dashboards = {
      from_port   = 5601
      to_port     = 5601
      protocol    = "tcp"
      description = "OpenSearch Dashboards"
    }
    prometheus = {
      from_port   = 9090
      to_port     = 9090
      protocol    = "tcp"
      description = "Prometheus"
    }
    grafana = {
      from_port   = 3000
      to_port     = 3000
      protocol    = "tcp"
      description = "Grafana"
    }
    all-all = {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      description = "All protocols"
    }
    all-tcp = {
      from_port   = 0
      to_port     = 65535
      protocol    = "tcp"
      description = "All TCP"
    }
    all-udp = {
      from_port   = 0
      to_port     = 65535
      protocol    = "udp"
      description = "All UDP"
    }
    all-icmp = {
      from_port   = -1
      to_port     = -1
      protocol    = "icmp"
      description = "All ICMP"
    }
    all-icmpv6 = {
      from_port   = -1
      to_port     = -1
      protocol    = "icmpv6"
      description = "All ICMPv6"
    }
  }
}