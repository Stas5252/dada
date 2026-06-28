import random

from locust import HttpUser, between, task

TENANT_ID = "00000000-0000-0000-0000-000000000001"

class WebhookUser(HttpUser):
    wait_time = between(1, 5)  # Simulate a user sending a message every 1 to 5 seconds

    @task
    def simulate_telegram_message(self):
        chat_id = random.randint(100000, 999999)
        update_id = random.randint(100000, 999999)
        payload = {
            "update_id": update_id,
            "message": {
                "message_id": random.randint(1000, 9999),
                "from": {"id": chat_id, "first_name": "LoadTestUser"},
                "chat": {"id": chat_id, "type": "private"},
                "date": 1603059201,
                "text": "Hello, this is a load test message."
            }
        }
        
        # We target the telegram webhook endpoint for the mock agent.
        agent_id = "00000000-0000-0000-0000-000000000010"
        self.client.post(
            f"/api/v1/webhooks/telegram/{agent_id}",
            json=payload,
            name="Telegram Webhook"
        )
