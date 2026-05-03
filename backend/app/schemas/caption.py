from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel


class CaptionProvider(str, Enum):
    azure    = "azure"
    openai   = "openai"
    gemini   = "gemini"
    lmstudio = "lmstudio"


class AzureConfig(BaseModel):
    endpoint: str
    deployment: str
    subscription_key: str
    api_version: str = "2024-12-01-preview"


class OpenAIConfig(BaseModel):
    api_key: str
    model: Literal["gpt-4o", "gpt-4.1", "gpt-4.1-mini"] = "gpt-4o"


class GeminiConfig(BaseModel):
    api_key: str
    model: Literal[
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ] = "gemini-2.5-flash"


class LMStudioConfig(BaseModel):
    base_url: str = "http://localhost:1234/v1"
    api_key:  str = ""
    model:    str = ""


class CaptionRequestConfig(BaseModel):
    """JSON-encoded config sent alongside the media file upload."""
    provider:        CaptionProvider
    system_prompt:   str = ""
    azure_config:    Optional[AzureConfig]    = None
    openai_config:   Optional[OpenAIConfig]   = None
    gemini_config:   Optional[GeminiConfig]   = None
    lmstudio_config: Optional[LMStudioConfig] = None


class CaptionResponse(BaseModel):
    caption:  str
    provider: str
    model:    str
