
import boto3
import json
import time

region = 'eu-central-1'
kb_name = 'TacMed_KB'
role_arn = 'arn:aws:iam::168705873426:role/TacMed_KB_Role'
# FIXED: aoss instead of aps
collection_arn = 'arn:aws:aoss:eu-central-1:168705873426:collection/afudncxh7dwboy26600d'

bedrock = boto3.client('bedrock-agent', region_name=region)

kb_config = {
    "type": "VECTOR",
    "vectorKnowledgeBaseConfiguration": {
        "embeddingModelArn": f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0"
    }
}

storage_config = {
    "type": "OPENSEARCH_SERVERLESS",
    "opensearchServerlessConfiguration": {
        "collectionArn": collection_arn,
        "vectorIndexName": "bedrock-knowledge-base-default-index",
        "fieldMapping": {
            "vectorField": "bedrock-knowledge-base-default-vector",
            "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
            "metadataField": "AMAZON_BEDROCK_METADATA"
        }
    }
}

try:
    print(f"Creating Knowledge Base {kb_name}...")
    response = bedrock.create_knowledge_base(
        name=kb_name,
        roleArn=role_arn,
        knowledgeBaseConfiguration=kb_config,
        storageConfiguration=storage_config
    )
    kb_id = response['knowledgeBase']['knowledgeBaseId']
    print(f"Successfully created KB: {kb_id}")
    
    # Save to file
    with open('kb_id.txt', 'w') as f:
        f.write(kb_id)
        
except Exception as e:
    print(f"Error creating KB: {e}")
    # Check if already exists
    try:
        kbs = bedrock.list_knowledge_bases()['knowledgeBaseSummaries']
        for kb in kbs:
            if kb['name'] == kb_name:
                print(f"Found existing KB: {kb['knowledgeBaseId']}")
                with open('kb_id.txt', 'w') as f:
                    f.write(kb['knowledgeBaseId'])
    except:
        pass
