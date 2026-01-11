
import boto3
import json

region = 'eu-central-1'
policy_name = 'tacmed-kb-4850-access'
kb_role_arn = "arn:aws:iam::168705873426:role/TacMed_KB_Role"
user_arn = "arn:aws:iam::168705873426:user/roman-dev"
root_arn = "arn:aws:iam::168705873426:root"

aoss = boto3.client('opensearchserverless', region_name=region)

policy = [
    {
        "Rules": [
            {
                "ResourceType": "collection",
                "Resource": ["collection/tacmed-kb-4850"],
                "Permission": [
                    "aoss:CreateCollectionItems",
                    "aoss:DeleteCollectionItems",
                    "aoss:UpdateCollectionItems",
                    "aoss:DescribeCollectionItems"
                ]
            },
            {
                "ResourceType": "index",
                "Resource": ["index/tacmed-kb-4850/*"],
                "Permission": [
                    "aoss:CreateIndex",
                    "aoss:DeleteIndex",
                    "aoss:UpdateIndex",
                    "aoss:DescribeIndex",
                    "aoss:ReadDocument",
                    "aoss:WriteDocument"
                ]
            }
        ],
        "Principal": [kb_role_arn, user_arn, root_arn]
    }
]

# Get current version
current = aoss.get_access_policy(name=policy_name, type='data')
version = current['accessPolicyDetail']['policyVersion']

print(f"Updating policy {policy_name} (version {version}) with root...")
response = aoss.update_access_policy(
    name=policy_name,
    type='data',
    policyVersion=version,
    policy=json.dumps(policy)
)
print("Policy updated.")
