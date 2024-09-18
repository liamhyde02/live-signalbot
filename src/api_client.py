import requests
import logging
from config import API_BASE_URL, API_KEY

logger = logging.getLogger(__name__)

def call_api(endpoint, method="GET", params=None, json=None):
    url = f"{API_BASE_URL}{endpoint}"
    headers = {"access_token": API_KEY}
    try:
        if method == "GET":
            response = requests.get(url, params=params, headers=headers)
        elif method == "POST":
            if params:
                response = requests.post(url, params=params, headers=headers)
            elif json:
                response = requests.post(url, json=json, headers=headers)
            else:
                response = requests.post(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API call failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response content: {e.response.content}")
        return None

def get_customer_org_id(team_id):
    response = call_api("/customerorganization/slack", method="GET", params={"slack_id": str(team_id)})
    if response and "customer_organization_id" in response:
        return response["customer_organization_id"]
    return None