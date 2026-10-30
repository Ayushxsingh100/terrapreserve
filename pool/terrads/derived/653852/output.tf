# output "webapp_instance_id" {
#   description = "The ID of the web application EC2 instance"
#   value = aws_instance.webapp_instance.id
# }

# output "webapp_instance_availability_zone" {
#   description = "The availability zone of the web application EC2 instance"
#   value = aws_instance.webapp_instance.availability_zone
  
# }

output "database_endpoint" {
  description = "The endpoint of the RDS database instance."
  value = aws_db_instance.database_instance.endpoint
}

output "database_address" {
  description = "The address of the RDS database instance."
  value = aws_db_instance.database_instance.address
}