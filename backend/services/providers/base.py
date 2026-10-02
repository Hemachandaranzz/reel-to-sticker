from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, UploadFile

logger = logging.getLogger("uvicorn")


class MediaProvider(ABC):
    """
    Abstract Base Class for video sources.
    Defines the contract for fetching media into a local temporary path.
    """

    @abstractmethod
    async def fetch(self, source: str | UploadFile, destination: Path) -> Path:
        """
        Fetch media from source and write to destination Path.
        Returns the destination Path.
        """
        pass


class UploadProvider(MediaProvider):
    """Provider for direct user file uploads."""

    async def fetch(self, source: UploadFile, destination: Path) -> Path:
        chunk_size = 1024 * 1024
        with open(destination, "wb") as f:
            while chunk := await source.read(chunk_size):
                f.write(chunk)
        return destination


class NotConfiguredProvider(MediaProvider):
    """
    Stub provider for direct third-party URL fetching.
    Direct fetching without Meta Graph API authorization is rejected to protect privacy and comply with Terms of Service.
    """

    def __init__(self, provider_name: str = "Meta Graph API"):
        self.provider_name = provider_name

    async def fetch(self, source: str | UploadFile, destination: Path) -> Path:
        raise HTTPException(
            status_code=501,
            detail=(
                f"Direct reel fetching via '{self.provider_name}' is not configured. "
                "To convert this Reel into a sticker, please save the video to your device "
                "and upload the video file directly."
            )
        )


def get_media_provider(provider_type: str = "upload") -> MediaProvider:
    """Factory to retrieve configured media provider."""
    normalized = (provider_type or "upload").strip().lower()
    if normalized == "upload":
        return UploadProvider()
    elif normalized in ("instagram", "reel", "meta"):
        return NotConfiguredProvider("Meta Graph API")
    else:
        return NotConfiguredProvider(provider_type)
