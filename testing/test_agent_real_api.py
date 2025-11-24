import boto3
import json
import time

BEARER_TOKEN = "TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrYPR7ZdTrczgYigcaRHxvF4JIl7HafKfQQ/5IXVFFOZGD24PcJ3isGqpYzN+uMG9LwX3zevOY4i7jfXVJeKhA83l8EAnSQoGAfs4Il2H1/nGJ0m6byLfHipQQspeniEUWv73/wLlix6WCRipde4gabtEcdA1rBUHjUbG/Cmjrmpp4ZcXQF/T38ZY87nB5y+j1C59FQwyXNJ1t1I9tx//k1j9I7UKzr7MxxyBOEAcIqjUIkLJ7e5H0BGyKo7izbkKzJXEG6yC+mJErpfLHUM7NiD0wBWepfpmQ0qj9F4XaU7OPrEJd63yXHOMOjIJfU2aSI5Oho5b9eBlsXncK0Xzz1DonOugjanXt3EgigX9P+aAWX689K0upI2Kw9L32uvxYEVimFBNvmC2De6m8ptBMa++Rc0NZeWM4E7nJNOPtdanPxGG/quK2uoKxQLQleMat1DyM+JF6SByik/d7vXLmf4jSRrDjoc1rj+dGDxAkGrD5z58bPwhp0E4S7yXpRwB+xNz5YuA7VyPH3A8wjJjyR3tCg4ChencrCgtfbqFpswnpHRuwA6HyRkeLZRGgeVSgScMTA1oiFV5sQK93M8TD6UY7PCm3vQLgWkFTXD5yh0yd6Y04BwYc5FY5i3+OuQAvPvwFAUM7De+10OfunP86VYhS+jiOvEVHb40UxdIcZkK0tkwazyFqGiKy1nCZDUVoRtOogejrPMETjXsQ0ECBP"
CUSTOMER_ID = "1645869"
CLIENT_ID = "09PF05VD"
AGENT_ID = "TIGRBGSXCS"
ALIAS_ID = "TSTALIASID"
REGION = "us-east-1"

bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)

session_attributes = {
    'customer_id': CUSTOMER_ID,
    'client_id': CLIENT_ID,
    'client_name': 'ProjectForce User',
    'customer_type': 'B2C',
    'pf_bearer_token': BEARER_TOKEN,
    'pf_api_base': 'https://api-cx-portal.dev.projectsforce.com'
}

input_text = f"""Session Context:
- Customer ID: {CUSTOMER_ID}
- Client ID: {CLIENT_ID}
- Client Name: ProjectForce User
- Customer Type: B2C

User Request: Show me all my projects

Please help the customer with their request using their customer ID and client ID for any actions."""

print(f"✅ Testing Scheduling Agent with FRESH TOKEN")
print(f"   Customer ID: {CUSTOMER_ID}")
print(f"   Input: {input_text}")
print(f"   Token works: Verified 25 projects via CURL\n")
print("🚀 Invoking agent...\n")

try:
    response = bedrock_agent_runtime.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=ALIAS_ID,
        sessionId=f"test-fresh-{int(time.time())}",
        inputText=input_text,
        enableTrace=True,
        sessionState={
            'sessionAttributes': session_attributes
        }
    )

    full_response = ""
    lambda_invoked = False
    lambda_response = None

    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                decoded = chunk['bytes'].decode('utf-8')
                full_response += decoded
        elif 'trace' in event:
            trace = event['trace']
            if 'trace' in trace and 'orchestrationTrace' in trace['trace']:
                orch = trace['trace']['orchestrationTrace']
                if 'invocationInput' in orch:
                    lambda_invoked = True
                    inv_input = orch['invocationInput']
                    if 'actionGroupInvocationInput' in inv_input:
                        action_input = inv_input['actionGroupInvocationInput']
                        print(f"✅ Lambda Invoked!")
                        print(f"   Action Group: {action_input.get('actionGroupName')}")
                        print(f"   API Path: {action_input.get('apiPath')}")
                if 'observation' in orch:
                    obs = orch['observation']
                    if 'actionGroupInvocationOutput' in obs:
                        print(f"\n📥 Lambda Response:")
                        output = obs['actionGroupInvocationOutput']
                        text = output.get('text', 'N/A')
                        lambda_response = text
                        if len(text) > 300:
                            print(f"   Text: {text[:300]}... [{len(text)} chars total]")
                        else:
                            print(f"   Text: {text}")

    print(f"\n📊 Results:")
    print(f"   Lambda Invoked: {'✅ YES' if lambda_invoked else '❌ NO'}")
    print(f"   Response Length: {len(full_response)} chars")
    print(f"\n💬 Agent Response:")
    print(full_response)

    if lambda_response:
        try:
            data = json.loads(lambda_response)
            if 'projects' in data:
                print(f"\n🎉 SUCCESS! Got {len(data['projects'])} projects from REAL API!")
                print(f"\nFirst 3 projects:")
                for i, proj in enumerate(data['projects'][:3], 1):
                    print(f"  {i}. {proj.get('project_name', 'N/A')} (ID: {proj.get('project_id', 'N/A')})")
        except:
            pass

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
