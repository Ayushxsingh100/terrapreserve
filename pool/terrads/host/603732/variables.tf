variable "aws_region" {
  description = "The AWS region to deploy resources in"
  type        = string
  default     = "us-east-1"
}

variable "ami_id" {
  description = "The AMI ID for the EC2 instances"
  type        = string
}

variable "key_name" {
  description = "The SSH key name to use for EC2 instances"
  type        = string
}

variable "instance_type_kafka" {
  description = "Instance type for Kafka server"
  type        = string
  default     = "t3.small"
}

variable "instance_type_logstash" {
  description = "Instance type for Logstash server"
  type        = string
  default     = "t3.small"
}

variable "instance_type_elasticsearch" {
  description = "Instance type for Elasticsearch server"
  type        = string
  default     = "t3.medium"
}

variable "instance_type_kibana" {
  description = "Instance type for Kibana server"
  type        = string
  default     = "t3.small"
}
