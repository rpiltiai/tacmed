
import boto3
import requests
import json
import time
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

region = 'eu-central-1'
collection_name = 'tacmed-kb-4850'
index_name = 'bedrock-knowledge-base-default-index'

aoss = boto3.client('opensearchserverless', region_name=region)

def get_collection_info():
    collections = aoss.list_collections(
        collectionFilters={'name': collection_name}
    )['collectionSummaries']
    if not collections:
        return None
    
    col_id = collections[0]['id']
    details = aoss.batch_get_collection(ids=[col_id])['collectionDetails']
    return details[0] if details else None

def create_index(endpoint):
    url = f"{endpoint}/{index_name}"
    
    # Bedrock Knowledge Base requirements for Titan Text Embeddings v2
    # Default dimension for Titan Text V2 is 1024
    payload = {
        "settings": {
            "index": {
                "knn": "true",
                "knn.algo_param.ef_search": "512"
            }
        },
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {
                        "name": "hnsw",
                        "engine": "nmslib",
                        "parameters": {
                          "ef_construction": 512,
                          "m": 16
                        },
                        "space_type": "l2"
                    }
                },
                "AMAZON_BEDROCK_TEXT_CHUNK": {
                    "type": "text"
                },
                "AMAZON_BEDROCK_METADATA": {
                    "type": "text"
                }
            }
        }
    }
    
    session = boto3.Session()
    credentials = session.get_credentials()
    
    request = AWSRequest(method='PUT', url=url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
    SigV4Auth(credentials, 'aoss', region).add_auth(request)
    
    prepared = request.prepare()
    response = requests.put(prepared.url, data=payload if isinstance(payload, str) else json.dumps(payload), headers=prepared.headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    return response.status_code

print(f"Waiting for collection {collection_name} to be ACTIVE...")
while True:
    info = get_collection_info()
    if info and info['status'] == 'ACTIVE':
        print("Collection is ACTIVE.")
        endpoint = info['collectionEndpoint']
        break
    print(f"Current Status: {info['status'] if info else 'Unknown'}. Retrying in 10s...")
    time.sleep(10)

print(f"Creating index {index_name} at {endpoint}...")
create_index(endpoint)
