output "lambda_sg_id" {
  description = "The ID of the security group for the Lambda function"
  value       = aws_security_group.lambda_sg.id
}
