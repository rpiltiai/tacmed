import boto3
import json
import traceback

client = boto3.client('bedrock-runtime', region_name='eu-central-1')

body = json.dumps({
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]
})

try:
    response = client.invoke_model(
        modelId='anthropic.claude-3-haiku-20240307-v1:0',
        body=body
    )
    print("Success")
    print(response['body'].read())
except Exception:
    traceback.print_exc()
