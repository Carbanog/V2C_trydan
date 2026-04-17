Aquí tienes la traducción exacta al inglés para tu archivo `README.md`, manteniendo el mismo formato profesional y la nota de transparencia:

-----

# 🧪 V2C Trydan - Personal Testing Version

> [\!IMPORTANT]
> **Transparency Notice:** This repository is an **independent fork** maintained by **Carbanog**. I am not a professional programmer; I am an enthusiast with basic knowledge who has developed this version primarily with the help of **AI** to meet personal stability needs that I couldn't find in other versions.

### 🛠️ Project Status

  * **Maintenance:** Active (for personal use and experimentation).
  * **Primary Goal:** Total stability on PLC/WiFi networks using a **Data Coordinator** (a single request for all sensors).
  * **Original Base:** Based on the work by [Rain1971](https://github.com/Rain1971/V2C_trydant), currently discontinued by the author.

-----

# V2C TRYDAN CHARGER for HOME ASSISTANT

[](https://www.google.com/search?q=%5Bhttps://github.com/hacs/integration%5D\(https://github.com/hacs/integration\))
[](https://github.com/Carbanog/V2C_trydan/releases/)
[](https://github.com/Carbanog/V2C_trydan/blob/main/README.md)
[](https://github.com/Carbanog/V2C_trydan/blob/main/README.es.md)

This integration allows you to control and monitor your **V2C Trydan** charger 100% locally via its HTTP interface. The core has been rewritten to minimize requests to the charger, avoiding crashes and connection errors frequent in PLC-based installations.

## 📋 Prerequisites

  * **Static IP:** It is **mandatory** to assign a fixed (static) IP address to your V2C Trydan charger in your router settings. If the IP changes, the integration will stop working.
  * **Updated Firmware:** It is recommended to have the charger updated to the latest official version from V2C.

## 🚀 Installation

1.  **HACS:** Add this repository as a "Custom Repository" in HACS.
2.  **Restart:** Restart Home Assistant.
3.  **Configuration:** Go to Settings -\> Devices & Services -\> Add Integration -\> Search for **V2C Trydan**.
4.  **IP:** Enter your charger's static IP address.

-----

## 📊 Available Entities

Entities are now organized by categories (Control, Sensors, and Diagnostic):

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

### Monitoring (Sensors)

| Name | Class | Description |
| :--- | :--- | :--- |
| `Charge Power` | Power (W) | Real-time power being delivered to the car. |
| `Charge Energy` | Energy (kWh) | Energy accumulated in the current session. |
| `Charge State` | Text | Hose disconnected, Connected, or Charging. |
| `Charge Time` | Time | Duration of the current session. |
| `House Power` | Power (W) | Total household consumption. |
| `Photovoltaic Power` | Power (W) | Solar production detected by the charger. |
| `Installation Voltage`| Voltage (V) | Real-time line voltage. |

-----

## 🛠️ Services for Automations

This integration registers services that you can use in your automations:

  * `v2c_trydan.set_intensity`: Adjusts the Amperage.
  * `v2c_trydan.set_dynamic_power_mode`: Changes the mode (0-5).
  * `v2c_trydan.set_max_intensity` / `v2c_trydan.set_min_intensity`.

## 📸 Interface

Thanks to the categorization, you can create clean dashboards using entity cards or stack cards.

## ⚖️ Credits and Acknowledgments

  * To **Rain1971** for creating the original base for this integration.
  * To the **Home Assistant community** and **AI tools** for helping a "non-programmer" keep this project alive for personal use.

-----
