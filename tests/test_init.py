"""Test moonraker setup process."""

from unittest.mock import patch

import pytest
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.moonraker import (
    MoonrakerDataUpdateCoordinator,
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.moonraker.const import DOMAIN, METHODS

from .const import MOCK_CONFIG, MOCK_CONFIG_WITH_NAME


@pytest.fixture(name="bypass_connect_client", autouse=True)
def bypass_connect_client_fixture():
    """Skip calls to get data from API."""
    with patch("custom_components.moonraker.MoonrakerApiClient.start"):
        yield


async def test_setup_unload_and_reload_entry(hass):
    """Test entry setup and unload."""
    # Create a mock entry so we don't have to go through config flow

    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(
        hass.data[DOMAIN][config_entry.entry_id], MoonrakerDataUpdateCoordinator
    )

    # Reload the entry and assert that the data from above is still there.
    hass.config_entries._entries[config_entry.entry_id] = config_entry
    assert await async_reload_entry(hass, config_entry) is None
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(
        hass.data[DOMAIN][config_entry.entry_id], MoonrakerDataUpdateCoordinator
    )

    # Unload the entry and verify that the data has been removed
    assert await async_unload_entry(hass, config_entry)
    assert config_entry.entry_id not in hass.data[DOMAIN]


async def test_setup_unload_and_reload_entry_with_name(hass):
    """Test entry setup with name and unload."""
    # Create a mock entry so we don't have to go through config flow

    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_WITH_NAME, entry_id="test"
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(
        hass.data[DOMAIN][config_entry.entry_id], MoonrakerDataUpdateCoordinator
    )

    # Reload the entry and assert that the data from above is still there.
    hass.config_entries._entries[config_entry.entry_id] = config_entry
    assert await async_reload_entry(hass, config_entry) is None
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(
        hass.data[DOMAIN][config_entry.entry_id], MoonrakerDataUpdateCoordinator
    )

    # Unload the entry and verify that the data has been removed
    assert await async_unload_entry(hass, config_entry)
    assert config_entry.entry_id not in hass.data[DOMAIN]


async def test_async_send_data_exception(hass):
    """Test async_post_exception."""

    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)

    with (
        patch(
            "moonraker_api.MoonrakerClient.call_method",
            side_effect=UpdateFailed,
            return_value={"result": "error"},
        ),
        pytest.raises(UpdateFailed),
    ):
        coordinator = hass.data[DOMAIN][config_entry.entry_id]
        assert await coordinator.async_send_data(METHODS.PRINTER_EMERGENCY_STOP)

    assert await async_unload_entry(hass, config_entry)


async def test_setup_entry_exception(hass):
    """Test ConfigEntryNotReady when API raises an exception during entry setup."""
    with patch(
        "moonraker_api.MoonrakerClient.call_method",
        side_effect=Exception,
    ):
        config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
        config_entry.add_to_hass(hass)

        with pytest.raises(ConfigEntryNotReady):
            assert await async_setup_entry(hass, config_entry)


def load_data(endpoint, *args, **kwargs):
    """Load data."""
    if endpoint == "printer.info":
        return {"hostname": "mainsail"}

    raise Exception


async def test_failed_first_refresh(hass):
    """Test ConfigEntryNotReady when API raises an exception during entry setup."""
    with patch(
        "moonraker_api.MoonrakerClient.call_method",
        side_effect=load_data,
    ):
        config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
        config_entry.add_to_hass(hass)

        with pytest.raises(ConfigEntryNotReady):
            assert await async_setup_entry(hass, config_entry)


async def test_set_custom_gcode_service(hass):
    """Test custom GCode Services."""

    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    device_id = list(hass.data["device_registry"].devices.keys())

    # Test that the function call works in its entirety.
    with patch("moonraker_api.MoonrakerClient.call_method") as mock_sensors:
        await hass.services.async_call(
            DOMAIN,
            "send_gcode",
            {
                "device_id": device_id,
                "gcode": "STATUS",
            },
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_sensors.assert_called_once_with(
            METHODS.PRINTER_GCODE_SCRIPT.value, script="STATUS"
        )
