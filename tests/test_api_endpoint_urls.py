#!/usr/bin/env python3
"""Unit tests for API client endpoint URL resolution (env / constructor / defaults)."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api.notification_client import (
    DEFAULT_NOTIFICATION_API_URL,
    NotificationClient,
)
from api.video_fetcher import DEFAULT_VIDEO_FETCHER_URL, VideoFetcher


PROD_FETCHER = DEFAULT_VIDEO_FETCHER_URL
PROD_NOTIFICATION = DEFAULT_NOTIFICATION_API_URL
STAGE_FETCHER = (
    "https://nv6ktiaxob.execute-api.us-east-1.amazonaws.com/stage/api/v1/files/paths/toTranscribe"
)
STAGE_NOTIFICATION = (
    "https://nv6ktiaxob.execute-api.us-east-1.amazonaws.com/stage/api/v1/pipeline/aiTranscription-Complete"
)
CUSTOM_URL = "https://example.com/custom"


class TestVideoFetcherEndpointUrl:
    def test_constructor_override(self):
        """Expected: explicit endpoint_url wins over env and default."""
        with patch.dict(os.environ, {"VIDEO_FETCHER_URL": STAGE_FETCHER}, clear=False):
            client = VideoFetcher(endpoint_url=CUSTOM_URL)
        assert client.endpoint_url == CUSTOM_URL

    def test_env_var_when_set(self):
        """Expected: VIDEO_FETCHER_URL is used when constructor arg is omitted."""
        with patch.dict(os.environ, {"VIDEO_FETCHER_URL": STAGE_FETCHER}, clear=False):
            client = VideoFetcher()
        assert client.endpoint_url == STAGE_FETCHER

    def test_falls_back_to_prod_default(self):
        """Edge: unset env uses prod default."""
        env = {k: v for k, v in os.environ.items() if k != "VIDEO_FETCHER_URL"}
        with patch.dict(os.environ, env, clear=True):
            client = VideoFetcher()
        assert client.endpoint_url == PROD_FETCHER

    def test_empty_constructor_none_uses_env(self):
        """Failure/edge: explicit None still resolves via env."""
        with patch.dict(os.environ, {"VIDEO_FETCHER_URL": STAGE_FETCHER}, clear=False):
            client = VideoFetcher(endpoint_url=None)
        assert client.endpoint_url == STAGE_FETCHER


class TestNotificationClientEndpointUrl:
    def test_constructor_override(self):
        """Expected: explicit endpoint_url wins over env and default."""
        with patch.dict(os.environ, {"NOTIFICATION_API_URL": STAGE_NOTIFICATION}, clear=False):
            client = NotificationClient(endpoint_url=CUSTOM_URL)
        assert client.endpoint_url == CUSTOM_URL

    def test_env_var_when_set(self):
        """Expected: NOTIFICATION_API_URL is used when constructor arg is omitted."""
        with patch.dict(os.environ, {"NOTIFICATION_API_URL": STAGE_NOTIFICATION}, clear=False):
            client = NotificationClient()
        assert client.endpoint_url == STAGE_NOTIFICATION

    def test_falls_back_to_prod_default(self):
        """Edge: unset env uses prod default."""
        env = {k: v for k, v in os.environ.items() if k != "NOTIFICATION_API_URL"}
        with patch.dict(os.environ, env, clear=True):
            client = NotificationClient()
        assert client.endpoint_url == PROD_NOTIFICATION

    def test_empty_constructor_none_uses_env(self):
        """Failure/edge: explicit None still resolves via env."""
        with patch.dict(os.environ, {"NOTIFICATION_API_URL": STAGE_NOTIFICATION}, clear=False):
            client = NotificationClient(endpoint_url=None)
        assert client.endpoint_url == STAGE_NOTIFICATION
