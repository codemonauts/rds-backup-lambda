#! /usr/bin/env python3

"""
Small AWS Lambda function to copy RDS snapshots to another region.
"""

import datetime
import re

import boto3
import botocore

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


class BackupException(Exception):
    """
    Backup exception raised when somthing went wrong doing the backups.
    """


def by_snapshot_id(snap):
    """
    Returns the snapshot identifier for an RDS instance
    """
    return snap["DBSnapshotIdentifier"]


def by_cluster_snapshot_id(snap):
    """
    Returns the snapshot identifier for an RDS cluster instance
    """
    return snap["DBClusterSnapshotIdentifier"]


def by_timestamp(snap):
    """
    Returns the timestamp of a snapshot
    """
    if "SnapshotCreateTime" in snap:
        return datetime.datetime.isoformat(snap["SnapshotCreateTime"])
    return datetime.datetime.isoformat(datetime.datetime.now())


def copy_rds_snapshots(source_client, target_client, account, name):
    """
    Copies snapshots from an RDS instance
    """
    print(f"Copying snapshots for {name}")
    source_snaps = source_client.describe_db_snapshots(SnapshotType="automated", DBInstanceIdentifier=name)[
        "DBSnapshots"
    ]
    if len(source_snaps) == 0:
        print("Found no automated snapshots. Nothing to do")
        return

    source_snap = sorted(source_snaps, key=by_snapshot_id, reverse=True)[0]["DBSnapshotIdentifier"]
    source_snap_arn = f"arn:aws:rds:{SOURCE_REGION}:{account}:snapshot:{source_snap}"
    target_snap_id = f"copy-of-{re.sub('rds:', '', source_snap)}"
    print(f"Will copy {source_snap_arn} to {target_snap_id}")

    try:
        target_client.copy_db_snapshot(
            SourceDBSnapshotIdentifier=source_snap_arn,
            TargetDBSnapshotIdentifier=target_snap_id,
            KmsKeyId=DEST_KMS,
            CopyTags=True,
            SourceRegion=SOURCE_REGION,
        )
    except botocore.exceptions.ClientError as ex:
        raise BackupException(f"Could not issue copy command: {ex}") from ex

    copied_snaps = target_client.describe_db_snapshots(SnapshotType="manual", DBInstanceIdentifier=name)["DBSnapshots"]
    if len(copied_snaps) > KEEP:
        for snap in sorted(copied_snaps, key=by_timestamp, reverse=True)[KEEP:]:
            print(f"Will remove {snap['DBSnapshotIdentifier']}")
            try:
                target_client.delete_db_snapshot(DBSnapshotIdentifier=snap["DBSnapshotIdentifier"])
            except botocore.exceptions.ClientError as ex:
                raise BackupException(f"Could not delete snapshot {snap['DBSnapshotIdentifier']}: {ex}") from ex


def copy_cluster_snapshots(source_client, target_client, account, cluster_name):
    """
    Coppies snapshots from a RDS cluster
    """
    print(f"Copying snapshots for {cluster_name}")
    source_snaps = source_client.describe_db_cluster_snapshots(
        SnapshotType="automated", DBClusterIdentifier=cluster_name
    )["DBClusterSnapshots"]
    if len(source_snaps) == 0:
        print("Found no automated snapshots. Nothing to do")
        return
    source_snap = sorted(source_snaps, key=by_cluster_snapshot_id, reverse=True)[0]["DBClusterSnapshotIdentifier"]
    source_snap_arn = f"arn:aws:rds:{SOURCE_REGION}:{account}:cluster-snapshot:{source_snap}"
    target_snap_id = f"copy-of-{re.sub('rds:', '', source_snap)}"
    print(f"Will copy {source_snap_arn} to {target_snap_id}")

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
        for snap in sorted(copied_snaps, key=by_timestamp, reverse=True)[KEEP:]:
            snap_id = snap["DBClusterSnapshotIdentifier"]
            print(f"Will remove {snap_id}")
            try:
                target_client.delete_db_snapshot(DBClusterSnapshotIdentifier=snap_id)
            except botocore.exceptions.ClientError as ex:
                raise BackupException(f"Could not delete snapshot {snap_id}: {ex}") from ex


def lambda_handler(event, context):
    """
    Entrypoint for AWS Lambda
    """
    if context:
        print(f"Starting '{context.function_name}' version {context.function_version}")

    target_region = event["region"]
    account = event["account"]
    source_client = boto3.client("rds", region_name=SOURCE_REGION)
    target_client = boto3.client("rds", region_name=target_region)
    for name in SOURCE_DB:
        copy_rds_snapshots(source_client, target_client, account, name)
    for name in SOURCE_CLUSTER:
        copy_cluster_snapshots(source_client, target_client, account, name)
