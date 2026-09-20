"""Bedrock Runtime Client Factory.

Encapsulates low-level boto3 client instantiation and botocore configuration.
"""

from typing import Any

import boto3
from botocore.config import Config

from app.providers.bedrock.config import BedrockProviderConfig


def create_bedrock_runtime_client(config: BedrockProviderConfig) -> Any:
    """Create a configured boto3 client for Bedrock Runtime with conservative timeouts."""
    boto_config = Config(
        region_name=config.region_name,
        connect_timeout=config.timeout_seconds,
        read_timeout=config.timeout_seconds,
        retries={
            "max_attempts": config.max_retries,
            "mode": "standard",
        },
    )
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=config.region_name,
        config=boto_config,
    )
