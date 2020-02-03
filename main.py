#! /usr/bin/env python3
import boto3
import botocore
import datetime
import re

# Region where the automated snapshots are located
SOURCE_REGION = "eu-west-1"
# List of RDS instances which snapshots should be copied
SOURCE_DB = ["my-rds-instance"]
# List of RDS clusters which snapshots should be copied
SOURCE_CLUSTER = ["my-aurora-cluster", "my-second-cluster"]
# KMS Key in target region to use for Aurora Cluster Snapshots
DEST_KMS = "arn:aws:kms:eu-central-1:ABC123:key/abc123"
# Number of snapshots to keep
KEEP = 10


def bySnapshotId(snap):
    return snap["DBSnapshotIdentifier"]


def byClusterSnapshotId(snap):
    return snap["DBClusterSnapshotIdentifier"]


def byTimestamp(snap):
    if "SnapshotCreateTime" in snap:
        return datetime.datetime.isoformat(snap["SnapshotCreateTime"])
    else:
        return datetime.datetime.isoformat(datetime.datetime.now())


def copy_rds_snapshots(source_client, target_client, account, name):
    print("Copying snapshots for {}".format(name))
    source_snaps = source_client.describe_db_snapshots(SnapshotType="automated", DBInstanceIdentifier=name)[
        "DBSnapshots"
    ]
    if len(source_snaps) == 0:
        print("Found no automated snapshots. Nothing to do")
        return

    source_snap = sorted(source_snaps, key=bySnapshotId, reverse=True)[0]["DBSnapshotIdentifier"]
    source_snap_arn = "arn:aws:rds:{}:{}:snapshot:{}".format(SOURCE_REGION, account, source_snap)
    target_snap_id = "copy-of-{}".format(re.sub("rds:", "", source_snap))
    print("Will copy {} to {}".format(source_snap_arn, target_snap_id))

    try:
        target_client.copy_db_snapshot(
            SourceDBSnapshotIdentifier=source_snap_arn,
            TargetDBSnapshotIdentifier=target_snap_id,
            KmsKeyId=DEST_KMS,
            CopyTags=True,
            SourceRegion=SOURCE_REGION,
        )
    except botocore.exceptions.ClientError as e:
        raise Exception("Could not issue copy command: %s" % e)

    copied_snaps = target_client.describe_db_snapshots(SnapshotType="manual", DBInstanceIdentifier=name)["DBSnapshots"]
    if len(copied_snaps) > KEEP:
        for snap in sorted(copied_snaps, key=byTimestamp, reverse=True)[KEEP:]:
            print("Will remove {}".format(snap["DBSnapshotIdentifier"]))
            try:
                target_client.delete_db_snapshot(DBSnapshotIdentifier=snap["DBSnapshotIdentifier"])
            except botocore.exceptions.ClientError as e:
                raise Exception("Could not delete snapshot {}: {}".format(snap["DBSnapshotIdentifier"], e))


def copy_cluster_snapshots(source_client, target_client, account, cluster_name):
    print("Copying snapshots for {}".format(cluster_name))
    source_snaps = source_client.describe_db_cluster_snapshots(
        SnapshotType="automated", DBClusterIdentifier=cluster_name
    )["DBClusterSnapshots"]
    if len(source_snaps) == 0:
        print("Found no automated snapshots. Nothing to do")
        return
    source_snap = sorted(source_snaps, key=byClusterSnapshotId, reverse=True)[0]["DBClusterSnapshotIdentifier"]
    source_snap_arn = "arn:aws:rds:{}:{}:cluster-snapshot:{}".format(SOURCE_REGION, account, source_snap)
    target_snap_id = "copy-of-{}".format(re.sub("rds:", "", source_snap))
    print("Will copy {} to {}".format(source_snap_arn, target_snap_id))

    target_client.copy_db_cluster_snapshot(
        SourceDBClusterSnapshotIdentifier=source_snap_arn,
        TargetDBClusterSnapshotIdentifier=target_snap_id,
        KmsKeyId=DEST_KMS,
        SourceRegion=SOURCE_REGION,
    )

    copied_snaps = target_client.describe_db_cluster_snapshots(SnapshotType="manual", DBClusterIdentifier=cluster_name)[
        "DBClusterSnapshots"
    ]
    if len(copied_snaps) > KEEP:
        for snap in sorted(copied_snaps, key=byTimestamp, reverse=True)[KEEP:]:
            snap_id = snap["DBClusterSnapshotIdentifier"]
            print("Will remove {}".format(snap_id))
            try:
                target_client.delete_db_snapshot(DBClusterSnapshotIdentifier=snap_id)
            except botocore.exceptions.ClientError as e:
                raise Exception("Could not delete snapshot {}: {}".format(snap_id, e))


def lambda_handler(event, context):
    target_region = event["region"]
    account = event["account"]
    source_client = boto3.client("rds", region_name=SOURCE_REGION)
    target_client = boto3.client("rds", region_name=target_region)
    for name in SOURCE_DB:
        copy_rds_snapshots(source_client, target_client, account, name)
    for name in SOURCE_CLUSTER:
        copy_cluster_snapshots(source_client, target_client, account, name)
