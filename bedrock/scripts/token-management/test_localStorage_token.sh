#!/bin/bash

# Test the access token from browser localStorage
# Token extracted from browser on 2025-11-03

API_URL="https://api-cx-portal.dev.projectsforce.com"
CLIENT_ID="09PF05VD"
CUSTOMER_ID="1645869"

# Token from localStorage
ACCESS_TOKEN="TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrY7E+JahPgJItOT1TeHzuFkKBZdKtH+Wm0nfNKp1Y6TR19FBC75H98jk3wtxyLeaKzcyIf+P98RcFLNju88pa7HuqtNdWiLW5cbC9xpuLYWDvpoHyQnNNbxw7BzOaRr/r7dOTbOkoDpNNm6AdtlwjTkTFGyDwY8ww9NUi7Y4PasyWS8w7REIcMG+mWqKu8p4k8NCRmbAhLgxqnp/ybcKHdQyy9CDahS2v1stGYZjwnRlEiXMBNEy8AxrMOAXYz/T4B+/vPzKF+p8Kdmjv9kuPjAOkNVnNIPuwqudsuIsjykgLJyB1yxMR2tgyS1Wp+7fuxCocy9+Nh7ZgvCBV9Rudk5jdANOA4GRBL8Dc68DntOQa2Sr4Z9JfRk/s0z8L/UdAv7Gp+UdX9aB+0BNXkv7uRUHM8weK7ZppN2Ur3pwZgc8VCIbLERjBkAZpaSGmyyWwM5X+TYKGwu27ps+XY8jnJM5u6lSZcKcF7SeOJc8IuX51Zc+tNr8uKR190xHI6wFUD2aSvq6sNXMDSomat+uo9+bs+WN+IHfiskYbJumDrFfTpN2o9SDVZtD8w1SiJFUSRglomQ9rQ/hwu1AIQNTyVu6f43/KxAbMvhXVcLB7cvEi/JrS4eF8Uz7zVNZK1IPdv8WU3p47SlAxfG/8dh5bF/bqfYEsBmHuzdDZWQ64q04HDn9kQ8O3FLZiKL8wN5iGMXt8hTZs3Xfz7xrjqT6du304Z/bfctLxPtu5/FMDtH37T9rbG7Lg3qriDu/v7HFrxCIp2p2YzlNl5OiyRTuEuSTY8sbp1PZzqpZSOHW4h2vfHNZXpH6jEXc9noe2gIb0inT/fC+AvXMmBTeQ1ItuBOdWyTtCpmIE9ydZHkg13l/lgab9PRBJ1RRuHH1dV4G+9+Si3NLysAwTQY2pjq8xYzosr12MkRqGdhlMCZ06OBzI4zDPFxo5lDyFMufA1tzkCaAc551vho6qxesALj72/0XwrKMI1aVi5D53c48cUmReg6Ypd/NBKFtwC/pcrMQj/S2t2dbkF3e9xrJNgaE+Z"

echo "========================================="
echo "Testing Token from Browser localStorage"
echo "========================================="
echo "Token expires: 1762189160 (Unix timestamp)"
echo "Current time: $(date +%s)"
echo ""

# Calculate if token is still valid
EXPIRY=1762189160
CURRENT=$(date +%s)
REMAINING=$((EXPIRY - CURRENT))

if [ $REMAINING -gt 0 ]; then
    HOURS=$((REMAINING / 3600))
    echo "✓ Token is still valid for $HOURS hours"
else
    echo "✗ Token has expired!"
    exit 1
fi

echo ""
echo "Testing Dashboard API..."
echo ""

RESPONSE=$(curl -s -X GET "$API_URL/dashboard/get/$CLIENT_ID/$CUSTOMER_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json")

# Check if we got data
PROJECT_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data', [])))" 2>/dev/null)

if [ ! -z "$PROJECT_COUNT" ] && [ "$PROJECT_COUNT" != "0" ]; then
    echo "✓ SUCCESS! Token is working!"
    echo "✓ Found $PROJECT_COUNT projects"
    echo ""
    echo "First project:"
    echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); p=data.get('data', [{}])[0]; print(f\"  ID: {p.get('id')}\"); print(f\"  Order: {p.get('order_number')}\"); print(f\"  Category: {p.get('category')}\"); print(f\"  Status: {p.get('status')}\")" 2>/dev/null
    echo ""

    # Save response
    echo "$RESPONSE" | python3 -m json.tool > localStorage_token_test_response.json 2>/dev/null
    echo "✓ Full response saved to: localStorage_token_test_response.json"
else
    echo "✗ FAILED! Token not working or expired"
    echo ""
    echo "Response:"
    echo "$RESPONSE"
fi

echo ""
echo "========================================="
echo "Next Steps:"
echo "========================================="
echo ""
echo "The token from localStorage is working!"
echo ""
echo "To update Lambda with this token:"
echo ""
echo "  ./update_lambda_token.sh \"$ACCESS_TOKEN\""
echo ""
