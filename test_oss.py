
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
    cols = aoss.list_collections(collectionFilters={'name': collection_name})['collectionSummaries']
    if not cols: return None
    return aoss.batch_get_collection(ids=[cols[0]['id']])['collectionDetails'][0]

info = get_collection_info()
endpoint = info['collectionEndpoint']
print(f"Endpoint: {endpoint}")

# Test simple GET
print("Testing GET / ...")
session = boto3.Session()
credentials = session.get_credentials()

def signed_request(method, url, payload=None):
    request = AWSRequest(method=method, url=url, data=payload, headers={'Content-Type': 'application/json', 'Host': url.split('//')[1].split('/')[0]})
    SigV4Auth(credentials, 'aoss', region).add_auth(request)
    prepared = request.prepare()
    return requests.request(method, prepared.url, data=payload, headers=prepared.headers)

# Test GET
resp = signed_request('GET', f"{endpoint}/")
print(f"GET / Status: {resp.status_code}")
print(f"GET / Response: {resp.text}")

# If GET works, then permissions are likely okay for "Describe", but maybe not "CreateIndex"
if resp.status_code == 200:
    print("GET successful. Attempting to create index...")
    payload = {
        "settings": {"index": {"knn": "true"}},
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {"type": "knn_vector", "dimension": 1024, "method": {"name": "hnsw", "engine": "nmslib", "space_type": "l2"}},
                "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text"},
                "AMAZON_BEDROCK_METADATA": {"type": "text"}
            }
        }
    }
    resp = signed_request('PUT', f"{endpoint}/{index_name}", json.dumps(payload))
    print(f"PUT /{index_name} Status: {resp.status_code}")
    print(f"PUT /{index_name} Response: {resp.text}")
else:
    print("GET failed. Access policy or network issue.")
