"""Tests for the cloud actions of the Tuya Local integration."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tuya_local import async_setup
from custom_components.tuya_local.const import (
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL_VERSION,
    CONF_TYPE,
    DOMAIN,
    SERVICE_LIST_CLOUD_DEVICES,
    SERVICE_REFRESH_LOCAL_KEYS,
)
from custom_components.tuya_local.services import (
    async_handle_list_cloud_devices,
    async_handle_refresh_local_keys,
    async_setup_cloud_services,
)

CLOUD_DEVICES = {
    "dev1": {
        "name": "Heater",
        "id": "dev1",
        "node_id": "",
        "uuid": "uuid1",
        CONF_LOCAL_KEY: "newkey1",
        "category": "qn",
        "product_id": "prod1",
        "product_name": "Smart Heater",
        "ip": "10.0.0.1",
        "online": True,
        "support_local": True,
        "is_hub": False,
        "exists": object(),
    },
    "dev2": {
        "name": "Gateway",
        "id": "dev2",
        "node_id": "",
        "uuid": "uuid2",
        CONF_LOCAL_KEY: "key2",
        "category": "wg2",
        "product_id": "prod2",
        "product_name": "Gateway",
        "ip": "10.0.0.2",
        "online": False,
        "support_local": True,
        "is_hub": True,
        "exists": None,
    },
}


def mock_cloud(devices=None, error=None):
    cloud = AsyncMock()
    if error:
        cloud.async_get_devices.side_effect = error
    else:
        cloud.async_get_devices.return_value = (
            CLOUD_DEVICES if devices is None else devices
        )
    return cloud


def patch_cloud(cloud):
    return patch(
        "custom_components.tuya_local.services.async_get_cloud",
        AsyncMock(return_value=cloud),
    )


def make_call(hass, service, data=None):
    return ServiceCall(hass, DOMAIN, service, data or {})


def make_entry(hass, device_id, local_key, options=None, title="Test device"):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=title,
        data={
            CONF_DEVICE_ID: device_id,
            CONF_LOCAL_KEY: local_key,
            CONF_PROTOCOL_VERSION: "auto",
            CONF_TYPE: "simple_switch",
        },
        options=options or {},
    )
    entry.add_to_hass(hass)
    return entry


class TestListCloudDevices:
    @pytest.mark.asyncio
    async def test_lists_all_devices_with_local_keys(self, hass):
        with patch_cloud(mock_cloud()):
            result = await async_handle_list_cloud_devices(
                hass, make_call(hass, SERVICE_LIST_CLOUD_DEVICES)
            )
        devices = result["devices"]
        assert len(devices) == 2
        assert devices[0]["id"] == "dev1"
        assert devices[0][CONF_LOCAL_KEY] == "newkey1"
        assert devices[0]["product_name"] == "Smart Heater"
        # "exists" holds a device object, which cannot go in a response
        assert devices[0]["configured"] is True
        assert devices[1]["configured"] is False
        assert "exists" not in devices[0]

    @pytest.mark.asyncio
    async def test_filters_by_device_id(self, hass):
        with patch_cloud(mock_cloud()):
            result = await async_handle_list_cloud_devices(
                hass,
                make_call(hass, SERVICE_LIST_CLOUD_DEVICES, {CONF_DEVICE_ID: "dev2"}),
            )
        assert [d["id"] for d in result["devices"]] == ["dev2"]

    @pytest.mark.asyncio
    async def test_filters_by_uuid(self, hass):
        with patch_cloud(mock_cloud()):
            result = await async_handle_list_cloud_devices(
                hass,
                make_call(hass, SERVICE_LIST_CLOUD_DEVICES, {CONF_DEVICE_ID: "uuid1"}),
            )
        assert [d["id"] for d in result["devices"]] == ["dev1"]

    @pytest.mark.asyncio
    async def test_unknown_device_is_an_error(self, hass):
        with patch_cloud(mock_cloud()), pytest.raises(ServiceValidationError):
            await async_handle_list_cloud_devices(
                hass,
                make_call(hass, SERVICE_LIST_CLOUD_DEVICES, {CONF_DEVICE_ID: "nodev"}),
            )

    @pytest.mark.asyncio
    async def test_requires_login(self, hass):
        with patch_cloud(None), pytest.raises(ServiceValidationError):
            await async_handle_list_cloud_devices(
                hass, make_call(hass, SERVICE_LIST_CLOUD_DEVICES)
            )

    @pytest.mark.asyncio
    async def test_cloud_failure_is_reported(self, hass):
        with (
            patch_cloud(mock_cloud(error=Exception("boom"))),
            pytest.raises(HomeAssistantError),
        ):
            await async_handle_list_cloud_devices(
                hass, make_call(hass, SERVICE_LIST_CLOUD_DEVICES)
            )


class TestRefreshLocalKeys:
    @pytest.mark.asyncio
    async def test_rotated_key_is_updated(self, hass):
        entry = make_entry(hass, "dev1", "oldkey")
        with patch_cloud(mock_cloud()):
            result = await async_handle_refresh_local_keys(
                hass, make_call(hass, SERVICE_REFRESH_LOCAL_KEYS, {"dry_run": False})
            )
        assert [d["name"] for d in result["updated"]] == ["Test device"]
        assert entry.data[CONF_LOCAL_KEY] == "newkey1"

    @pytest.mark.asyncio
    async def test_key_in_options_is_updated_too(self, hass):
        entry = make_entry(hass, "dev1", "oldkey", options={CONF_LOCAL_KEY: "oldkey"})
        with patch_cloud(mock_cloud()):
            await async_handle_refresh_local_keys(
                hass, make_call(hass, SERVICE_REFRESH_LOCAL_KEYS, {"dry_run": False})
            )
        assert entry.options[CONF_LOCAL_KEY] == "newkey1"
        assert entry.data[CONF_LOCAL_KEY] == "newkey1"

    @pytest.mark.asyncio
    async def test_unchanged_key_is_left_alone(self, hass):
        entry = make_entry(hass, "dev1", "newkey1")
        with patch_cloud(mock_cloud()):
            result = await async_handle_refresh_local_keys(
                hass, make_call(hass, SERVICE_REFRESH_LOCAL_KEYS, {"dry_run": False})
            )
        assert [d["name"] for d in result["unchanged"]] == ["Test device"]
        assert not result["updated"]
        assert entry.data[CONF_LOCAL_KEY] == "newkey1"

    @pytest.mark.asyncio
    async def test_device_not_in_account_is_reported(self, hass):
        make_entry(hass, "other", "oldkey")
        with patch_cloud(mock_cloud()):
            result = await async_handle_refresh_local_keys(
                hass, make_call(hass, SERVICE_REFRESH_LOCAL_KEYS, {"dry_run": False})
            )
        assert [d[CONF_DEVICE_ID] for d in result["not_found"]] == ["other"]

    @pytest.mark.asyncio
    async def test_dry_run_does_not_change_config(self, hass):
        entry = make_entry(hass, "dev1", "oldkey")
        with patch_cloud(mock_cloud()):
            result = await async_handle_refresh_local_keys(
                hass, make_call(hass, SERVICE_REFRESH_LOCAL_KEYS, {"dry_run": True})
            )
        assert [d["name"] for d in result["updated"]] == ["Test device"]
        assert entry.data[CONF_LOCAL_KEY] == "oldkey"

    @pytest.mark.asyncio
    async def test_requires_login(self, hass):
        with patch_cloud(None), pytest.raises(ServiceValidationError):
            await async_handle_refresh_local_keys(
                hass, make_call(hass, SERVICE_REFRESH_LOCAL_KEYS, {"dry_run": False})
            )


@pytest.mark.asyncio
async def test_services_are_registered_once(hass):
    async_setup_cloud_services(hass)
    async_setup_cloud_services(hass)
    assert hass.services.has_service(DOMAIN, SERVICE_LIST_CLOUD_DEVICES)
    assert hass.services.has_service(DOMAIN, SERVICE_REFRESH_LOCAL_KEYS)


@pytest.mark.asyncio
async def test_services_do_not_need_a_working_device(hass):
    """The actions must be available even when no device could be set up."""
    assert await async_setup(hass, {}) is True
    assert hass.services.has_service(DOMAIN, SERVICE_LIST_CLOUD_DEVICES)
    assert hass.services.has_service(DOMAIN, SERVICE_REFRESH_LOCAL_KEYS)
