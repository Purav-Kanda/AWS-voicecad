"""Try a tiny request against several Bedrock model IDs and report which ones this account can use.

Usage:
    python scripts/check_bedrock.py                      # tries the built-in list
    python scripts/check_bedrock.py MODEL_ID [MODEL_ID]  # tries the IDs you give

Reads AWS_REGION and the usual AWS credentials (or AWS_BEARER_TOKEN_BEDROCK) from the environment.
Each call asks for at most 10 tokens, so the cost is negligible.
"""
import os
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# IDs taken from the Cross-region inference page of one account. Yours may list more or fewer.
DEFAULTS = [
    "global.amazon.nova-2-lite-v1:0",
    "global.anthropic.claude-haiku-5-5",
    "global.anthropic.claude-sonnet-5-5",
    "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "global.anthropic.claude-opus-4-8",
    "global.anthropic.claude-opus-5",
]

region = os.environ.get("AWS_REGION", "us-east-2")
client = boto3.client("bedrock-runtime", region_name=region)
ids = sys.argv[1:] or DEFAULTS
print(f"region: {region}")

worked = []
for model_id in ids:
    try:
        reply = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": "Say OK."}]}],
            inferenceConfig={"maxTokens": 10},
        )
        text = reply["output"]["message"]["content"][0].get("text", "").strip()
        print(f"WORKS   {model_id}  (replied: {text!r})")
        worked.append(model_id)
    except (ClientError, BotoCoreError) as err:
        print(f"FAILS   {model_id}\n        {str(err)[:220]}")

print()
if worked:
    print("Use one of these:")
    print(f'  $env:VOICECAD_MODEL_ID="{worked[0]}"')
else:
    print("None worked. Paste the output above.")
