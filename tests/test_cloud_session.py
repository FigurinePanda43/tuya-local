"""Tests for persistence of the Tuya cloud login session."""

import pytest

from custom_components.tuya_local.cloud_session import (
    async_clear_session,
    async_get_cloud,
    async_restore_session,
    async_save_session,
)
from custom_components.tuya_local.const import DATA_AUTH_CACHE, DOMAIN

AUTH = {
    "user_code": "testcode",
    "terminal_id": "terminal",
    "endpoint": "https://example.com",
    "token_info": {"access_token": "token"},
}


@pytest.mark.asyncio
async def test_restore_returns_false_when_nothing_saved(hass):
    assert await async_restore_session(hass) is False


@pytest.mark.asyncio
async def test_session_survives_loss_of_memory_cache(hass):
    hass.data[DOMAIN] = {DATA_AUTH_CACHE: AUTH}
    await async_save_session(hass)

    # Simulate a restart, where only the stored session remains
    hass.data[DOMAIN] = {}
    assert await async_restore_session(hass) is True
    assert hass.data[DOMAIN][DATA_AUTH_CACHE] == AUTH


@pytest.mark.asyncio
async def test_restore_keeps_memory_cache(hass):
    hass.data[DOMAIN] = {DATA_AUTH_CACHE: AUTH}
    assert await async_restore_session(hass) is True
    assert hass.data[DOMAIN][DATA_AUTH_CACHE] == AUTH


@pytest.mark.asyncio
async def test_saving_without_auth_clears_the_store(hass):
    hass.data[DOMAIN] = {DATA_AUTH_CACHE: AUTH}
    await async_save_session(hass)
    hass.data[DOMAIN] = {DATA_AUTH_CACHE: None}
    await async_save_session(hass)

    hass.data[DOMAIN] = {}
    assert await async_restore_session(hass) is False


@pytest.mark.asyncio
async def test_clear_session_forgets_everything(hass):
    hass.data[DOMAIN] = {DATA_AUTH_CACHE: AUTH}
    await async_save_session(hass)
    await async_clear_session(hass)

    assert hass.data[DOMAIN][DATA_AUTH_CACHE] is None
    hass.data[DOMAIN] = {}
    assert await async_restore_session(hass) is False


@pytest.mark.asyncio
async def test_get_cloud_returns_none_when_not_logged_in(hass):
    assert await async_get_cloud(hass) is None


@pytest.mark.asyncio
async def test_get_cloud_returns_authenticated_cloud(hass):
    hass.data[DOMAIN] = {DATA_AUTH_CACHE: AUTH}
    await async_save_session(hass)
    hass.data[DOMAIN] = {}

    cloud = await async_get_cloud(hass)
    assert cloud is not None
    assert cloud.is_authenticated
