# rds-backup-lambda

Small AWS Lambda function to copy automated RDS snapshots into another region.

## Installation

Create a AWS lambda function in your prefered region. Add the following environment configuration:


```
# AWS account ID
ACCOUNT = "1234567890"
# Region where the automated snapshots are located
SOURCE_REGION = "eu-west-1"
# Region where the automated snapshots should be copied to
TARGET_REGION = "eu-central-1"
# Comma separated list of RDS instances which snapshots should be copied
SOURCE_DB = "my-rds-instance"
# Comma-separated list of RDS clusters which snapshots should be copied
SOURCE_CLUSTER = "my-aurora-cluster"
# KMS Key in target region to use for snapshot encryption
DEST_KMS = "arn:aws:kms:eu-central-1:1234567890:key/abc123"
# Number of snapshots to keep
KEEP_SNAPSHOTS = 10
```

Create a `package.zip` for uploading as code:

```
make build
```
