import json
import boto3
import base64
import os
from datetime import datetime

# Initialize clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime') # For knowledge base
bedrock_runtime = boto3.client('bedrock-runtime') # For quiz generation
transcribe = boto3.client('transcribe')
dynamodb = boto3.resource('dynamodb')

USERS_TABLE = os.environ.get('USERS_TABLE', 'TacMed_Users')
HISTORY_TABLE = os.environ.get('HISTORY_TABLE', 'TacMed_History')
# KB_ID = os.environ.get('KB_ID') # TODO: Configure Knowledge Base ID
s3 = boto3.client('s3')

def get_kb_bucket():
    # Priority: Env Var -> Discovery
    env_bucket = os.environ.get('KB_BUCKET')
    print(f"DEBUG: Env Bucket: {env_bucket}")
    if env_bucket:
        return env_bucket
        
    # Find bucket starting with tacmed-kb-
    try:
        buckets = s3.list_buckets().get('Buckets', [])
        for b in buckets:
            if b['Name'].startswith('tacmed-kb-'):
                return b['Name']
    except Exception as e:
        print(f"Bucket Discovery Error: {e}")
    return None

def lambda_handler(event, context):
    print("Event:", json.dumps(event))
    
    path = event.get('rawPath')
    http_method = event.get('requestContext', {}).get('http', {}).get('method')
    
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization'
    }
    
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
        
    try:
        if path == '/ask' and http_method == 'POST':
            return handle_ask(event, headers)
        elif path == '/quiz' and http_method == 'POST':
            return handle_quiz(event, headers)
        elif path == '/leaderboard' and http_method == 'GET':
            return handle_leaderboard(headers)
        else:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'Not Found'})}
    except Exception as e:
        print("Error:", str(e))
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def handle_ask(event, headers):
    try:
        body = json.loads(event.get('body', '{}'))
        if not body:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Body required'})}

        question = body.get('question')
        audio_data = body.get('audio')
        
        if audio_data:
            # Handle audio transcription
            try:
                bucket_name = get_kb_bucket()
                if not bucket_name:
                    raise Exception("Storage bucket not found")
                    
                # Decode and save to /tmp
                audio_bytes = base64.b64decode(audio_data)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                file_name = f"audio_{timestamp}.webm"
                s3_key = f"audio-temp/{file_name}"
                
                # Upload to S3
                s3.put_object(Bucket=bucket_name, Key=s3_key, Body=audio_bytes)
                
                # Start Transcription
                job_name = f"Transcribe_{timestamp}"
                media_uri = f"s3://{bucket_name}/{s3_key}"
                
                transcribe.start_transcription_job(
                    TranscriptionJobName=job_name,
                    Media={'MediaFileUri': media_uri},
                    MediaFormat='webm',
                    LanguageCode='en-US'
                )
                
                # Polling for completion (Max 20 seconds for prototype)
                import time
                max_retries = 20
                for _ in range(max_retries):
                    status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
                    job_status = status['TranscriptionJob']['TranscriptionJobStatus']
                    if job_status in ['COMPLETED', 'FAILED']:
                        break
                    time.sleep(1)
                
                if job_status == 'COMPLETED':
                    transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    import urllib.request
                    with urllib.request.urlopen(transcript_uri) as url:
                        data = json.loads(url.read().decode())
                        # Check if transcripts exist
                        if data['results']['transcripts']:
                            question = data['results']['transcripts'][0]['transcript']
                            print(f"DEBUG: Transcribed text: '{question}'")
                        else:
                            print("DEBUG: Empty transcript")
                            question = ""
                            
                        if not question:
                             return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'answer': "Radio check. converting... I heard nothing. Please check your microphone."})}
                else:
                    raise Exception("Transcription timed out or failed")
                    
            except Exception as e:
                print(f"Transcribe Error: {e}")
                return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'answer': f"Voice Systems Offline: {str(e)} (Check logs)"})}

        if not question:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Question required'})}
            
        # RAG Logic: Use Bedrock's retrieve_and_generate with the TCCC Guidelines PDF in S3
        bucket_name = get_kb_bucket()
        if not bucket_name:
             return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'answer': "Storage error: KB bucket not found."})}
             
        s3_uri = f"s3://{bucket_name}/clinical-guidelines-2024-ua.pdf"
        
        # Use regional model ID as base for ARN
        region = 'eu-central-1'
        # Note: EXTERNAL_SOURCES is a cost-effective way to do RAG on small sets of files
        model_arn = f"arn:aws:bedrock:{region}::foundation-model/meta.llama3-2-3b-instruct-v1:0"
        
        try:
            response = bedrock_agent_runtime.retrieve_and_generate(
                input={'text': question},
                retrieveAndGenerateConfiguration={
                    'type': 'EXTERNAL_SOURCES',
                    'externalSourcesConfiguration': {
                        'modelArn': model_arn,
                        'sources': [
                            {
                                'sourceType': 'S3',
                                's3Location': {
                                    'uri': s3_uri
                                }
                            }
                        ]
                    }
                }
            )
            answer = response['output']['text']
        except Exception as rag_err:
            print(f"RAG Error (External Sources): {rag_err}")
            # Fallback to direct invocation if RAG fails (e.g. region lack of support)
            system_prompt = """You are an expert TCCC AI Assistant. 
Answer in the same language as the user. If they ask about 'турнікет', they mean medical tourniquet.
Respond concisely but accurately based on TCCC standards."""
            
            final_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>
{question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

            fallback_resp = bedrock_runtime.invoke_model(
                modelId='eu.meta.llama3-2-3b-instruct-v1:0',
                body=json.dumps({
                    "prompt": final_prompt,
                    "max_gen_len": 512,
                    "temperature": 0.5,
                    "top_p": 0.9
                })
            )
            answer = json.loads(fallback_resp.get('body').read())['generation']
        
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'answer': answer})}
        
    except Exception as e:
        print(f"Error in ask: {e}")
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'answer': f"HQ Offline: {str(e)}"})}

