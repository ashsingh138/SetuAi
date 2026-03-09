import json

def lambda_handler(event, context):
    # Retrieve query parameters
    query_params = event.get('queryStringParameters') or {}
    lat = query_params.get('latitude')
    lng = query_params.get('longitude')

    
    nearest_csc = {
        "center_name": "Gram Panchayat Seva Kendra, Varanasi",
        "address": "Near Main Market, Block B, Varanasi, UP - 221002",
        "distance_km": "1.2",
        "operating_hours": "9:00 AM - 5:00 PM (Mon-Sat)",
        "services": ["PMAY Application", "Aadhaar Update", "Pension Submission"],
        "lat": 25.3176,
        "lng": 82.9739
    }

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        },
        "body": json.dumps(nearest_csc)
    }