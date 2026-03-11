import json
import boto3
import uuid
import os
import faiss
import numpy as np
import re
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
    return json.loads(response.get('body').read()).get('embedding')

# --- 2. THE AI TOOLS (PYTHON FUNCTIONS) ---

def search_eligible_schemes(problem, state, age, gender, caste, income):
    """Tool 1: Searches the vector DB. Only triggered when AI has all profile data."""
    try:
        query = f"Schemes for {problem} in {state} for {gender} age {age} caste {caste} income {income}"
        vector = get_titan_embedding(query)
        distances, indices = index.search(np.array([vector]).astype('float32'), 4) # Get top 4
        
        results = []
        for idx in indices[0]:
            if idx == -1: continue 
            row = metadata_list[idx] 
            results.append({
                "Scheme Name": row.get('scheme_name', 'Unknown'),
                "Main Benefit": row.get('benefits', 'N/A')
            })
        return json.dumps({"status": "success", "eligible_schemes": results})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def get_scheme_deep_dive(scheme_name):
    """Tool 2: Gets exact application details when user selects a scheme from the menu."""
    try:
        for row in metadata_list:
            if scheme_name.lower() in row.get('scheme_name', '').lower():
                return json.dumps({
                    "Documents Required": row.get('documents', 'N/A'),
                    "Application Process": row.get('application', 'N/A'),
                    "Detailed Eligibility": row.get('eligibility', 'N/A')
                })
        return json.dumps({"error": "Scheme details not found."})
    except Exception as e:
        return json.dumps({"error": str(e)})


