output "instance-ip"{
    value = aws_instance.tutorial-instance.*.public_ip
}