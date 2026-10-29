output "bastion_sg_id" {
    value = aws_security_group.bastion.id
}

output "eks_control_plane_sg_id" {
    value = aws_security_group.eks_control_plane.id
}

/* output "eks_nodes_sg_id" {
    value = aws_security_group.eks_nodes.id
} */