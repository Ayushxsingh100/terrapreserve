resource "aws_rds_cluster_instance" "d" {
  cluster_identifier = "c"
  instance_class     = "db.t3.medium"
  engine             = "aurora-postgresql"
}
