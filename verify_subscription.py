import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000/api/v1"

def verify_subscription():
    """Verify the subscription for user Jagga Daku"""
    
    # Step 1: Login to get JWT token
    login_data = {
        "email": "jd@gmail.com",
        "password": "jd@123"
    }
    
    print("Step 1: Logging in as 'Jagga Daku' (jd@gmail.com)...")
    try:
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        if response.status_code == 200:
            login_response = response.json()
            access_token = login_response.get('access_token')
            print("Login successful!")
            print(f"Access token: {access_token[:50]}...")
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return
    except requests.exceptions.ConnectionError:
        print("Could not connect to the API. Make sure the server is running on localhost:8000")
        return
    
    # Step 2: Get user subscription details
    headers = {"Authorization": f"Bearer {access_token}"}
    print("\nStep 2: Getting user subscription details...")
    
    try:
        response = requests.get(f"{BASE_URL}/subscriptions/user-subscription", headers=headers)
        if response.status_code == 200:
            subscription = response.json()
            print("User subscription details:")
            print(json.dumps(subscription, indent=2))
        else:
            print(f"Failed to get subscription: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("Could not connect to the API for getting subscription details")
    
    # Step 3: Get payment history
    print("\nStep 3: Getting payment history...")
    try:
        response = requests.get(f"{BASE_URL}/subscriptions/payment-history", headers=headers)
        if response.status_code == 200:
            payment_history = response.json()
            print("Payment history:")
            print(json.dumps(payment_history, indent=2))
        else:
            print(f"Failed to get payment history: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("Could not connect to the API for getting payment history")

if __name__ == "__main__":
    verify_subscription()
