#! /usr/bin/env python3

"""
Small AWS Lambda function to copy RDS snapshots to another region.
"""

import datetime
import re

import boto3
import botocore
from environs import Env


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


def copy_rds_snapshots(source_client, target_client, source_region, account, name, kms, keep):
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
    source_snap_arn = f"arn:aws:rds:{source_region}:{account}:snapshot:{source_snap}"
    target_snap_id = f"copy-of-{re.sub('rds:', '', source_snap)}"
    print(f"Will copy {source_snap_arn} to {target_snap_id}")

    try:
        target_client.copy_db_snapshot(
            SourceDBSnapshotIdentifier=source_snap_arn,
            TargetDBSnapshotIdentifier=target_snap_id,
            KmsKeyId=kms,
            CopyTags=True,
            SourceRegion=source_region,
        )
    except botocore.exceptions.ClientError as ex:
        raise BackupException(f"Could not issue copy command: {ex}") from ex

    copied_snaps = target_client.describe_db_snapshots(SnapshotType="manual", DBInstanceIdentifier=name)["DBSnapshots"]
    if len(copied_snaps) > keep:
        for snap in sorted(copied_snaps, key=by_timestamp, reverse=True)[keep:]:
            print(f"Will remove {snap['DBSnapshotIdentifier']}")
            try:
                target_client.delete_db_snapshot(DBSnapshotIdentifier=snap["DBSnapshotIdentifier"])
            except botocore.exceptions.ClientError as ex:
                raise BackupException(f"Could not delete snapshot {snap['DBSnapshotIdentifier']}: {ex}") from ex


def copy_cluster_snapshots(source_client, target_client, source_region, account, cluster_name, kms, keep):
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
    source_snap_arn = f"arn:aws:rds:{source_region}:{account}:cluster-snapshot:{source_snap}"
    target_snap_id = f"copy-of-{re.sub('rds:', '', source_snap)}"
    print(f"Will copy {source_snap_arn} to {target_snap_id}")

    target_client.copy_db_cluster_snapshot(
        SourceDBClusterSnapshotIdentifier=source_snap_arn,
        TargetDBClusterSnapshotIdentifier=target_snap_id,
        KmsKeyId=kms,
        SourceRegion=source_region,
    )

    copied_snaps = target_client.describe_db_cluster_snapshots(SnapshotType="manual", DBClusterIdentifier=cluster_name)[
        "DBClusterSnapshots"
    ]
    if len(copied_snaps) > keep:
        for snap in sorted(copied_snaps, key=by_timestamp, reverse=True)[keep:]:
            snap_id = snap["DBClusterSnapshotIdentifier"]
            print(f"Will remove {snap_id}")
            try:
                target_client.delete_db_snapshot(DBClusterSnapshotIdentifier=snap_id)
            except botocore.exceptions.ClientError as ex:
                raise BackupException(f"Could not delete snapshot {snap_id}: {ex}") from ex


def lambda_handler(event, context):  # pylint: disable=unused-argument
    """
    Entrypoint for AWS Lambda
    """

    # Get config from environment
    env = Env()
    source_region = env.str("SOURCE_REGION")
    source_db = env.list("SOURCE_DB", [])
    source_cluster = env.list("SOURCE_CLUSTER", [])
    dest_kms = env.str("DEST_KMS", "")
    keep_snapshots = env.int("KEEP_SNAPSHOTS", 1)
    target_region = env.str("TARGET_REGION")
    account = env.str("AWS_ACCOUNT")

    # Create clients
    source_client = boto3.client("rds", region_name=source_region)
    target_client = boto3.client("rds", region_name=target_region)

    for name in source_db:
        copy_rds_snapshots(source_client, target_client, source_region, account, name, dest_kms, keep_snapshots)

    for name in source_cluster:
        copy_cluster_snapshots(source_client, target_client, source_region, account, name, dest_kms, keep_snapshots)
