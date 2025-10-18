# EFS Restore Directory Mover

This project provides a CloudFormation stack with a Lambda function to automatically move contents from AWS Backup restore directories to the root of an EFS filesystem.

## Overview

When you restore an EFS filesystem from AWS Backup, it creates a restore directory named `aws-backup-restore_<datetime>`. This solution provides an automated way to move all contents from this restore directory to the root of the EFS filesystem, preserving permissions and attributes.

## Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.13 with boto3 installed
- EFS filesystem with mount targets accessible from the specified subnet
- Security group configured for NFS access (port 2049)
- Subnet with access to EFS mount targets
