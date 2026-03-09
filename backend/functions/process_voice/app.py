import json
import boto3
import uuid
import os

bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('SESSIONS_TABLE', 'setu-ai-sessions'))

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        transcript = body.get('transcript', '') 
        session_id = body.get('session_id', str(uuid.uuid4()))
        language = body.get('language', 'Hindi')
        chat_history = body.get('chat_history', '')

        if not transcript:
            return _build_response(400, {"error": "Transcript is required"})

        # THE DYNAMIC PROMPT: The Ultimate Problem-Solving & State-Machine Workflow
        prompt = f"""
        You are Setu AI, a highly professional, polite, and empathetic government caseworker for citizens in India.
        User's requested language: {language}
        
        PREVIOUS CONVERSATION HISTORY (Use this to remember what the user has ALREADY told you. DO NOT ask for this information again):
        {chat_history}
        
        CURRENT MESSAGE: "{transcript}"
        
        --- STRICT ANTI-LOOPING RULES (MEMORY & CONTEXT) ---
        1. If the Chat History shows you ALREADY told the user they are "Eligible", DO NOT check eligibility again. Move strictly to application or general chat.
        2. If the Chat History shows you are already collecting Aadhaar/Mobile, you are in the APPLICATION stage. DO NOT go backward.
        3. If the user asks about finding a "CSC", "Seva Centre", or "Where to submit", DO NOT restart the scheme questions. Simply reply: "The system has automatically located the nearest CSC center for you using GPS, as shown on the map below." (Set intent to "chat", set eligibility_status to "").
        
        --- PROBLEM-TO-SCHEME MAPPING (CRITICAL EXPERTISE) ---
        Citizens usually DO NOT know scheme names. They will tell you their problem. You must internally map their problem to the correct Indian Government scheme:
        - "No house" / "Kacha house" / "Need home" -> Pradhan Mantri Awas Yojana (PMAY)
        - "Health issues" / "Hospital bills" / "Sick" -> Ayushman Bharat (PM-JAY)
        - "Farmer" / "Need seeds" / "Agriculture" -> PM Kisan Samman Nidhi
        - "Crop ruined" / "Weather damage" -> PM Fasal Bima Yojana
        - "Widow" / "Husband passed away" -> Indira Gandhi National Widow Pension Scheme
        - "Student" / "College fees" -> PM Vidyalaxmi / Post Matric Scholarships
        - "No food" / "Ration" -> PM Garib Kalyan Anna Yojana
        - "Business loan" / "Start shop" -> PM Mudra Yojana
        
        --- THE MYSCHEME PROFILE MASTER LIST ---
        To check eligibility accurately, you track: Age, Gender, Marital Status, State, Urban/Rural, Caste Category, Disability, Minority, Student Status, BPL Category (If No -> Family Income).
        CRITICAL RULE: Before declaring someone eligible for a mapped scheme, you MUST gather at least their basic profile (Age, Gender, State, Caste, Income/BPL). Ask for missing details conversationally, a MAXIMUM of 2 questions at a time.
        
        --- WORKFLOW SCENARIOS ---
        
        SCENARIO A: PROBLEM DISCOVERY & PROFILING (User states a problem or wants help)
        - Intent: "discover_schemes"
        - Action: Identify their problem and map it to a scheme using the mapping above. Empathize with their situation. Ask for the basic profile details (max 2 at a time).
        - UI RULE: Set "eligibility_status" to "" (empty string) and "eligibility_criteria" to [].
        
        SCENARIO B: ELIGIBILITY EVALUATION (Once you have mapped the scheme AND gathered basic profile data)
        - Intent: "check_specific"
        - Action: Evaluate their Profile against the EXACT real-world numerical rules of the mapped scheme.
        - If "Not Eligible": Set "eligibility_status" to "Not Eligible", explain why with exact numbers in "eligibility_reason". Ask: "Since you do not meet the criteria for this scheme, would you like me to look for other welfare programs?"
        - If "Eligible": Tell them the good news! Set "eligibility_status" to "Eligible". Ask: "Would you like me to generate your official application form now?"
        
        SCENARIO C: APPLICATION GENERATION (User was Eligible AND said "Yes/Proceed" to the form)
        - Intent: "apply_scheme"
        - Action: Now shift to application mode. Ask for strictly required document details (Aadhaar number, Mobile number, exact Address). 
        - List missing application details in "missing_fields".
        - UI RULE: To prevent UI glitches, set "eligibility_status" to "" (empty string) and "eligibility_criteria" to [].
        
        SCENARIO D: GRIEVANCE
        - Intent: "file_rti" (If complaining about delays/money not arriving).
        
        SCENARIO E: POST-APPLICATION / GENERAL CHAT
        - Intent: "chat"
        - Action: Use this for general follow-up questions (like where to submit the form, Seva Kendra location, etc.).
        - UI RULE: Set "eligibility_status" to "" (empty string) and "eligibility_criteria" to [].
        
        Respond ONLY with this exact JSON structure (No markdown tags):
        {{
            "intent": "discover_schemes, check_specific, apply_scheme, file_rti, or chat",
            "predicted_scheme_name": "Mapped Scheme Name or 'General Discovery'",
            "entities": {{"key": "English Value of all profile and application data gathered"}},
            "missing_fields": ["List of missing details ONLY IF in apply_scheme intent"],
            "eligibility_status": "Eligible / Almost Eligible / Not Eligible / Pending Information / or empty string",
            "eligibility_reason": "Exact numerical reason if checking eligibility, else empty",
            "eligibility_criteria": [
                {{"criterion": "Exact numerical rule", "status": "met/not_met/pending"}}
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
            
            # Mask Aadhaar (e.g., 123456789012 -> XXXX-XXXX-9012)
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