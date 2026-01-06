# Troubleshooting EFS Mount Issues

## Common Error
```
ResourceInitializationError: failed to invoke EFS utils commands to set up EFS volumes
mount.nfs4: mount system call failed
```

## Steps to Fix

### 1. Apply Terraform Changes
Make sure you've applied the latest Terraform changes:
```bash
cd multimodal-transcription/terraform
terraform plan
terraform apply
```

This will:
- Create a new EFS security group with NFS (port 2049) ingress rules
- Update EFS mount targets to use the new security group
- Fix the IAM policy for EFS access

### 2. Verify Security Group Configuration

Check that the EFS security group exists and has the correct rules:
```bash
# Get the EFS security group ID
aws ec2 describe-security-groups \
  --profile bci \
  --region us-east-2 \
  --filters "Name=group-name,Values=multimodal-transcription-efs-sg" \
  --query 'SecurityGroups[0].GroupId' \
  --output text

# Verify ingress rules (should allow port 2049 from ECS tasks security group)
aws ec2 describe-security-groups \
  --profile bci \
  --region us-east-2 \
  --group-ids sg-0c68d69c52c6eed43 \
  --query 'SecurityGroups[0].IpPermissions'
```

### 3. Verify EFS Mount Targets

Check that mount targets are using the correct security group:
```bash
# Get EFS file system ID
EFS_ID=$(aws efs describe-file-systems \
  --profile bci \
  --region us-east-2 \
  --query 'FileSystems[?Name==`multimodal-transcription-efs`].FileSystemId' \
  --output text)

# Check mount targets
aws efs describe-mount-targets \
  --profile bci \
  --region us-east-2 \
  --file-system-id $EFS_ID \
  --query 'MountTargets[*].[MountTargetId,SecurityGroups]'
```

### 4. Manual Fix (If Terraform Apply Doesn't Work)

If mount targets are using the wrong security group, update them manually:

```bash
# Get mount target IDs
MOUNT_TARGET_IDS=$(aws efs describe-mount-targets \
  --profile bci \
  --region us-east-2 \
  --file-system-id $EFS_ID \
  --query 'MountTargets[*].MountTargetId' \
  --output text)

# Get EFS security group ID
EFS_SG_ID=$(aws ec2 describe-security-groups \
  --profile bci \
  --region us-east-2 \
  --filters "Name=group-name,Values=multimodal-transcription-efs-sg" \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Update each mount target
for MT_ID in $MOUNT_TARGET_IDS; do
  aws efs modify-mount-target-security-groups \
    --profile bci \
    --region us-east-2 \
    --mount-target-id $MT_ID \
    --security-groups $EFS_SG_ID
done
```

### 5. Verify IAM Permissions

Check that the execution role has EFS permissions:
```bash
aws iam get-role-policy \
  --profile bci \
  --role-name multimodal-transcription-batch-task-execution-role \
  --policy-name multimodal-transcription-batch-task-execution-efs
```

### 6. Check ECS Task Logs

View the ECS task logs for more details:
```bash
aws logs tail /ecs/multimodal-transcription-batch \
  --profile bci \
  --region us-east-2 \
  --follow
```

## Common Issues

1. **Security Group Not Applied**: The EFS security group must exist and allow NFS traffic from the ECS tasks security group
2. **Mount Targets Using Wrong SG**: Mount targets must use the EFS security group, not the ECS tasks security group
3. **IAM Policy Issues**: The execution role must have EFS permissions with correct access point ARNs
4. **Network Connectivity**: Ensure ECS tasks and EFS mount targets are in the same VPC and subnets

## Verification Checklist

- [ ] EFS security group exists with NFS (port 2049) ingress from ECS tasks SG
- [ ] EFS mount targets use the EFS security group
- [ ] Execution role has EFS IAM policy with correct access point ARNs
- [ ] EFS file system exists and is accessible
- [ ] ECS tasks are in the same VPC as EFS mount targets
- [ ] Terraform changes have been applied

