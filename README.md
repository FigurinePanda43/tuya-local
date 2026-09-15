![logo](custom_components/tuya_local/brand/icon.svg) 

> **This is a personal fork of [make-all/tuya-local](https://github.com/make-all/tuya-local).**
> On top of the upstream integration it adds:
>
> - the Tuya cloud login is saved, so the QR code only needs to be scanned once
>   rather than once per Home Assistant run;
> - a `tuya_local.list_cloud_devices` action, which reports the device id and
>   local key of every device in your Smart Life or Tuya account, so the Tuya
>   IoT developer portal is no longer needed to find them;
> - a `tuya_local.refresh_local_keys` action, which repairs configured devices
>   after Tuya has changed their local key.
>
> Both are described under [Cloud actions](#cloud-actions) below. Everything
> else is unchanged from upstream.

Please report any [issues](https://github.com/make-all/tuya-local/issues) and feel free to raise [pull requests](https://github.com/make-all/tuya-local/pulls) with the upstream project, for anything that is not specific to this fork.
[Many others](https://github.com/make-all/tuya-local/blob/main/ACKNOWLEDGEMENTS.md) have contributed their help already.

[![BuyMeCoffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/jasonrumney)

This is a Home Assistant integration to support devices running Tuya
firmware without going via the Tuya cloud.  Devices are supported
over WiFi, limited support for devices connected via hubs is available.

Note that many Tuya devices seem to support only one local connection.
If you have connection issues when using this integration, ensure that
other integrations offering local Tuya connections are not configured
to use the same device, mobile applications on devices on the local
network are closed, and no other software is trying to connect locally
to your Tuya devices.

Using this integration does not stop your devices from sending status
to the Tuya cloud, so this should not be seen as a security measure,
rather it improves speed and reliability by using local connections,
and may unlock some features of your device, or even unlock whole
devices, that are not supported by the Tuya cloud API.

A similar but unrelated integration is
[rospogrigio/localtuya](https://github.com/rospogrigio/localtuya/), if
your device is not supported by this integration, you may find it
easier to set up using that, or another more recent fork, as an alternative.


---

## Installation

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

### Via HACS

The [Home Assistant Community Store (HACS)](https://hacs.xyz/) is the easiest
way to install third-party integrations. This fork is not part of the HACS
default store, so it has to be added as a [custom
repository](https://hacs.xyz/docs/faq/custom_repositories): in HACS, open the
menu in the top right corner, choose **Custom repositories**, enter
`https://github.com/FigurinePanda43/tuya-local` and select the **Integration**
category. Tuya Local can then be downloaded like any other HACS integration.
The button below does the same thing, if you have My Home Assistant configured.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FigurinePanda43&repository=tuya-local&category=integration)

Expect the download to take a while. Repositories in the HACS default store are
pre-indexed, but a custom repository is not, so HACS fetches the integration
file by file, and this one is made up of more than 1800 files, nearly all of
them device configurations.

### Manually

If the HACS download does not complete, the integration can be installed by
hand instead. Copy the `custom_components/tuya_local` directory of this
repository into the `custom_components` directory of your Home Assistant
configuration, so that you end up with
`/config/custom_components/tuya_local/manifest.json`, then restart Home
Assistant. Delete any previous `tuya_local` directory first rather than copying
over it, so that no stale files are left behind.

Installing this way means HACS will not offer updates for the integration, so
repeat the copy to update it.

## Configuration

After installing, you can easily configure your devices using the Integrations configuration UI.  Go to Settings / Devices & Services and press the Add Integration button, or click the shortcut button below (requires My Homeassistant configured).

[![Add Integration to your Home Assistant
instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tuya_local)

### Choose your configuration path

There are two options for configuring a device:
- You can login to Tuya cloud with the Tuya or SmartLife app and retrieve a list of devices and the necessary local connection data.
- You can provide all the necessary information manually [as per the instructions in DEVICES_DETAILS.md](DEVICE_DETAILS.md#finding-your-device-id-and-local-key).

The first choice essentially automates all the manual steps of the second and without needing to create a Tuya IOT developer account. This is especially important now that Tuya has started time limiting access to a key data access capability in the IOT developer portal to only a month with the ability to refresh the trial of that only every 6 months.

The cloud assisted choice will guide you through authenticating, choosing a device to add from the list of devices associated with your Tuya account, locate the device on your local subnet and then drop you into [Stage One](#stage-one) with fully populated data necessary to move forward to [Stage Two](#stage-two).

The Tuya login is saved by the integration, so you only need to scan the QR
code once, and can then add further devices without authenticating again, even
after restarting Home Assistant. The token does eventually expire, in which case
you will be asked to scan a new QR code. Choosing "cloud fresh login" instead of
"cloud" discards the saved login, which is what you need if you want to switch
to a different Tuya account.

The saved login is also what the [cloud actions](#cloud-actions) below use to
look up device ids and local keys without the Tuya IoT developer portal.

### Stage One

The first stage of configuration is to provide the information needed to connect to the device.

When using the cloud assisted config, the device id and local key will be pre-filled from the cloud, and the IP address will also be filled if local discovery is not blocked by other integrations or a complex network setup. Otherwise, see [DEVICE_DETAILS.md](DEVICE_DETAILS.md) for instructions on how to find the info.

#### host

&nbsp;&nbsp;&nbsp;&nbsp;_(string) (Required)_ IP or hostname of the device.

#### device_id

&nbsp;&nbsp;&nbsp;&nbsp;_(string) (Required)_ Device ID retrieved

#### local_key

&nbsp;&nbsp;&nbsp;&nbsp;_(string) (Required)_ Local key retrieved

Note that each time you pair the device, the local key changes, so if you obtained the local key using the instructions below, then re-paired with your manufacturer's app, then the key will have changed already. For a device that is already set up, the [`tuya_local.refresh_local_keys`](#tuya_localrefresh_local_keys) action will fetch the new key and update the configuration for you.

#### protocol_version

&nbsp;&nbsp;&nbsp;&nbsp;_(string or float) (Required)_ Valid options are "auto", 3.1, 3.2, 3.3, 3.4, 3.5, 3.22.  If you aren't sure, choose "auto", but some 3.2, 3.22 and maybe 3.4 devices may be misdetected as 3.3 (or vice-versa), so if your device does not seem to respond to commands reliably, try selecting between those protocol versions. Protocol 3.22 is a special case, that enables tinytuya's "device22" detection with protocol 3.3. Previously we let tinytuya auto-detect this, but it was found to sometimes misdetect genuine 3.3 devices as device22 which stops them receiving updates, so an explicit version was added to enable the device22 detection.

At the end of this step, an attempt is made to connect to the device and see if
it returns any data. For tuya protocol version 3.1 devices, the local key is
only used for sending commands to the device, so if your local key is
incorrect the setup will appear to work, and you will not see any problems
until you try to control your device.  For more recent Tuya protocol versions,
the local key is used to decrypt received data as well, so an incorrect key
will be detected at this step and cause an immediate failure.


### Stage Two

The second stage of configuration is to select which device you are connecting.
The list of devices offered will be limited to devices which appear to be
at least a partial match to the data returned by the device.

#### type

&nbsp;&nbsp;&nbsp;&nbsp;_(string) (Optional)_ The type of Tuya device.
Select from the available options.

The list presented is filtered to exclude devices that definitely do not match among the 1000+ supported devices. If a device config you expected is not shown, you may have a different firmware version, so the best way to report this is as a new device.

If you pick the wrong type, you will need to delete the device and set
it up again. This is because different types of devices create different
entities, so changing the device type without deleting everything is
not advisable.

### Stage Three

The final stage is to choose a name for the device in Home Assistant.

If you have multiple devices of the same type, you may want to change
the name to make it easier to distinguish them.

#### name

&nbsp;&nbsp;&nbsp;&nbsp;_(string) (Required)_ Any unique name for the
device.  This will be used as the base for the entity names in Home
Assistant.

---

## Cloud actions

Two actions use the saved Tuya cloud login to get device information that
otherwise requires a Tuya IoT developer account. Both need you to have logged
in at least once through the cloud assisted config flow above.

### `tuya_local.list_cloud_devices`

Returns the devices in your Smart Life or Tuya account, with the `local_key`,
`id`, `uuid`, `node_id`, `product_id`, `product_name`, `category`, `ip`,
`online` and `support_local` reported by the cloud, plus `configured` saying
whether the device is already set up in this integration.

Run it from **Developer tools** > **Actions**, in YAML mode, and the response
is shown in the UI:

```yaml
action: tuya_local.list_cloud_devices
data: {}
```

Pass a `device_id` (which also matches a uuid or node id) to report a single
device:

```yaml
action: tuya_local.list_cloud_devices
data:
  device_id: bfa8c98xxxxxxxxxxxxxxx
```

This is useful for devices that are not yet supported here, or for setting up
another local integration, since it gives you the same information the
developer portal would.

### `tuya_local.refresh_local_keys`

Tuya changes the local key each time a device is paired in the app, which
silently stops local control from working. This action fetches the current keys
from your account and updates the configuration of any device whose key has
changed:

```yaml
action: tuya_local.refresh_local_keys
data:
  dry_run: false
```

The response lists the devices under `updated`, `unchanged` and `not_found`
(the last being configured devices that are not in the cloud account). Set
`dry_run: true` to see which keys have changed without altering the
configuration.

## Device support

A list of currently supported devices can be found in the [DEVICES.md](https://github.com/make-all/tuya-local/blob/main/DEVICES.md) file.

Note that devices sometimes get firmware upgrades, or incompatible
versions are sold under the same model name, so it is possible that
the device will not work despite being listed.

Battery powered devices such as door and window sensors, smoke alarms
etc which do not use a hub are not possible to support locally, due
to the power management that they need to do to get acceptable battery
life. In some cases that may also apply when a device that can be
either battery or USB powered is plugged into USB. If you cannot gather
Warning level logs with dps listed when attempting to set it up, then it
will likely not work with this integration.

Hubs are currently supported, but with limitations.  Each connection
to a sub device uses a separate network connection, but like other
Tuya devices, hubs are usually limited in the number of connections
they can handle, with typical limits being 1 or 3, depending on the specific
Tuya module they are using.  This severely limits the number of sub devices
that can be connected through this integration.

Sub devices should be added using the `device_id`, `address` and `local_key`
of the hub they are attached to, and the `node_id` of the sub-device. If there
is no `node_id` listed, try using the `uuid` instead.

Tuya Zigbee devices are usually standard zigbee devices, so as an
alternative to this integration with a Tuya hub, you can use a
supported Zigbee USB stick or Wifi hub with
[ZHA](https://www.home-assistant.io/integrations/zha/#compatible-hardware)
or [Zigbee2MQTT](https://www.zigbee2mqtt.io/guide/adapters/).

Some Tuya Bluetooth devices can be supported directly by the
[tuya_ble](https://github.com/PlusPlus-ua/ha_tuya_ble/) integration.

Some Tuya hubs now support Matter over WiFi, and this can be used as an
alternative to this integration for connecting the hub and sub-devices
to Home Assistant. Other limitations will apply to this, so you might want
to try both, and only use this integration for devices that are not working
properly over Matter.

Tuya IR hubs that expose general IR remotes as sub devices usually
expose them as one way devices (send only) except in learning mode,
if they expose them at all locally. In general, Tuya IR hubs are only
useful for HA's built in IR support, not for any Tuya features such as their
predefined (cloud only) device database, or climate device simulation.

## Contributing

Documentation on building a device configuration file is in [/custom_components/tuya_local/devices/README.md](https://github.com/make-all/tuya-local/blob/main/custom_components/tuya_local/devices/README.md)

If your device is not listed, you can find the information required to add a configuration for it in the following locations:

1. When attempting to add the device, if it is not supported, you will either get a message saying the device cannot be recognised at all, or you will be offered a list of devices that are partial matches. You can cancel the process at this point, and look in the Home Assistant log - there should be a message there containing the current data points (dps) returned by the device.
2. If you have signed up for [iot.tuya.com](https://iot.tuya.com/), you should have access to the API Explorer under "Cloud". Under "Device Control" there is a function called "Query Things Data Model", which returns the dp id in addition to range information that is needed for integer and enum data types.

If you file an issue to request support for a new device, please include the following information:

1. Logs from this integration showing the LOCAL DPS actually received from the device.
2. Identification of the device, such as model and brand name.
3. As much information on the datapoints you can gather using the above methods.
4. If manuals or webpages are available online, links to those help understand how to interpret the technical info above - even if they are not in English automatic translations can help, or information in them may help to identify identical devices sold under other brands in other countries that do have English or more detailed information available.

If you submit a pull request, please understand that the config file naming and details of the configuration may get modified before release - for example if your name was too generic, I may rename it to a more specific name, or conversely if the device appears to be generic and sold under many brands, I may change the brand specific name to something more general.  So it may be necessary to remove and re-add your device once it has been integrated into a release.

---

## Offline operation issues

Many Tuya devices will stop responding if unable to connect to the
Tuya servers for an extended period.  Reportedly, some devices act
better offline if DNS as well as TCP connections is blocked.

## General issues

Many Tuya devices do not handle multiple commands sent in quick
succession.  Some will reboot, possibly changing state in the process,
others will go offline for 30s to a few minutes if you overload them.
There is some rate limiting to try to avoid this, but it is not
sufficient for some devices, and may not work across entities where
you are sending commands to multiple entities on the same device.  The
rate limiting also combines commands, which not all devices can
handle. If you are sending commands from an automation, it is best to
add delays between commands - if your automation is for multiple
devices, it might be enough to send commands to other devices first
before coming back to send a second command to the first one, or you
may still need a delay after that.  The exact timing depends on the
device, so you may need to experiment to find the minimum delay that
gives reliable results.

Most devices can handle multiple commands in a single message, so for
entity platforms that support it (eg climate `set_temperature` can
include presets, lights pretty much everything is set through
`turn_on`) multiple settings are sent at once.  But some devices do
not like this and require all commands to set only a single dp at a
time, so you may need to experiment with your automations to see
whether a single command or multiple commands (with delays, see above)
work best with your devices.

When adding devices, some devices that are detected as protocol version
3.3 at first require version 3.2 to work correctly. Either they cannot be
detected, or work as read-only if the pprotocol is set to 3.3.

## Connecting to devices via hubs

If your device connects via a hub (eg. battery powered water timers) you have to provide the following info when adding a new device:

- Device id (uuid): this is the **hub's** device id
- IP address or hostname: the **hub's** IP address or hostname
- Local key: the **hub's** local key
- Sub device id: the **actual device you want to control's** `node_id`. Note this `node_id` differs from the device id, you can find it with tinytuya as described below.

## Secure locks

Many locks are designed with basic security controls to make remote unlocking
more difficult. This integration supports the standard BLE lock model from Tuya
which uses a pair of dps (60: `remote_no_pd_seykey`, 61: `remote_no_dp_key`)
to share a key between the app and the lock during the pairing phase.
If you have access to the Tuya developer portal, you can eavesdrop on the
second of these messages when the app is used to unlock the lock remotely.
If you capture the value sent by the app, then you can decode it using a base64
decoder such as https://base64decode.org.
The format has 4 bytes of binary data, followed by an 8 digit ASCII numeric
code, followed by 3 or 4 more bytes of binary data.

The 8 digit numeric code from the first app that was paired should work for
unlocking the lock.

Although this is documented in the BLE lock documentation from Tuya, Zigbee
and WiFi locks often use the same naming for datapoints, which may be
compatible with this scheme.

## IR/RF blasters

Tuya IR and RF blasters are exposed as remote entities and support learning and
sending commands via the standard Home Assistant remote services. IR blasters are
also exposed as general `infrared` emitters, and learned commands can be sent to
other `infrared` emitters using the tuya-local specific "Send Learned IR command"
service.

### Learning commands

Use the `remote.learn_command` service with:
- `command`: the name to store the command under (e.g. `power`)
- `device`: a name for the appliance being controlled (e.g. `TV`)
- `command_type`: set to `rf` for RF remotes, omit or leave blank for IR

The integration will put the blaster into learning mode and wait up to 30 seconds
for you to press a button on the original remote. The learned code is stored
persistently and survives restarts.

### Sending commands

Using the `infrared` platform, you can send known IR commands using
other HA integrations, including
[HAIR](https://github.com/DAB-LABS/HAIR), a custom integration for
learning remote commands via an ESPHome receiver and sending them to
any supported `infrared` emitter.

To send learned commands using the same `remote` entity, you use the
`remote.send_command` service with the same `command` and `device`
values used when learning. You can also send known Tuya codes directly
without learning first:

- **IR inline code**: prefix with `b64:` followed by the base64-encoded IR code
- **RF inline code**: prefix with `rf:` followed by the base64-encoded RF code

There is also a special `send_learned_ir_command` service for sending commands
learned by the `remote` entity to any `infrared` emitter (including non-Tuya ones).
To use this, you must specify the `remote` entity the learned command was saved
with, the target `infrared` emitter entity, and the `command` and optional `device`
the command was saved as.


### UI

If you would like to expose the learnt commands as buttons in the user interface
you might want to take a look at the [Remote buttons](https://github.com/kongo09/remote_buttons)
integration, which is compatible with Tuya Local.

## Pet feeders

Many pet feeders expose an encoded **Meal plan** setting via a text entity. By default this is disabled, but you can enable it under the Device settings in HA. When enabled many pet feeders share the same underlying format, which is supported by the [FrederikM97/mealplan-card](https://github.com/FredrikM97/mealplan-card) custom card.

## Contributing

Beyond contributing device configs, here are some areas that could benefit from more hands:

1. Unit tests. This integration is mostly unit-tested thanks to the upstream project, but there are a few more to complete. Focus on unit tests is on python code, the current coverage is summarised in reports on github, but to get full coverage details you can run the tests yourself.
2. Once unit tests are complete, the next task is to properly evaluate against the Home Assistant quality scale.
3. Discovery. Local discovery is currently limited to finding the IP address in the cloud assisted config. Performing discovery in background would allow notifications to be raised when new devices are noticed on the network, and would provide a productKey for the manual config method to use when matching device configs.

