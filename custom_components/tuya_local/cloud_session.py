"""Persistent storage of the Tuya cloud login session.

The QR code login in the config flow authenticates against the Smart Life
account using Home Assistant's public device sharing app registration, so no
Tuya IoT developer account, cloud project, access id or access secret is
needed to look up device ids and local keys.

Until now the resulting token was only held in memory for the duration of the
config flow, so it was lost on restart.  Saving it lets the cloud services
(listing the device ids and local keys of the account, and refreshing local
keys that Tuya has rotated) run without scanning a new QR code every time.
"""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .cloud import Cloud
from .const import (
    CLOUD_STORAGE_KEY,
    CLOUD_STORAGE_VERSION,
    DATA_AUTH_CACHE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _domain_data(hass: HomeAssistant) -> dict:
    """Return the integration's data store, creating it if needed."""
    return hass.data.setdefault(DOMAIN, {})


def _store(hass: HomeAssistant) -> Store:
    """Return the store holding the cloud session."""
    return Store(hass, CLOUD_STORAGE_VERSION, CLOUD_STORAGE_KEY, private=True)


async def async_save_session(hass: HomeAssistant) -> None:
    """Save the in memory cloud authentication to disk."""
    auth = _domain_data(hass).get(DATA_AUTH_CACHE)
    if not auth:
        await async_clear_session(hass)
        return
    _LOGGER.debug("Saving Tuya cloud session")
    await _store(hass).async_save(auth)


async def async_restore_session(hass: HomeAssistant) -> bool:
    """Restore a previously saved cloud session into memory.

    Returns True if an authentication is available afterwards.
    """
    data = _domain_data(hass)
    if data.get(DATA_AUTH_CACHE):
        return True
    stored = await _store(hass).async_load()
    if not stored:
        return False
    _LOGGER.debug("Restored Tuya cloud session from storage")
    data[DATA_AUTH_CACHE] = stored
    return True


async def async_clear_session(hass: HomeAssistant) -> None:
    """Forget the cloud session, both in memory and on disk."""
    _domain_data(hass)[DATA_AUTH_CACHE] = None
    await _store(hass).async_remove()


async def async_get_cloud(hass: HomeAssistant) -> Cloud | None:
    """Return an authenticated cloud interface, or None if not logged in."""
    if not await async_restore_session(hass):
        return None
    cloud = Cloud(hass)
    return cloud if cloud.is_authenticated else None
