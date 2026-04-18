# V2C Trydan for Home Assistant

> [!IMPORTANT]
> **Transparency Notice:** This repository is an **independent fork** maintained by **Carbanog**. I am not a professional programmer; I am an enthusiast with basic knowledge who has developed this version primarily with the help of **AI** to meet personal stability needs that I couldn't find in other versions. Provided as-is, without warranties or official support. Use at your own risk.

### 🛠️ Project Status

* **Maintenance:** Active (for personal use and experimentation).
* **Primary Goal:** Total stability on PLC/WiFi networks using a **Data Coordinator** (a single request for all sensors).
* **Original Base:** Based on the work by [Rain1971](https://github.com/Rain1971/V2C_trydant), currently discontinued.

-----

# V2C TRYDAN CHARGER for HOME ASSISTANT

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/Carbanog/V2C_trydan.svg)](https://github.com/Carbanog/V2C_trydan/releases/)
[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/Carbanog/V2C_trydan/blob/main/README.md)
[![es](https://img.shields.io/badge/lang-es-yellow.svg)](https://github.com/Carbanog/V2C_trydan/blob/main/README.es.md)

This integration allows you to control and monitor your **V2C Trydan** charger 100% locally via its HTTP interface. The core has been rewritten to minimize requests to the charger, avoiding crashes and connection errors frequent in PLC-based installations.

## 🆚 Improvements over the official integration and original fork

* **No external dependencies** — does not use `pytrydan`, communicates directly via HTTP
* **PLC stability** — native retries, 20s timeouts, silent logs on temporary failures
* **More entities** — Binary Sensors, ContractedPower, descriptive ChargeState and more diagnostics
* **Documented services** — with sliders in HA UI
* **Modern architecture** — uses `ConfigEntry.runtime_data`, no legacy `hass.data`
* **JSON fix** — automatically repairs malformed firmware responses

## 📋 Prerequisites

* **Static IP:** It is **mandatory** to assign a fixed (static) IP address to your V2C Trydan charger in your router settings. If the IP changes, the integration will stop working.
* **Updated Firmware:** It is recommended to have the charger updated to the latest official version from V2C.

## 🚀 Installation

1. **HACS:** Add this repository as a "Custom Repository" in HACS.
2. **Restart:** Restart Home Assistant.
3. **Configuration:** Go to Settings → Devices & Services → Add Integration → Search for **V2C Trydan**.
4. **IP:** Enter your charger's static IP address.

-----

## 📊 Available Entities

### Controls (Action)

| Name | Type | Description |
| :--- | :--- | :--- |
| `Pause Charge` | Switch | Pauses or resumes the current charging session. |
| `Lock Charger` | Switch | Locks the charger hardware. |
| `Dynamic Charge` | Switch | Enables/Disables dynamic power modulation. |
| `Charge Intensity` | Number | Adjust Amps manually (6A - 32A). |
| `Maximum Intensity` | Number | Upper limit for dynamic mode. |
| `Minimum Intensity` | Number | Lower limit for dynamic mode. |
| `Dynamic Power Mode` | Select | Mode selector (Exclusive Solar, Grid+PV, Minimum, etc.). |

### 🔌 Binary Sensors (Status)
Perfect for automation triggers (On/Off).

| Name | Icon | Description |
|---|---|---|
| `Cable Connected` | 🔌 | On when the car is physically plugged in. |
| `Charging` | ⚡ | On only when power is actively flowing. |
| `Ready to Charge` | ✅ | On when the charger is ready and has no errors. |

### 📈 Monitoring (Sensors)

| Name | Class | Description |
| :--- | :--- | :--- |
| `Charge Power` | Power (W) | Real-time power being delivered to the car. |
| `Charge Energy` | Energy (kWh) | Energy accumulated in the current session. |
| `Charge State` | Enum | Hose disconnected, Connected, or Charging. |
| `Charge Time` | Time (s) | Duration of the current session. |
| `House Power` | Power (W) | Total household consumption. |
| `Photovoltaic Power` | Power (W) | Solar production detected by the charger. |
| `Battery Power` | Power (W) | Home battery power. |
| `Charge Intensity` | Current (A) | Current charging intensity. |
| `Minimum Intensity` | Current (A) | Configured lower limit. |
| `Maximum Intensity` | Current (A) | Configured upper limit. |
| `Installation Voltage` | Voltage (V) | Real-time line voltage. |
| `Contracted Power` | Power (W) | Power contracted with the electricity company. |

### 🔧 Diagnostic

| Name | Description |
| :--- | :--- |
| `Firmware Version` | Charger firmware version. |
| `IP Address` | Current charger IP. |
| `WiFi Network` | Connected SSID. |
| `WiFi Signal Status` | Signal quality. |
| `Device ID` | Unique charger identifier. |
| `Ready State` | Internal readiness state. |
| `Meter Error` | Meter error code. |
| `Dynamic Charge` | Dynamic mode state. |
| `Dynamic Power Mode` | Active dynamic mode. |
| `Charger Locked` | Lock state. |
| `Charge Paused` | Pause state. |
| `Dynamic Pause` | Dynamic pause state. |
| `Timer` | Internal timer state. |

-----

## 🛠️ Services for Automations

| Service | Description |
| :--- | :--- |
| `v2c_trydan.set_intensity` | Sets charging amperage (6-32A). |
| `v2c_trydan.set_min_intensity` | Sets minimum intensity (6-32A). |
| `v2c_trydan.set_max_intensity` | Sets maximum intensity (6-32A). |
| `v2c_trydan.set_dynamic_power_mode` | Changes dynamic power mode (0-5). |

All services appear with descriptions and sliders in **Developer Tools → Actions**.

-----

## ⚙️ Technical Parameters

| Parameter | Value |
| :--- | :--- |
| Polling interval | 15 seconds |
| Connection timeout | 20 seconds |
| Retries per cycle | 3 (with 2s wait) |
| Errors before alert | 5 consecutive |

-----

## ⚖️ Credits and Acknowledgments

* To **Rain1971** for creating the original base for this integration.
* To the **Home Assistant community** and **AI tools** for helping a "non-programmer" keep this project alive for personal use.

-----
