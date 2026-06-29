from huggingface_hub import HfApi
import os

token = "hf_********************************"
api = HfApi(token=token)

repo_id = "Basel0/qshub"

secrets = {
    "SMTP_HOST": "smtp.hostinger.com",
    "SMTP_PORT": "465",
    "SMTP_USER": "support@qshub.online",
    "SMTP_PASS": "********",
    "SMTP_FROM": "support@qshub.online",
    "APP_BASE_URL": "https://qshub.online"
}

for k, v in secrets.items():
    print(f"Adding secret {k}...")
    api.add_space_secret(repo_id=repo_id, key=k, value=v)

print("Successfully updated Hugging Face Space secrets!")
