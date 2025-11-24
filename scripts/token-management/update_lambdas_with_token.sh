#!/bin/bash
# Update all Lambda functions with fresh Bearer token
# Generated on 2025-11-03

TOKEN="TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrYPR7ZdTrczgYigcaRHxvF4PUl7KCfKcSa/5LTVI9GZGD2xjCQuIIGifYzjbeIG4F9hljoQfRSa4yHgXV4iKYuqyrGhSMR2SSZtZYnMIprKV7PPtLJLXXojLSR83z7CvMj+yU3eijQF2zV/j36DMcly02sUHcU5kr6g6O+gal69chM4ZDylDHUT2nf96l3PWgtNWRjeMxNAyHYPQy6fDnNvhP5rGMq//5qI6u+uhCaqHPSRrDiyr0TshrCqQ6d6g4J4HMSXxptjsabo0yz6lV4GjtV+q+eBeVd2yewwYF2pPvo/7uOpwdkwGzr3sjaNBfbwTLQETna9tPu3VlJXvsZmJ/0pSEkS5CXWUxPdkJgwFcJ96n8t1mhDcqVLquHEtrFVzJgc3PxvfVmLiiJSnXAGXs8bQlToPyNP3y54bLnIe/7ErMnRawjv5mPiDWrQbr2mqanhBHMRKFmCSkhGR0GjY9YU798hHAO+dwws4mNCWH3lcuUMoo22oude4yU5/zJd92nJc4ZCJENv3zeHHAY7l81sfD1CQ6ZWgYaHxXv8S55hQvbygYfD++S/y8Fx+NY6j5P3t5o/1vQDjj7MZ+p1CL/uERprGPUthvIqQrx78hMAgxRDC61Cmp5P7n5LUaIEgkVt4DPOYPn74cPIZJYHz6uUN8KHYO5+c85btKw6Mt13SjTwk4Hm0iYm0U75XU="
CLIENT_ID="09PF05VD"

echo "========================================"
echo "Updating Lambda Functions with Token"
echo "========================================"
echo ""
echo "Token length: ${#TOKEN} characters"
echo "Client ID: $CLIENT_ID"
echo ""

# Update information-actions Lambda
echo "Updating pf-information-actions..."
aws lambda update-function-configuration \
  --function-name pf-information-actions \
  --environment "Variables={USE_MOCK_API=false,ENVIRONMENT=dev,BEARER_TOKEN=$TOKEN,DEFAULT_CLIENT_ID=$CLIENT_ID,LOG_LEVEL=INFO}" \
  --region us-east-1 \
  > /dev/null 2>&1

if [ $? -eq 0 ]; then
  echo "✅ pf-information-actions updated"
else
  echo "❌ Failed to update pf-information-actions"
fi
echo ""

# Update scheduling-actions Lambda
echo "Updating pf-scheduling-actions..."
aws lambda update-function-configuration \
  --function-name pf-scheduling-actions \
  --environment "Variables={USE_MOCK_API=false,ENVIRONMENT=dev,BEARER_TOKEN=$TOKEN,DEFAULT_CLIENT_ID=$CLIENT_ID,LOG_LEVEL=INFO}" \
  --region us-east-1 \
  > /dev/null 2>&1

if [ $? -eq 0 ]; then
  echo "✅ pf-scheduling-actions updated"
else
  echo "❌ Failed to update pf-scheduling-actions"
fi
echo ""

# Update notes-actions Lambda (if it exists)
echo "Updating pf-notes-actions..."
aws lambda update-function-configuration \
  --function-name pf-notes-actions \
  --environment "Variables={USE_MOCK_API=false,ENVIRONMENT=dev,BEARER_TOKEN=$TOKEN,DEFAULT_CLIENT_ID=$CLIENT_ID,LOG_LEVEL=INFO}" \
  --region us-east-1 \
  > /dev/null 2>&1

if [ $? -eq 0 ]; then
  echo "✅ pf-notes-actions updated"
else
  echo "⚠️  pf-notes-actions not found or failed to update"
fi
echo ""

echo "========================================"
echo "Update Complete!"
echo "========================================"
echo ""
echo "Verify the updates:"
echo "  aws lambda get-function-configuration --function-name pf-information-actions --query 'Environment.Variables' --output json"
