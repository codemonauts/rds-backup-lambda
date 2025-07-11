# rds-backup-lambda

Small AWS Lambda function to copy automated RDS snapshots into another region.

## Installation by hand

### Role and policy

Create a role for the Lambda function and add the following policy. Please replace the `<REGION>` and `<ACCOUNTID>` with your values.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "rds:ListTagsForResource",
                "rds:Describe*",
                "rds:DeleteDBSnapshot",
                "rds:CopyDBSnapshot",
                "rds:CopyDBClusterSnapshot",
                "rds:CopyCustomDBEngineVersion",
                "rds:AddTagsToResource"
            ],
            "Effect": "Allow",
            "Resource": "*"
        },
        {
            "Action": [
                "logs:PutLogEvents",
                "logs:CreateLogStream"
            ],
            "Effect": "Allow",
            "Resource": "arn:aws:logs:<REGION>:<ACCOUNTID>:log-group:/aws/lambda/rds-backup:*"
        }
    ]
}
```

### Build package for Lambda

Run the following command to build a `package.zip` with the code for the Lambda function.

```shell
make build
```

### Lambda function

You can create the Lambda function with the console. The following settings are recommended:

- Timeout wit 60 seconds or more (depends on the number of snapshots to copy).
- Runtime is Python 3.13 or newer.
- The handler is `main.lambda_handler`.
- Architecture can be `arm64` or `x86_64`.

Or create a Lambda function with the AWS CLI. Replace the `<ARN>` with the ARN of the role created above:

```shell
aws lambda create-function \
    --function-name rds-backup \
    --runtime python3.13 \
    --zip-file fileb://package.zip \
    --handler main.lambda_handler \
    --timeout 60 \
    --publish \
    --architectures arm64 \
    --role <ARN>
```

Add the following environment configuration to the Lambda function:


```shell
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
KEEP_SNAPSHOTS = 1
```

You have now a Lambda function without a trigger. We suggest to use an EventBridge schedule rule or the EventBridge Scheduler.

## Installation by Terraform

You can use the `main.tf` to

- Create all roles.
- A log group.
- The Lambda function itself.
- A scheduler to invoke the Lambda function at a one days rate.

If you know what you do, you can do:

```shell
make build
make plan
make deploy
```
