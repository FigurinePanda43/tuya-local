"""Services for Tuya Local integration."""

import asyncio
import logging

import voluptuous as vol
from homeassistant.components import infrared
from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    DEFAULT_DELAY_SECS,
)
from homeassistant.components.remote import DOMAIN as REMOTE_DOMAIN
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service

from .cloud_session import async_get_cloud
from .const import (
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    DOMAIN,
    SERVICE_LIST_CLOUD_DEVICES,
    SERVICE_REFRESH_LOCAL_KEYS,
)
from .infrared import TuyaRemoteCommand
from .remote import FLAG_SAVE_DELAY, TuyaLocalRemote

REMOTE_SEND_IR_COMMAND_SCHEMA = {
    vol.Required("emitter_entity_id"): cv.entity_id,
    vol.Required("command"): str,
    vol.Optional("device"): str,
}

LIST_CLOUD_DEVICES_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DEVICE_ID): cv.string,
    }
)

REFRESH_LOCAL_KEYS_SCHEMA = vol.Schema(
    {
        vol.Optional("dry_run", default=False): cv.boolean,
    }
)

# The fields of a cloud device that are reported by the list_cloud_devices
# action.  Between them they cover everything needed to set up a device
# locally, without visiting the Tuya IoT developer platform.
CLOUD_DEVICE_FIELDS = (
    "name",
    "id",
    "node_id",
    "uuid",
    CONF_LOCAL_KEY,
    "category",
    "product_id",
    "product_name",
    "ip",
    "online",
    "support_local",
    "is_hub",
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_services(hass: HomeAssistant, entities: list[str]):
    """Set up services for the Tuya Local integration."""
    if "remote" in entities:
        service.async_register_platform_entity_service(
            hass,
            DOMAIN,
            "send_learned_ir_command",
            entity_domain=REMOTE_DOMAIN,
            schema=REMOTE_SEND_IR_COMMAND_SCHEMA,
            func=async_handle_send_ir_command,
        )
    return True


@callback
def async_setup_cloud_services(hass: HomeAssistant):
    """Register the actions that query the Tuya cloud account."""
    if hass.services.has_service(DOMAIN, SERVICE_LIST_CLOUD_DEVICES):
        return

    async def async_list_cloud_devices(call: ServiceCall):
        return await async_handle_list_cloud_devices(hass, call)

    async def async_refresh_local_keys(call: ServiceCall):
        return await async_handle_refresh_local_keys(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_CLOUD_DEVICES,
        async_list_cloud_devices,
        schema=LIST_CLOUD_DEVICES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_LOCAL_KEYS,
        async_refresh_local_keys,
        schema=REFRESH_LOCAL_KEYS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


async def _async_cloud_devices(hass: HomeAssistant):
    """Return the devices of the logged in Tuya cloud account."""
    cloud = await async_get_cloud(hass)
    if cloud is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="cloud_not_logged_in",
        )
    try:
        devices = await cloud.async_get_devices()
    except Exception as e:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="cloud_query_failed",
            translation_placeholders={"error": f"{type(e).__name__}: {e}"},
        ) from e
    return cloud, devices


def _cloud_device_info(device: dict):
    """Pick the reportable fields out of a cloud device."""
    info = {field: device.get(field) for field in CLOUD_DEVICE_FIELDS}
    # "exists" holds the device object when it is already set up, which is not
    # serializable into an action response.
    info["configured"] = bool(device.get("exists"))
    return info


async def async_handle_list_cloud_devices(hass: HomeAssistant, call: ServiceCall):
    """Action to list the devices of the Tuya account, with their local keys.

    This gives the device id, local key and other details of every device in
    the Smart Life or Tuya account, so they can be used to set up devices
    manually here or in other local integrations, without needing a Tuya IoT
    developer account.
    """
    _, devices = await _async_cloud_devices(hass)
    wanted = call.data.get(CONF_DEVICE_ID)
    found = []
    for device in devices.values():
        if wanted and wanted not in (
            device.get("id"),
            device.get("uuid"),
            device.get("node_id"),
        ):
            continue
        found.append(_cloud_device_info(device))

    if wanted and not found:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="cloud_device_not_found",
            translation_placeholders={"device_id": wanted},
        )

    _LOGGER.debug("Returning %d devices from the Tuya cloud", len(found))
    return {"devices": found}


async def async_handle_refresh_local_keys(hass: HomeAssistant, call: ServiceCall):
    """Action to update configured devices with local keys from the cloud.

    Tuya rotates the local key whenever a device is re-paired in the app, which
    silently breaks local control until the new key is entered.  This compares
    the configured keys against the cloud and repairs the ones that no longer
    match.
    """
    _, devices = await _async_cloud_devices(hass)
    cloud_keys = {
        device["id"]: device[CONF_LOCAL_KEY]
        for device in devices.values()
        if device.get("id") and device.get(CONF_LOCAL_KEY)
    }
    dry_run = call.data.get("dry_run", False)

    updated = []
    unchanged = []
    not_found = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        config = {**entry.data, **entry.options}
        device_id = config.get(CONF_DEVICE_ID)
        report = {"name": entry.title, CONF_DEVICE_ID: device_id}
        new_key = cloud_keys.get(device_id)
        if not new_key:
            not_found.append(report)
            continue
        if new_key == config.get(CONF_LOCAL_KEY):
            unchanged.append(report)
            continue

        updated.append(report)
        _LOGGER.warning(
            "Local key of %s has been rotated by Tuya%s",
            entry.title,
            ", not updating as this is a dry run" if dry_run else ", updating it",
        )
        if dry_run:
            continue
        data = {**entry.data, CONF_LOCAL_KEY: new_key}
        options = {**entry.options}
        if CONF_LOCAL_KEY in options:
            options[CONF_LOCAL_KEY] = new_key
        hass.config_entries.async_update_entry(entry, data=data, options=options)

    return {
        "updated": updated,
        "unchanged": unchanged,
        "not_found": not_found,
    }


async def async_handle_send_ir_command(entity, call: ServiceCall):
    """Action to send a saved remote command."""
    _LOGGER.info("Sending saved remote command: %s", call.data)

    if not isinstance(entity, TuyaLocalRemote):
        raise ValueError("Entity must be a tuya-local remote")
    if not entity._storage_loaded:
        await entity._async_load_storage()

    emitter = call.data.get("emitter_entity_id")
    device = call.data.get("device")
    command = call.data.get("command")
    delay = call.data.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)
    code_list = entity._extract_codes(
        [command], subdevice=device
    )  # Validate command and get code
    at_least_one_sent = False
    for codes in code_list:
        if at_least_one_sent:
            await asyncio.sleep(delay)
        if len(codes) > 1:
            code = codes[entity._flags[device]]
            entity._flags[device] ^= 1
        else:
            code = codes[0]
        if code.startswith("rf:"):
            _LOGGER.error("RF emitters are not yet supported by this service")
            continue
        await infrared.async_send_command(
            entity.hass, emitter, TuyaRemoteCommand(code=code)
        )
        at_least_one_sent = True

        if at_least_one_sent:
            entity._flag_storage.async_delay_save(
                lambda: entity._flags, FLAG_SAVE_DELAY
            )