# --- 3. THE TOOL CONFIGURATION FOR BEDROCK ---
tool_config = {
    "tools": [
        {
            "toolSpec": {
                "name": "search_eligible_schemes",
                "description": "Search the database for eligible government schemes. DO NOT CALL THIS TOOL if any required fields are missing. You must ask the user first.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "problem": {"type": "string", "description": "The specific help they need (e.g. house, hospital, farming)"},
                            "state": {"type": "string", "description": "State of residence. IF UNKNOWN, DO NOT USE TOOL. ASK USER."},
                            "age": {"type": "string", "description": "Age. IF UNKNOWN, DO NOT USE TOOL. ASK USER."},
                            "gender": {"type": "string", "description": "Gender. IF UNKNOWN, DO NOT USE TOOL. ASK USER."},
                            "caste": {"type": "string", "description": "General, SC, ST, or OBC. IF UNKNOWN, DO NOT USE TOOL. ASK USER."},
                            "income": {"type": "string", "description": "Annual income or BPL status. IF UNKNOWN, DO NOT USE TOOL. ASK USER."}
                        },
                        "required": ["problem", "state", "age", "gender", "caste", "income"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "get_scheme_deep_dive",
                "description": "Fetch the exact documents required and application process for a specific scheme. Call this when the user chooses a scheme from your menu.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "scheme_name": {"type": "string"}
                        },
                        "required": ["scheme_name"]
                    }
                }
            }
        }
    ]
}

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        transcript = body.get('transcript', '') 
        session_id = body.get('session_id', str(uuid.uuid4()))
        language = body.get('language', 'Hindi')
        chat_history = body.get('chat_history', '')

        if not transcript:
            return _build_response(400, {"error": "Transcript is required"})

        # --- 4. THE SYSTEM PROMPT (The Orchestrator) ---
        system_prompt = f"""
        You are Setu AI, a professional government caseworker. 
        Language: {language}

        CRITICAL PROFILING RULE: You MUST NOT call the `search_eligible_schemes` tool if the user has not explicitly told you their exact State, Age, Gender, Caste, and Income. NEVER guess, assume, or use placeholders like 'unknown'. If any are missing, stay in STEP 1.

        You strictly follow this 6-Step Pipeline and MUST output the exact corresponding "intent" in your JSON:

        STEP 1: PROFILING -> You MUST set "intent": "profiling"
        Action: If ANY of the 6 details (Problem, State, Age, Gender, Caste, Income) are missing, politely ask the user for them (max 2 questions at a time). NEVER suggest schemes yet.

        STEP 2: THE MENU -> You MUST set "intent": "suggest_menu"
        Action: ONLY when you have all 6 details explicitly, call `search_eligible_schemes`. List the schemes with bullets, state their 'Main Benefit', and ask which one they want to explore.

        STEP 3: DEEP DIVE -> You MUST set "intent": "explain_scheme"
        Action: When the user chooses a scheme, call `get_scheme_deep_dive`. Explain documents/process using bullets. Ask if they want to apply.

        STEP 4: FORM FILLING -> You MUST set "intent": "apply_scheme"
        Action: If they say yes to applying, ask for their Aadhaar, Phone, and exact Address.

        STEP 5: PDF GENERATION -> You MUST set "intent": "generate_pdf"
        Action: WHEN the user provides their Aadhaar and Phone, you MUST set the intent exactly to "generate_pdf". Say: "I am generating your application PDF."

        STEP 6: LOCATE CSC -> You MUST set "intent": "locate_csc"
        Action: If the user asks for the nearest center or map, you MUST set the intent exactly to "locate_csc". Say: "I am locating the nearest Seva Kendra on the map."

        CRITICAL FORMATTING RULES:
        1. NEVER use asterisks (* or **) anywhere in your text.
        2. Inside "response_text", use "\\n\\n" for paragraph breaks and "\\n• " for bullet points.
        3. Your final output MUST ALWAYS be a valid JSON object matching this schema exactly:
        {{
            "intent": "profiling, suggest_menu, explain_scheme, apply_scheme, generate_pdf, or locate_csc",
            "predicted_scheme_name": "Name of scheme being discussed, or empty",
            "response_text": "Your properly formatted conversational reply.",
            "entities": {{}},
            "profile_tracker": {{"problem": "", "state": "", "age": "", "gender": "", "caste": "", "income": ""}}
        }}
        """

        messages = [
            {"role": "user", "content": [{"text": f"Chat History:\n{chat_history}\n\nUser's Current Message: {transcript}"}]}
        ]

        # --- 5. THE AGENTIC LOOP ---
        
        response = bedrock.converse(
            modelId= "amazon.nova-pro-v1:0",
            messages=messages,
            system=[{"text": system_prompt}],
            toolConfig=tool_config,
            inferenceConfig={"maxTokens": 1000, "temperature": 0.1}
        )
        
        stop_reason = response['stopReason']
        message_content = response['output']['message']['content']

        
        if stop_reason == 'tool_use':
            tool_results = []
            for block in message_content:
                if 'toolUse' in block:
                    tool_name = block['toolUse']['name']
                    tool_inputs = block['toolUse']['input']
                    tool_id = block['toolUse']['toolUseId']
                    
                    # Execute the Python Tool
                    if tool_name == "search_eligible_schemes":
                        tool_output = search_eligible_schemes(**tool_inputs)
                    elif tool_name == "get_scheme_deep_dive":
                        tool_output = get_scheme_deep_dive(**tool_inputs)
                    else:
                        tool_output = '{"error": "Unknown tool"}'
                        
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_id,
                            "content": [{"text": tool_output}]
                        }
                    })
            
            
            messages.append({"role": "assistant", "content": message_content})
            messages.append({"role": "user", "content": tool_results})
            
            response = bedrock.converse(
                modelId="amazon.nova-pro-v1:0",
                messages=messages,
                system=[{"text": system_prompt}],
                toolConfig=tool_config,
                inferenceConfig={"maxTokens": 1000, "temperature": 0.1}
            )
            final_ai_text = response['output']['message']['content'][0]['text']
        else:
            
            final_ai_text = message_content[0]['text']

       
        try:
           
            json_match = re.search(r'\{.*\}', final_ai_text, re.DOTALL)
            
            if json_match:
                cleaned_text = json_match.group(0)
            else:
                cleaned_text = final_ai_text
                
            result_json = json.loads(cleaned_text)
            
        except json.JSONDecodeError as e:
            
            print(f"🚨 JSON Parsing Failed! Raw AI Output was:\n{final_ai_text}")
           
            result_json = {
                "intent": "chat",
                "predicted_scheme_name": "",
                "response_text": final_ai_text.strip(), 
                "entities": {},
                "profile_tracker": {"problem": "", "state": "", "age": "", "gender": "", "caste": "", "income": ""}
            }

        # PII Masking Logic
        entities = result_json.get('entities', {})
        for key, value in entities.items():
            val_str = str(value).replace(" ", "")
            if 'aadhaar' in key.lower() or 'aadhar' in key.lower() or 'uid' in key.lower():
                if len(val_str) >= 4:
                    entities[key] = f"XXXX-XXXX-{val_str[-4:]}"
                    result_json['pii_secured'] = True
            elif 'phone' in key.lower() or 'mobile' in key.lower():
                if len(val_str) >= 4:
                    entities[key] = f"XXXXXX{val_str[-4:]}"
                    result_json['pii_secured'] = True

        result_json['entities'] = entities
        result_json['session_id'] = session_id

        # Save to DB
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