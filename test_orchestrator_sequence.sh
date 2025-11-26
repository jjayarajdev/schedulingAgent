#!/bin/bash
SESSION="voice-seq-test-$(date +%s)"
TOKEN="TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrYPR7ZdTrczgYigcaRHxvF4PUl7KCfKcSa/5LTVI9GZGD2xjCQuIIGifYzjbeIG4F9hljoQfRSa4yHgXV4iKYuqyrGhSMR2SSZtZYnMIprKV5KJRBHQXWOYrSRPMv7ChrMdiVSwy1MO6JOQB8KxSPXXKr67qF7ksV03kD5hYArIZYjeyy19NJcnL1W023ZFudJ6mtzl4wvPOnsddTyPERJsiXHMN8yY5w1o3xNlwr8DHTPIyAqiu5yW5+QhygaNJzyVaa17Yb/GgRxqPrKFI1IXkIlvGGvVmao0nAhYHfgwnVe/WJ39G1kmXWxs8vDB4XYNx2967IpI2J507Ku91i757vsVOQ0yZgVerZDeDi8HK5AKExtynD9+4Mi+DtIBjFoCu31ewM762XzanR/GK3TTEUVXATINTcx+V6XRzP5t7JknIrtCHo/s0PtfKs2qjW5Pz17c5KwjHjLeb6KWzSraLR1PhqnOf3AdziZLbyXPXt+U49/+uZbXC1y5/od+6w21aLhb6+4h9SofJzE1+zbz0YmXnWm4EvVGbkuQmwtQkaH6QWCzy99RnwQya3DDPO37IQijZbz0Y89njHdyAILi3gDTA9N7e3OmYliRsIqnRF76JECjRu3VNODN3USbCv36tXAKec2JFD1Pj4a676FN4ECtYM6v8gzXQpQUArzZ9D+/u/nnOZBUf77bLGKibE="

echo "=========================================="
echo "TEST SEQUENCE: Voice Integration"
echo "Session: $SESSION"
echo "=========================================="
echo ""

# Test 1: List my projects
echo "=== 1. List my projects ==="
aws lambda invoke --function-name pf-orchestrator --payload "{\"body\": \"{\\\"message\\\": \\\"List all my projects\\\", \\\"session_id\\\": \\\"$SESSION\\\", \\\"pf_token\\\": \\\"$TOKEN\\\", \\\"pf_client_id\\\": \\\"09PF05VD\\\", \\\"pf_user_id\\\": \\\"1646085\\\"}\"}" result1.json > /dev/null
cat result1.json | python -m json.tool | grep -A 2 '"response"' | head -5
echo ""
sleep 2

# Test 2: Details of first project
echo "=== 2. Give me details of first project ==="
aws lambda invoke --function-name pf-orchestrator --payload "{\"body\": \"{\\\"message\\\": \\\"Give me details of the first project\\\", \\\"session_id\\\": \\\"$SESSION\\\", \\\"pf_token\\\": \\\"$TOKEN\\\", \\\"pf_client_id\\\": \\\"09PF05VD\\\", \\\"pf_user_id\\\": \\\"1646085\\\"}\"}" result2.json > /dev/null
cat result2.json | python -m json.tool | grep -A 2 '"response"' | head -5
echo ""
sleep 2

# Test 3: Who is the technician
echo "=== 3. Who is the technician of this project ==="
aws lambda invoke --function-name pf-orchestrator --payload "{\"body\": \"{\\\"message\\\": \\\"Who is the technician for this project\\\", \\\"session_id\\\": \\\"$SESSION\\\", \\\"pf_token\\\": \\\"$TOKEN\\\", \\\"pf_client_id\\\": \\\"09PF05VD\\\", \\\"pf_user_id\\\": \\\"1646085\\\"}\"}" result3.json > /dev/null
cat result3.json | python -m json.tool | grep -A 2 '"response"' | head -5
echo ""
sleep 2

# Test 4: Do I have appointments
echo "=== 4. Do I have any appointments ==="
aws lambda invoke --function-name pf-orchestrator --payload "{\"body\": \"{\\\"message\\\": \\\"Do I have any appointments\\\", \\\"session_id\\\": \\\"$SESSION\\\", \\\"pf_token\\\": \\\"$TOKEN\\\", \\\"pf_client_id\\\": \\\"09PF05VD\\\", \\\"pf_user_id\\\": \\\"1646085\\\"}\"}" result4.json > /dev/null
cat result4.json | python -m json.tool | grep -A 2 '"response"' | head -5
echo ""
sleep 2

# Test 5: Weather tomorrow
echo "=== 5. What's the weather tomorrow ==="
aws lambda invoke --function-name pf-orchestrator --payload "{\"body\": \"{\\\"message\\\": \\\"Whats the weather tomorrow\\\", \\\"session_id\\\": \\\"$SESSION\\\", \\\"pf_token\\\": \\\"$TOKEN\\\", \\\"pf_client_id\\\": \\\"09PF05VD\\\", \\\"pf_user_id\\\": \\\"1646085\\\"}\"}" result5.json > /dev/null
cat result5.json | python -m json.tool | grep -A 2 '"response"' | head -5

echo ""
echo "=========================================="
echo "SEQUENCE TEST COMPLETE"
echo "=========================================="