def handle_quiz(event, headers):
    try:
        # Prompt for TCCC scenario generation (Llama 3 Format)
        system_prompt = "You are an expert military medical instructor teaching Tactical Combat Casualty Care (TCCC)."
        user_prompt = """Generate a multiple-choice quiz question based on standard TCCC protocols (MARCH-PAWS).
        Return purely JSON with the following structure:
        {
            "question": "The scenario text...",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_index": 0,
            "explanation": "Why this is the correct answer."
        }
        Do not output any markdown formatting, just the raw JSON string."""
        
        final_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>
{user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

        body = json.dumps({
            "prompt": final_prompt,
            "max_gen_len": 1000,
            "temperature": 0.5,
            "top_p": 0.9
        })

        # Invoke Llama 3 8B
        model_id = 'us.meta.llama3-2-3b-instruct-v1:0'
        
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=body
        )
        
        response_body = json.loads(response.get('body').read())
        content_text = response_body['generation']
        
        # Parse JSON from model output (handling potential mardown wrapper)
        clean_json = content_text.strip()
        if clean_json.startswith('```json'):
            clean_json = clean_json.split('```json')[1].split('```')[0].strip()
        elif clean_json.startswith('```'):
            clean_json = clean_json.split('```')[1].split('```')[0].strip()
            
        quiz_data = json.loads(clean_json)
        
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps(quiz_data)}
        
    except Exception as e:
        print(f"Bedrock Error: {e}")
        # Fallback for demo purposes if Bedrock fails or permissions issue
        fallback_quiz = {
            "question": "Fallback: During Care Under Fire, what is the only medically indicated intervention?",
            "options": ["Airway management", "Tourniquet application", "Needle decompression", "IV access"],
            "correct_index": 1,
            "explanation": "Hemorrhage control via tourniquet is the only approved intervention in CUF."
        }
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps(fallback_quiz)}

def handle_leaderboard(headers):
    table = dynamodb.Table(USERS_TABLE)
    try:
        # Scan or Query based on GSI
        # For simplicity in prototype, using scan (requires optimization for production)
        response = table.scan(
            IndexName='TotalScoreIndex',
            Limit=10,
            ProjectionExpression='UserId, TotalScore'
        )
        items = response.get('Items', [])
        # Sort manually if Scan doesn't sort by GSI (Scan doesn't sort)
        items.sort(key=lambda x: int(x.get('TotalScore', 0)), reverse=True)
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'leaderboard': items})}
    except Exception as e:
        print("DB Error:", e)
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': 'Database error'})}
