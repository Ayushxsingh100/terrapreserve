Checkov terraform checks listed: 4647 rows; AWS rows: 3612; kept: 176

| Id | Type | Entity | Policy | Source file |
|---|---|---|---|---|
| CKV2_AWS_1 | resource | aws_network_acl | Ensure that all NACL are attached to subnets | SubnetHasACL.json |
| CKV2_AWS_12 | resource | aws_default_security_group | Ensure the default security group of every VPC restricts all traffic | VPCHasRestrictedSG.json |
| CKV2_AWS_12 | resource | aws_vpc | Ensure the default security group of every VPC restricts all traffic | VPCHasRestrictedSG.json |
| CKV2_AWS_27 | resource | aws_rds_cluster | Ensure Postgres RDS as aws_rds_cluster has Query Logging enabled | PostgresRDSHasQueryLoggingEnabled.json |
| CKV2_AWS_27 | resource | aws_rds_cluster_parameter_group | Ensure Postgres RDS as aws_rds_cluster has Query Logging enabled | PostgresRDSHasQueryLoggingEnabled.json |
| CKV2_AWS_30 | resource | aws_db_instance | Ensure Postgres RDS as aws_db_instance has Query Logging enabled | PostgresDBHasQueryLoggingEnabled.json |
| CKV2_AWS_30 | resource | aws_db_parameter_group | Ensure Postgres RDS as aws_db_instance has Query Logging enabled | PostgresDBHasQueryLoggingEnabled.json |
| CKV2_AWS_37 | resource | aws_db_cluster_snapshot | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_event_subscription | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_instance | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_instance_automated_backups_replication | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_instance_role_association | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_option_group | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_parameter_group | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_proxy | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_proxy_default_target_group | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_proxy_endpoint | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_proxy_target | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_security_group | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_snapshot | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_snapshot_copy | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_db_subnet_group | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_default_network_acl | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_default_security_group | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_network_acl | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_network_acl_association | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_network_acl_rule | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_certificate | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_cluster | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_cluster_activity_stream | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_cluster_endpoint | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_cluster_instance | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_cluster_parameter_group | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_cluster_role_association | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_cluster_snapshot_copy | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_custom_db_engine_version | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_export_task | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_global_cluster | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_instance_state | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_integration | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_rds_reserved_instance | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_security_group | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_security_group_rule | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_vpc_security_group_egress_rule | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_vpc_security_group_ingress_rule | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_37 | resource | aws_vpc_security_group_vpc_association | Ensure CodeCommit associates an approval rule | CodecommitApprovalRulesAttached.json |
| CKV2_AWS_5 | resource | aws_security_group | Ensure that Security Groups are attached to another resource | SGAttachedToResource.json |
| CKV2_AWS_6 | resource | aws_s3_bucket | Ensure that S3 bucket has a Public Access block | S3BucketHasPublicAccessBlock.json |
| CKV2_AWS_6 | resource | aws_s3_bucket_public_access_block | Ensure that S3 bucket has a Public Access block | S3BucketHasPublicAccessBlock.json |
| CKV2_AWS_60 | resource | aws_db_instance | Ensure RDS instance with copy tags to snapshots is enabled | RDSEnableCopyTagsToSnapshot.json |
| CKV2_AWS_66 | resource | aws_mwaa_environment | Ensure MWAA environment is not publicly accessible | AWS_private_MWAA_environment.json |
| CKV2_AWS_69 | resource | aws_db_instance | Ensure AWS RDS database instance configured with encryption in transit | RDSEncryptionInTransit.json |
| CKV2_AWS_69 | resource | aws_db_parameter_group | Ensure AWS RDS database instance configured with encryption in transit | RDSEncryptionInTransit.json |
| CKV2_AWS_7 | resource | aws_emr_cluster | Ensure that Amazon EMR clusters' security groups are not open to the world | AMRClustersNotOpenToInternet.json |
| CKV2_AWS_7 | resource | aws_security_group | Ensure that Amazon EMR clusters' security groups are not open to the world | AMRClustersNotOpenToInternet.json |
| CKV2_AWS_75 | resource | aws_db_cluster_snapshot | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_event_subscription | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_instance | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_instance_automated_backups_replication | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_instance_role_association | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_option_group | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_parameter_group | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_proxy | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_proxy_default_target_group | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_proxy_endpoint | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_proxy_target | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_security_group | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_snapshot | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_snapshot_copy | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_db_subnet_group | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_default_network_acl | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_default_security_group | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_network_acl | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_network_acl_association | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_network_acl_rule | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_certificate | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_cluster | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_cluster_activity_stream | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_cluster_endpoint | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_cluster_instance | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_cluster_parameter_group | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_cluster_role_association | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_cluster_snapshot_copy | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_custom_db_engine_version | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_export_task | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_global_cluster | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_instance_state | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_integration | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_rds_reserved_instance | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_security_group | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_security_group_rule | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_vpc_security_group_egress_rule | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_vpc_security_group_ingress_rule | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_75 | resource | aws_vpc_security_group_vpc_association | Ensure no open CORS policy | LambdaOpenCorsPolicy.json |
| CKV2_AWS_8 | resource | aws_rds_cluster | Ensure that RDS clusters has backup plan of AWS Backup | RDSClusterHasBackupPlan.json |
| CKV_AWS_100 | resource | aws_eks_node_group | Ensure AWS EKS node group does not have implicit SSH access from 0.0.0.0/0 | EKSNodeGroupRemoteAccess.py |
| CKV_AWS_102 | resource | aws_neptune_cluster_instance | Ensure Neptune Cluster instance is not publicly available | NeptuneClusterInstancePublic.py |
| CKV_AWS_118 | resource | aws_db_instance | Ensure that enhanced monitoring is enabled for Amazon RDS instances | RDSEnhancedMonitorEnabled.py |
| CKV_AWS_118 | resource | aws_rds_cluster_instance | Ensure that enhanced monitoring is enabled for Amazon RDS instances | RDSEnhancedMonitorEnabled.py |
| CKV_AWS_129 | resource | aws_db_instance | Ensure that respective logs of Amazon Relational Database Service (Amazon RDS) are enabled | DBInstanceLogging.py |
| CKV_AWS_133 | resource | aws_db_instance | Ensure that RDS instances has backup policy | DBInstanceBackupRetentionPeriod.py |
| CKV_AWS_133 | resource | aws_rds_cluster | Ensure that RDS instances has backup policy | DBInstanceBackupRetentionPeriod.py |
| CKV_AWS_139 | resource | aws_rds_cluster | Ensure that RDS clusters have deletion protection enabled | RDSDeletionProtection.py |
| CKV_AWS_140 | resource | aws_rds_global_cluster | Ensure that RDS global clusters are encrypted | RDSClusterEncrypted.py |
| CKV_AWS_146 | resource | aws_db_cluster_snapshot | Ensure that RDS database cluster snapshot is encrypted | RDSClusterSnapshotEncrypted.py |
| CKV_AWS_157 | resource | aws_db_instance | Ensure that RDS instances have Multi-AZ enabled | RDSMultiAZEnabled.py |
| CKV_AWS_16 | resource | aws_db_instance | Ensure all data stored in the RDS is securely encrypted at rest | RDSEncryption.py |
| CKV_AWS_161 | resource | aws_db_instance | Ensure RDS database has IAM authentication enabled | RDSIAMAuthentication.py |
| CKV_AWS_162 | resource | aws_rds_cluster | Ensure RDS cluster has IAM authentication enabled | RDSClusterIAMAuthentication.py |
| CKV_AWS_164 | resource | aws_transfer_server | Ensure Transfer Server is not exposed publicly. | TransferServerIsPublic.py |
| CKV_AWS_17 | resource | aws_db_instance | Ensure all data stored in RDS is not publicly accessible | RDSPubliclyAccessible.py |
| CKV_AWS_17 | resource | aws_rds_cluster_instance | Ensure all data stored in RDS is not publicly accessible | RDSPubliclyAccessible.py |
| CKV_AWS_198 | resource | aws_db_security_group | Ensure no aws_db_security_group resources exist | RDSHasSecurityGroup.py |
| CKV_AWS_211 | resource | aws_db_instance | Ensure RDS uses a modern CaCert | RDSCACertIsRecent.py |
| CKV_AWS_226 | resource | aws_db_instance | Ensure DB instance gets all minor upgrades automatically | DBInstanceMinorUpgrade.py |
| CKV_AWS_226 | resource | aws_rds_cluster_instance | Ensure DB instance gets all minor upgrades automatically | DBInstanceMinorUpgrade.py |
| CKV_AWS_229 | resource | aws_network_acl | Ensure no NACL allow ingress from 0.0.0.0:0 to port 21 | NetworkACLUnrestrictedIngress21.py |
| CKV_AWS_229 | resource | aws_network_acl_rule | Ensure no NACL allow ingress from 0.0.0.0:0 to port 21 | NetworkACLUnrestrictedIngress21.py |
| CKV_AWS_23 | resource | aws_db_security_group | Ensure every security group and rule has a description | SecurityGroupRuleDescription.py |
| CKV_AWS_23 | resource | aws_elasticache_security_group | Ensure every security group and rule has a description | SecurityGroupRuleDescription.py |
| CKV_AWS_23 | resource | aws_redshift_security_group | Ensure every security group and rule has a description | SecurityGroupRuleDescription.py |
| CKV_AWS_23 | resource | aws_security_group | Ensure every security group and rule has a description | SecurityGroupRuleDescription.py |
| CKV_AWS_23 | resource | aws_security_group_rule | Ensure every security group and rule has a description | SecurityGroupRuleDescription.py |
| CKV_AWS_23 | resource | aws_vpc_security_group_egress_rule | Ensure every security group and rule has a description | SecurityGroupRuleDescription.py |
| CKV_AWS_23 | resource | aws_vpc_security_group_ingress_rule | Ensure every security group and rule has a description | SecurityGroupRuleDescription.py |
| CKV_AWS_230 | resource | aws_network_acl | Ensure no NACL allow ingress from 0.0.0.0:0 to port 20 | NetworkACLUnrestrictedIngress20.py |
| CKV_AWS_230 | resource | aws_network_acl_rule | Ensure no NACL allow ingress from 0.0.0.0:0 to port 20 | NetworkACLUnrestrictedIngress20.py |
| CKV_AWS_231 | resource | aws_network_acl | Ensure no NACL allow ingress from 0.0.0.0:0 to port 3389 | NetworkACLUnrestrictedIngress3389.py |
| CKV_AWS_231 | resource | aws_network_acl_rule | Ensure no NACL allow ingress from 0.0.0.0:0 to port 3389 | NetworkACLUnrestrictedIngress3389.py |
| CKV_AWS_232 | resource | aws_network_acl | Ensure no NACL allow ingress from 0.0.0.0:0 to port 22 | NetworkACLUnrestrictedIngress22.py |
| CKV_AWS_232 | resource | aws_network_acl_rule | Ensure no NACL allow ingress from 0.0.0.0:0 to port 22 | NetworkACLUnrestrictedIngress22.py |
| CKV_AWS_24 | resource | aws_security_group | Ensure no security groups allow ingress from 0.0.0.0:0 to port 22 | SecurityGroupUnrestrictedIngress22.py |
| CKV_AWS_24 | resource | aws_security_group_rule | Ensure no security groups allow ingress from 0.0.0.0:0 to port 22 | SecurityGroupUnrestrictedIngress22.py |
| CKV_AWS_24 | resource | aws_vpc_security_group_ingress_rule | Ensure no security groups allow ingress from 0.0.0.0:0 to port 22 | SecurityGroupUnrestrictedIngress22.py |
| CKV_AWS_245 | resource | aws_db_instance_automated_backups_replication | Ensure replicated backups are encrypted at rest using KMS CMKs | RDSInstanceAutoBackupEncryptionWithCMK.py |
| CKV_AWS_246 | resource | aws_rds_cluster_activity_stream | Ensure RDS Cluster activity streams are encrypted using KMS CMKs | RDSClusterActivityStreamEncryptedWithCMK.py |
| CKV_AWS_248 | resource | aws_elasticsearch_domain | Ensure that Elasticsearch is not using the default Security Group | ElasticsearchDefaultSG.py |
| CKV_AWS_248 | resource | aws_opensearch_domain | Ensure that Elasticsearch is not using the default Security Group | ElasticsearchDefaultSG.py |
| CKV_AWS_25 | resource | aws_security_group | Ensure no security groups allow ingress from 0.0.0.0:0 to port 3389 | SecurityGroupUnrestrictedIngress3389.py |
| CKV_AWS_25 | resource | aws_security_group_rule | Ensure no security groups allow ingress from 0.0.0.0:0 to port 3389 | SecurityGroupUnrestrictedIngress3389.py |
| CKV_AWS_25 | resource | aws_vpc_security_group_ingress_rule | Ensure no security groups allow ingress from 0.0.0.0:0 to port 3389 | SecurityGroupUnrestrictedIngress3389.py |
| CKV_AWS_250 | resource | aws_db_instance | Ensure that RDS PostgreSQL instances use a non vulnerable version with the log_fdw extension (https://aws.amazon.com/security/security-bulletins/AWS-2022-004/) | RDSPostgreSQLLogFDWExtension.py |
| CKV_AWS_250 | resource | aws_rds_cluster | Ensure that RDS PostgreSQL instances use a non vulnerable version with the log_fdw extension (https://aws.amazon.com/security/security-bulletins/AWS-2022-004/) | RDSPostgreSQLLogFDWExtension.py |
| CKV_AWS_260 | resource | aws_security_group | Ensure no security groups allow ingress from 0.0.0.0:0 to port 80 | SecurityGroupUnrestrictedIngress80.py |
| CKV_AWS_260 | resource | aws_security_group_rule | Ensure no security groups allow ingress from 0.0.0.0:0 to port 80 | SecurityGroupUnrestrictedIngress80.py |
| CKV_AWS_260 | resource | aws_vpc_security_group_ingress_rule | Ensure no security groups allow ingress from 0.0.0.0:0 to port 80 | SecurityGroupUnrestrictedIngress80.py |
| CKV_AWS_266 | resource | aws_db_snapshot_copy | Ensure DB Snapshot copy uses CMK | DBSnapshotCopyUsesCMK.py |
| CKV_AWS_277 | resource | aws_security_group | Ensure no security groups allow ingress from 0.0.0.0:0 to port -1 | SecurityGroupUnrestrictedIngressAny.py |
| CKV_AWS_277 | resource | aws_security_group_rule | Ensure no security groups allow ingress from 0.0.0.0:0 to port -1 | SecurityGroupUnrestrictedIngressAny.py |
| CKV_AWS_277 | resource | aws_vpc_security_group_ingress_rule | Ensure no security groups allow ingress from 0.0.0.0:0 to port -1 | SecurityGroupUnrestrictedIngressAny.py |
| CKV_AWS_293 | resource | aws_db_instance | Ensure that AWS database instances have deletion protection enabled | RDSInstanceDeletionProtection.py |
| CKV_AWS_301 | resource | aws_lambda_permission | Ensure that AWS Lambda function is not publicly accessible | LambdaFunctionIsNotPublic.py |
| CKV_AWS_302 | resource | aws_db_snapshot | Ensure DB Snapshots are not Public | DBSnapshotsArePrivate.py |
| CKV_AWS_313 | resource | aws_rds_cluster | Ensure RDS cluster configured to copy tags to snapshots | RDSClusterCopyTags.py |
| CKV_AWS_324 | resource | aws_rds_cluster | Ensure that RDS Cluster log capture is enabled | RDSClusterLogging.py |
| CKV_AWS_325 | resource | aws_rds_cluster | Ensure that RDS Cluster audit logging is enabled for MySQL engine | RDSClusterAuditLogging.py |
| CKV_AWS_326 | resource | aws_rds_cluster | Ensure that RDS Aurora Clusters have backtracking enabled | RDSClusterAuroraBacktrack.py |
| CKV_AWS_327 | resource | aws_rds_cluster | Ensure RDS Clusters are encrypted using KMS CMKs | RDSClusterEncryptedWithCMK.py |
| CKV_AWS_352 | resource | aws_network_acl_rule | Ensure NACL ingress does not allow all Ports | NetworkACLUnrestricted.py |
| CKV_AWS_353 | resource | aws_db_instance | Ensure that RDS instances have performance insights enabled | RDSInstancePerformanceInsights.py |
| CKV_AWS_353 | resource | aws_rds_cluster_instance | Ensure that RDS instances have performance insights enabled | RDSInstancePerformanceInsights.py |
| CKV_AWS_354 | resource | aws_db_instance | Ensure RDS Performance Insights are encrypted using KMS CMKs | RDSInstancePerfInsightsEncryptionWithCMK.py |
| CKV_AWS_354 | resource | aws_rds_cluster_instance | Ensure RDS Performance Insights are encrypted using KMS CMKs | RDSInstancePerfInsightsEncryptionWithCMK.py |
| CKV_AWS_38 | resource | aws_eks_cluster | Ensure Amazon EKS public endpoint not accessible to 0.0.0.0/0 | EKSPublicAccessCIDR.py |
| CKV_AWS_382 | resource | aws_security_group | Ensure no security groups allow egress from 0.0.0.0:0 to port -1 | SecurityGroupUnrestrictedEgressAny.py |
| CKV_AWS_382 | resource | aws_security_group_rule | Ensure no security groups allow egress from 0.0.0.0:0 to port -1 | SecurityGroupUnrestrictedEgressAny.py |
| CKV_AWS_382 | resource | aws_vpc_security_group_egress_rule | Ensure no security groups allow egress from 0.0.0.0:0 to port -1 | SecurityGroupUnrestrictedEgressAny.py |
| CKV_AWS_387 | resource | aws_sqs_queue_policy | Ensure SQS policy does not allow public access through wildcards | SQSOverlyPermissive.py |
| CKV_AWS_388 | resource | aws_db_instance | Ensure AWS Aurora PostgreSQL is not exposed to local file read vulnerability | UnpatchedAuroraPostgresDB.py |
| CKV_AWS_390 | resource | aws_emr_block_public_access_configuration | Ensure AWS EMR block public access setting is enabled | EMRPubliclyAccessible.py |
| CKV_AWS_391 | resource | aws_redshift_cluster | Avoid AWS Redshift cluster with commonly used master username and public access setting enabled | RedshiftClusterWithCommonUsernameAndPublicAccess.py |
| CKV_AWS_392 | resource | aws_s3_access_point | Ensure AWS S3 access point block public access setting is enabled | S3AccessPointPubliclyAccessible.py |
| CKV_AWS_69 | resource | aws_mq_broker | Ensure MQ Broker is not publicly exposed | MQBrokerNotPubliclyExposed.py |
| CKV_AWS_87 | resource | aws_redshift_cluster | Redshift cluster should not be publicly accessible | RedshitClusterPubliclyAvailable.py |
| CKV_AWS_89 | resource | aws_dms_replication_instance | DMS replication instance should not be publicly accessible | DMSReplicationInstancePubliclyAccessible.py |
| CKV_AWS_96 | resource | aws_rds_cluster | Ensure all data stored in Aurora is securely encrypted at rest | AuroraEncryption.py |
