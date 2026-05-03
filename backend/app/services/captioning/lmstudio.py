"""
LM Studio captioner.

Uses LM Studio's OpenAI-compatible local API. Requires LM Studio to be running
with a vision-capable model loaded. Default base URL: http://localhost:1234/v1
"""
from __future__ import annotations

import base64

from openai import AsyncOpenAI

from .base import BaseCaptioner

_DEFAULT_SYSTEM = (
    "You are a concise image description assistant. "
    "Generate a single-sentence caption describing the visual content."
)
_MAX_TOKENS = 300


class LMStudioCaptioner(BaseCaptioner):
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
    ) -> None:
        self.model_name = model
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or "lm-studio",
        )

    async def generate(
        self,
        image_bytes: bytes,
        system_prompt: str,
        mime_type: str = "image/jpeg",
    ) -> str:
        b64 = base64.b64encode(image_bytes).decode()
        system = system_prompt.strip() or _DEFAULT_SYSTEM

        response = await self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Generate a caption for this image or animation."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                        },
                    ],
                },
            ],
            max_tokens=_MAX_TOKENS,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
