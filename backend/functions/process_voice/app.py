import json
import boto3
import uuid
import os
import faiss
import numpy as np

# --- 1. AWS Services Setup ---
bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('SESSIONS_TABLE', 'setu-ai-sessions'))


print("Loading FAISS Database...")
try:
    index = faiss.read_index('schemes_vector_titan.index')
    
    with open('schemes_metadata_titan.json', 'r', encoding='utf-8') as f:
        metadata_list = json.load(f)
except Exception as e:
    print(f"Warning: Database files not found. Error: {e}")


def get_titan_embedding(text):
    body = json.dumps({"inputText": text})
    response = bedrock.invoke_model(
        body=body,
        modelId='amazon.titan-embed-text-v2:0',
        accept='application/json',
        contentType='application/json'
    )
    response_body = json.loads(response.get('body').read())
    return response_body.get('embedding')

def find_best_schemes(user_problem, top_k=3):
    """Searches the database using AWS Titan Embeddings"""
    try:
        vector = get_titan_embedding(user_problem)
        distances, indices = index.search(np.array([vector]).astype('float32'), top_k)
        
        context = ""
       
        for idx in indices[0]:
            if idx == -1: continue 
            row = metadata_list[idx] 
            
            context += f"Scheme Name: {row.get('scheme_name', 'Unknown')}\n"
            context += f"Level (State/Central): {row.get('level', 'N/A')}\n"
            context += f"Category & Tags: {row.get('schemeCategory', '')} | {row.get('tags', '')}\n"
            context += f"Details: {row.get('details', 'N/A')}\n"
            context += f"Benefits: {row.get('benefits', 'N/A')}\n"
            context += f"Eligibility Criteria: {row.get('eligibility', 'N/A')}\n"
            context += f"Documents Required: {row.get('documents', 'N/A')}\n"
            context += f"Application Process: {row.get('application', 'N/A')}\n"
            context += "-" * 50 + "\n\n"
            
        return context
    except Exception as e:
        print(f"Search error: {e}")
        return "Fallback Scheme: Pradhan Mantri Awas Yojana (PMAY)\nEligibility: Below Poverty Line."


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        transcript = body.get('transcript', '') 
        session_id = body.get('session_id', str(uuid.uuid4()))
        language = body.get('language', 'Hindi')
        chat_history = body.get('chat_history', '')

        if not transcript:
            return _build_response(400, {"error": "Transcript is required"})

        # --- 3. Semantic Search ---
        live_db_context = find_best_schemes(transcript)

        # --- 4. The Dynamic RAG Prompt ---
        prompt = f"""
        You are Setu AI, a highly professional, polite, and empathetic government caseworker for citizens in India.
        User's requested language: {language}
        
        PREVIOUS CONVERSATION HISTORY (Use this to remember what the user has ALREADY told you. DO NOT ask for this information again):
        {chat_history}
        
        CURRENT MESSAGE: "{transcript}"
        
        --- LIVE DATABASE KNOWLEDGE (CRITICAL) ---
        Based on the user's problem, our backend vector database found these highly relevant Indian government schemes. 
        Read the Details, Eligibility, Documents Required, and Application Process carefully:
        
        {live_db_context}
        -------------------------------------------
        
        --- STRICT ANTI-LOOPING RULES (MEMORY & CONTEXT) ---
        1. If the Chat History shows you ALREADY told the user they are "Eligible", DO NOT check eligibility again. Move strictly to application or general chat.
        2. If the Chat History shows you are already collecting Aadhaar/Mobile, you are in the APPLICATION stage. DO NOT go backward.
        3. If the user asks about finding a "CSC", "Seva Centre", or "Where to submit", DO NOT restart the scheme questions. Simply reply: "The system has automatically located the nearest CSC center for you using GPS, as shown on the map below." (Set intent to "chat", set eligibility_status to "").
        
        --- WORKFLOW SCENARIOS ---
        
        SCENARIO A: PROBLEM DISCOVERY & PROFILING
        - Intent: "discover_schemes"
        - Action: Use the LIVE DATABASE KNOWLEDGE provided above to map their problem to the best scheme. Empathize with their situation. 
        - Based on the 'Eligibility Criteria' listed for the chosen scheme, ask the user 1 or 2 conversational questions to verify their details (e.g., Age, Income, Caste, State, etc.).
        - UI RULE: Set "eligibility_status" to "" (empty string) and "eligibility_criteria" to [].
        
        SCENARIO B: ELIGIBILITY EVALUATION
        - Intent: "check_specific"
        - Action: Evaluate their Profile against the EXACT 'Eligibility Criteria' rules from the LIVE DATABASE KNOWLEDGE above.
        - If "Not Eligible": Set "eligibility_status" to "Not Eligible", explain why with exact numbers. Ask if they want to look for other programs.
        - If "Eligible": Tell them the good news! Set "eligibility_status" to "Eligible". Tell them a summary of the 'Benefits' from the database. Ask: "Would you like me to generate your official application form now?"
        
        SCENARIO C: APPLICATION GENERATION 
        - Intent: "apply_scheme"
        - Action: The user is Eligible and said "Yes". Ask for strictly required document details (Aadhaar number, Mobile number, exact Address) AND any specific items listed under 'Documents Required' in the database.
        - List missing application details in "missing_fields".
        - UI RULE: To prevent UI glitches, set "eligibility_status" to "" (empty string) and "eligibility_criteria" to [].
        
        SCENARIO D: GRIEVANCE
        - Intent: "file_rti" (If complaining about delays/money not arriving).
        
        SCENARIO E: POST-APPLICATION / GENERAL CHAT
        - Intent: "chat"
        - Action: Use this for general follow-up questions. If they ask how to apply, look at the 'Application Process' field in the database.
        - UI RULE: Set "eligibility_status" to "" (empty string) and "eligibility_criteria" to [].
        
        Respond ONLY with this exact JSON structure (No markdown tags):
        {{
            "intent": "discover_schemes, check_specific, apply_scheme, file_rti, or chat",
            "predicted_scheme_name": "Mapped Scheme Name or 'General Discovery'",
            "entities": {{"key": "Directly translate to English. NEVER use placeholders like '[Requires English Translation]'."}},
            "missing_fields": ["List of missing details ONLY IF in apply_scheme intent"],
            "eligibility_status": "Eligible / Almost Eligible / Not Eligible / Pending Information / or empty string",
            "eligibility_reason": "Exact numerical reason if checking eligibility, else empty",
            "eligibility_criteria": [
                {{"criterion": "Exact numerical rule from database", "status": "met/not_met/pending"}}
            ],
            "rti_draft_text": "Draft if RTI, else empty",
            "response_text": "Your highly professional, empathetic, and stage-appropriate response strictly in {language}"
        }}
        """
        
        response = bedrock.converse(
            modelId="amazon.nova-lite-v1:0",
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 1000, "temperature": 0.2}
        )
        
        ai_response_text = response['output']['message']['content'][0]['text']
        cleaned_text = ai_response_text.strip().replace("```json", "").replace("```", "").strip()
        result_json = json.loads(cleaned_text)
        
        entities = result_json.get('entities', {})
        for key, value in entities.items():
            key_lower = key.lower()
            val_str = str(value).replace(" ", "")
            
            # Mask Aadhaar
            if 'aadhaar' in key_lower or 'aadhar' in key_lower or 'uid' in key_lower:
                if len(val_str) >= 4:
                    entities[key] = f"XXXX-XXXX-{val_str[-4:]}"
                    result_json['pii_secured'] = True
            
            # Mask Phone Numbers
            elif 'phone' in key_lower or 'mobile' in key_lower:
                if len(val_str) >= 4:
                    entities[key] = f"XXXXXX{val_str[-4:]}"
                    result_json['pii_secured'] = True

        result_json['entities'] = entities
        result_json['session_id'] = session_id

        table.put_item(Item={
            'session_id': session_id,
            'latest_transcript': transcript,
            'language': language,
            'detected_intent': result_json.get('intent'),
            'extracted_entities': result_json.get('entities', {})
        })

        return _build_response(200, result_json)

    except Exception as e:
        print(f"Error: {str(e)}")
        return _build_response(500, {"error": "Internal server error", "details": str(e)})

def _build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }