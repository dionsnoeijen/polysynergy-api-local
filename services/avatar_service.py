import os
import base64
import random
from openai import OpenAI
from polysynergy_node_runner.services.s3_service import S3Service

from models import Account

class AvatarService:
    @staticmethod
    def generate_and_upload(
        node_id: str,
        name: str,
        instructions: str,
        account: Account,
        s3_service: S3Service
    ) -> str:
        memberships = account.memberships
        if not memberships:
            raise ValueError("No tenants available for this user")

        prompt = AvatarService.build_prompt(name or "Alex", instructions or "No specific instructions")
        api_key = os.getenv('OPENAI_API_KEY', "")
        if not api_key:
            raise ValueError("Missing OpenAI API key")

        image_bytes = AvatarService.generate_image(prompt, api_key)

        s3_key = f"avatars/{node_id}.png"
        s3_url = s3_service.upload_file(image_bytes, s3_key)

        if not s3_url:
            raise RuntimeError("Upload to S3 failed")
        return s3_url

    @staticmethod
    def build_prompt(name: str, instructions: str) -> str:
        gender = random.choice(["man", "woman"])
        accessory = random.choice([
            "wearing a headset",
            "with glasses and a serious expression",
            "smiling confidently",
            "with a coffee mug",
            "in a blazer and sneakers",
            "leaning slightly, arms crossed"
        ])
        return (
            f"A pixel art portrait of a {gender} office worker named {name}. "
            f"This character works as an AI assistant. "
            f"Instructions: {instructions}. "
            f"They are depicted {accessory}, in a moody and stylish office environment. "
            "Bust shot, dramatic purple and pink lighting, deep shadows, vibrant but not bright. "
            "Rendered in 32-bit retro video game style. No white background, no text in image."
        )

    @staticmethod
    def generate_image(prompt: str, api_key: str) -> bytes:
        client = OpenAI(api_key=api_key)
        response = client.images.generate(
            model="dall-e-2",
            prompt=prompt,
            size="1024x1024",
            response_format="b64_json",
            n=1
        )
        b64 = response.data[0].b64_json
        return base64.b64decode(b64)