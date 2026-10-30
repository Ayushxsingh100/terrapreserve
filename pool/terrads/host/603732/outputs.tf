output "vpc_id" {
  description = "The ID of the created VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "The ID of the public subnet"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "The ID of the security group"
  value       = aws_security_group.default.id
}

output "kafka_instance_ip" {
  description = "The public IP address of the Kafka server"
  value       = aws_instance.kafka.public_ip
}

output "logstash_instance_ip" {
  description = "The public IP address of the Logstash server"
  value       = aws_instance.logstash.public_ip
}

output "elasticsearch_instance_ip" {
  description = "The public IP address of the Elasticsearch server"
  value       = aws_instance.elasticsearch.public_ip
}

output "kibana_instance_ip" {
  description = "The public IP address of the Kibana server"
  value       = aws_instance.kibana.public_ip
}
