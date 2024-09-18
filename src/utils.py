from api_client import call_api

def show_organizations(client, channel_id, customer_org_id):
    organizations = call_api("/organization/list", params={"customer_organization_id": customer_org_id})
    org_list = "\n".join([f"{org['id']}: {org['name']}" for org in organizations])
    client.chat_postMessage(
        channel=channel_id,
        text=f"Here are the available organizations:\n{org_list}\n\nPlease reply with:\n"
             f"- One or more organization IDs (comma-separated)\n"
             f"- 'new' to create a new organization\n"
             f"- 'none' to proceed without selecting any organizations"
    )

def show_users(client, channel_id, customer_org_id):
    users = call_api("/user/list", params={"customer_organization_id": customer_org_id})
    user_list = "\n".join([f"{user['id']}: {user['name']}" for user in users])
    client.chat_postMessage(
        channel=channel_id,
        text=f"Here are the available users:\n{user_list}\n\nPlease reply with:\n"
             f"- An existing user ID\n"
             f"- 'new' to create a new user"
    )

def show_customer_organizations(client, channel_id):
    organizations = call_api("/customerorganization/list")
    org_list = "\n".join([f"{org['id']}: {org['name']}" for org in organizations])
    client.chat_postMessage(
        channel=channel_id,
        text=f"Here are the available customer organizations:\n{org_list}\n\nPlease reply with:\n"
             f"- An existing customer organization ID\n"
             f"- 'new' to create a new customer organization"
    )