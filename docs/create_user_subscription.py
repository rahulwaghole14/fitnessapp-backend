import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000/api/v1"

def create_user_and_subscription():
    """Create user 'jagga daku' and then create a subscription"""
    
    # Step 1: Register the user
    user_data = {
        "username": "jagga daku",
        "email": "jagga.daku@example.com",
        "password": "password123"
    }
    
    print("Step 1: Registering user 'jagga daku'...")
    try:
        response = requests.post(f"{BASE_URL}/register", json=user_data)
        if response.status_code == 201:
            print("User registered successfully!")
            user_response = response.json()
            print(f"User ID: {user_response.get('id')}")
        elif response.status_code == 400 and "already registered" in response.text:
            print("User already exists, proceeding to login...")
        else:
            print(f"Registration failed: {response.status_code} - {response.text}")
            return
    except requests.exceptions.ConnectionError:
        print("Could not connect to the API. Make sure the server is running on localhost:8000")
        return
    
    # Step 2: Login to get JWT token
    login_data = {
        "username": "jagga daku",
        "password": "password123"
    }
    
    print("\nStep 2: Logging in...")
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
        print("Could not connect to the API for login")
        return
    
    # Step 3: Get available subscription plans
    headers = {"Authorization": f"Bearer {access_token}"}
    print("\nStep 3: Getting available subscription plans...")
    
    try:
        response = requests.get(f"{BASE_URL}/subscription-plans", headers=headers)
        if response.status_code == 200:
            plans = response.json()
            print("Available plans:")
            for plan in plans:
                print(f"ID: {plan['id']}, Name: {plan['name']}, Price: {plan['price']}, Duration: {plan['duration_days']} days")
        else:
            print(f"Failed to get plans: {response.status_code} - {response.text}")
            return
    except requests.exceptions.ConnectionError:
        print("Could not connect to the API for getting plans")
        return
    
    # Step 4: Create subscription order (using plan ID 4 - test plan)
    subscription_data = {
        "plan_id": 4  # Using the test plan (ID=4, Price=299.00, Duration=90 days)
    }
    
    print("\nStep 4: Creating subscription order...")
    try:
        response = requests.post(f"{BASE_URL}/subscriptions/order", json=subscription_data, headers=headers)
        if response.status_code == 200:
            order_response = response.json()
            print("Subscription order created successfully!")
            print(f"Order ID: {order_response.get('order_id')}")
            print(f"Amount: {order_response.get('amount')}")
            print(f"Receipt: {order_response.get('receipt')}")
            
            # Step 5: Get user subscription details
            print("\nStep 5: Getting user subscription details...")
            try:
                response = requests.get(f"{BASE_URL}/subscriptions/user-subscription", headers=headers)
                if response.status_code == 200:
                    subscription = response.json()
                    print("User subscription details:")
                    print(json.dumps(subscription, indent=2))
                else:
                    print(f"No active subscription found: {response.status_code}")
            except requests.exceptions.ConnectionError:
                print("Could not get subscription details")
                
        else:
            print(f"Failed to create subscription order: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("Could not connect to the API for creating subscription")

if __name__ == "__main__":
    create_user_and_subscription()
