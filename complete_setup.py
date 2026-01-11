
import boto3
import json
import time
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

region = 'eu-central-1'
collection_name = 'tacmed-rag-v3' # New name just in case
index_name = 'bedrock-knowledge-base-default-index'
kb_name = 'TacMed_KB_V3'
role_arn = 'arn:aws:iam::168705873426:role/TacMed_KB_Role'
user_arn = 'arn:aws:iam::168705873426:user/roman-dev'
s3_bucket = 'tacmed-kb-4850'

aoss = boto3.client('opensearchserverless', region_name=region)
bedrock = boto3.client('bedrock-agent', region_name=region)

def setup_oss():
    print(f"Setting up OSS Collection: {collection_name}")
    
    # 1. Encryption Policy
    enc_name = f"{collection_name}-enc"
    try:
        aoss.create_security_policy(
            name=enc_name,
            type='encryption',
            policy=json.dumps({
                "Rules": [{"ResourceType": "collection", "Resource": [f"collection/{collection_name}"]}],
                "AWSOwnedKey": True
            })
        )
        print("Encryption policy created.")
    except aoss.exceptions.ConflictException:
        print("Encryption policy already exists.")

    # 2. Network Policy
    net_name = f"{collection_name}-net"
    try:
        aoss.create_security_policy(
            name=net_name,
            type='network',
            policy=json.dumps([{
                "Rules": [
                    {"ResourceType": "collection", "Resource": [f"collection/{collection_name}"]},
                    {"ResourceType": "dashboard", "Resource": [f"collection/{collection_name}"]}
                ],
                "AllowFromPublic": True
            }])
        )
        print("Network policy created.")
    except aoss.exceptions.ConflictException:
        print("Network policy already exists.")

    # 3. Access Policy
    acc_name = f"{collection_name}-access"
    try:
        aoss.create_access_policy(
            name=acc_name,
            type='data',
            policy=json.dumps([{
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{collection_name}"],
                        "Permission": ["aoss:*"]
                    },
                    {
                        "ResourceType": "index",
                        "Resource": [f"index/{collection_name}/*"],
                        "Permission": ["aoss:*"]
                    }
                ],
                "Principal": [role_arn, user_arn]
            }])
        )
        print("Access policy created.")
    except aoss.exceptions.ConflictException:
        print("Access policy already exists.")

    # 4. Collection
    try:
        resp = aoss.create_collection(name=collection_name, type='VECTORSEARCH')
        col_id = resp['createCollectionDetail']['id']
        print(f"Collection creation initiated: {col_id}")
    except aoss.exceptions.ConflictException:
        col_id = aoss.list_collections(collectionFilters={'name': collection_name})['collectionSummaries'][0]['id']
        print(f"Using existing collection: {col_id}")

    # Wait for ACTIVE
    print("Waiting for collection to be ACTIVE...")
    while True:
        status = aoss.batch_get_collection(ids=[col_id])['collectionDetails'][0]
        if status['status'] == 'ACTIVE':
            print("Collection is ACTIVE.")
            return status['collectionEndpoint'], status['arn']
        print(f"Status: {status['status']}. Waiting 10s...")
        time.sleep(10)

def create_index(endpoint):
    print(f"Creating index {index_name}...")
    url = f"{endpoint}/{index_name}"
    payload = {
        "settings": {"index": {"knn": "true"}},
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {"name": "hnsw", "engine": "nmslib", "space_type": "l2"}
                },
                "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text"},
                "AMAZON_BEDROCK_METADATA": {"type": "text"}
            }
        }
    }
    
    session = boto3.Session()
    credentials = session.get_credentials()
    request = AWSRequest(method='PUT', url=url, data=json.dumps(payload), headers={'Content-Type': 'application/json', 'Host': url.split('//')[1].split('/')[0]})
    SigV4Auth(credentials, 'aoss', region).add_auth(request)
    prepared = request.prepare()
    
    # Retry loop for index creation (permissions propagation delay)
    for i in range(10):
        resp = requests.put(prepared.url, data=json.dumps(payload), headers=prepared.headers)
        if resp.status_code in [200, 201]:
            print("Index created successfully.")
            return True
        print(f"Attempt {i+1} failed ({resp.status_code}). Retrying in 15s...")
        time.sleep(15)
    return False

def setup_kb(col_arn):
    print(f"Setting up Knowledge Base: {kb_name}")
    try:
        resp = bedrock.create_knowledge_base(
            name=kb_name,
            roleArn=role_arn,
            knowledgeBaseConfiguration={
                "type": "VECTOR",
                "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0"
                }
            },
            storageConfiguration={
                "type": "OPENSEARCH_SERVERLESS",
                "opensearchServerlessConfiguration": {
                    "collectionArn": col_arn,
                    "vectorIndexName": index_name,
                    "fieldMapping": {
                        "vectorField": "bedrock-knowledge-base-default-vector",
                        "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
                        "metadataField": "AMAZON_BEDROCK_METADATA"
                    }
                }
            }
        )
        kb_id = resp['knowledgeBase']['knowledgeBaseId']
        print(f"KB created: {kb_id}")
    except bedrock.exceptions.ConflictException:
        kbs = bedrock.list_knowledge_bases()['knowledgeBaseSummaries']
        kb_id = [k['knowledgeBaseId'] for k in kbs if k['name'] == kb_name][0]
        print(f"Using existing KB: {kb_id}")

    # 2. Data Source
    print("Creating Data Source...")
    try:
        resp = bedrock.create_data_source(
            knowledgeBaseId=kb_id,
            name="TacMed_S3_Source",
            dataSourceConfiguration={
                "type": "S3",
                "s3Configuration": {"bucketArn": f"arn:aws:s3:::{s3_bucket}"}
            }
        )
        ds_id = resp['dataSource']['dataSourceId']
        print(f"Data Source created: {ds_id}")
    except bedrock.exceptions.ConflictException:
        dss = bedrock.list_data_sources(knowledgeBaseId=kb_id)['dataSourceSummaries']
        ds_id = [d['dataSourceId'] for d in dss if d['name'] == "TacMed_S3_Source"][0]
        print(f"Using existing Data Source: {ds_id}")

    # 3. Start Sync
    print("Starting Ingestion Job...")
    resp = bedrock.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id)
    print(f"Ingestion Job started: {resp['ingestionJob']['ingestionJobId']}")
    return kb_id

if __name__ == "__main__":
    endpoint, col_arn = setup_oss()
    if create_index(endpoint):
        kb_id = setup_kb(col_arn)
        print(f"FINISH: KB_ID={kb_id}")
    else:
        print("FAILED to create index. Check permissions.")
