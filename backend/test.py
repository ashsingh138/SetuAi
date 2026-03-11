import boto3

def test_10_bedrock_models():
    print("🔌 Initializing AWS Bedrock connection in us-east-1...\n")
    bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')

    # The Top 10 Best Text/Agent Models on Bedrock
    models_to_test = {
        # --- Amazon Native Models (Most likely to work without billing traps) ---
        "Amazon Nova Pro (Flagship)": "amazon.nova-pro-v1:0",
        "Amazon Nova Lite (Fast)": "amazon.nova-lite-v1:0",
        "Amazon Nova Micro (Ultra-Fast)": "amazon.nova-micro-v1:0",
        "Amazon Titan Text Premier": "amazon.titan-text-premier-v1:0",
        
        # --- Meta Llama 3.1 Family ---
        "Meta Llama 3.1 (8B)": "meta.llama3-1-8b-instruct-v1:0",
        "Meta Llama 3.1 (70B)": "meta.llama3-1-70b-instruct-v1:0",
        
        # --- Mistral AI Family ---
        "Mistral 7B Instruct": "mistral.mistral-7b-instruct-v0:2",
        "Mistral Mixtral 8x7B": "mistral.mixtral-8x7b-instruct-v0:1",
        "Mistral Large": "mistral.mistral-large-2402-v1:0",
        
        # --- Cohere Family (Excellent at RAG & Tool Calling) ---
        "Cohere Command R": "cohere.command-r-v1:0"
    }

    prompt = "Reply with exactly one word: 'Online'."

    for name, model_id in models_to_test.items():
        print(f"Testing {name}\nID: {model_id}...")
        try:
            response = bedrock.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 10, "temperature": 0.1}
            )
            reply = response['output']['message']['content'][0]['text'].strip()
            print(f"  ✅ SUCCESS! Replied: {reply}\n")
            
        except Exception as e:
            error_msg = str(e)
            if "AccessDenied" in error_msg or "INVALID_PAYMENT" in error_msg:
                print("  ❌ FAILED: Blocked by AWS Marketplace Billing.\n")
            elif "ResourceNotFound" in error_msg or "use case details" in error_msg:
                print("  ❌ FAILED: Needs 'Use Case' form submitted in Console.\n")
            elif "AccessDeniedException" in error_msg:
                 print("  ❌ FAILED: Needs to be checked/unlocked in Model Access page.\n")
            else:
                print(f"  ❌ FAILED: {error_msg}\n")

if __name__ == "__main__":
    test_10_bedrock_models()