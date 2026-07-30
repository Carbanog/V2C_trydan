# V2C Trydan para Home Assistant

> [!IMPORTANT]
> **Aviso de Transparencia:** Este repositorio es un **fork independiente** mantenido por **Carbanog**. No soy programador profesional; soy un usuario con nociones básicas que ha desarrollado esta versión principalmente con la ayuda de **IA** para cubrir necesidades personales de estabilidad que no encontraba en otras versiones. Se ofrece tal cual, sin garantías ni soporte oficial. Úsala bajo tu propia responsabilidad.

### 🛠️ Estado del Proyecto

* **Mantenimiento:** Activo (para uso personal y experimentación).
* **Objetivo principal:** Estabilidad total en redes PLC/WiFi mediante un **Data Coordinator** (una sola petición para todos los sensores).
* **Base Original:** Basado en el trabajo de [Rain1971](https://github.com/Rain1971/V2C_trydant), actualmente discontinuado.

-----

# CARGADOR V2C TRYDAN para HOME ASSISTANT

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/Carbanog/V2C_trydan.svg)](https://github.com/Carbanog/V2C_trydan/releases/)
[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/Carbanog/V2C_trydan/blob/main/README.md)
[![es](https://img.shields.io/badge/lang-es-yellow.svg)](https://github.com/Carbanog/V2C_trydan/blob/main/README.es.md)

Esta integración permite controlar y monitorizar tu cargador **V2C Trydan** de forma 100% local a través de su interfaz HTTP. Se ha reescrito el núcleo para minimizar las peticiones al cargador, evitando bloqueos y errores de conexión frecuentes en instalaciones con PLC.

## 🆚 Mejoras respecto a la integración oficial y al original

* **Sin dependencias externas** — no usa `pytrydan`, va directo al dispositivo via HTTP
* **Estabilidad en PLC** — reintentos nativos, timeouts de 20s, logs silenciosos en fallos puntuales
* **Más entidades** — Binary Sensors, ContractedPower, ChargeState con texto descriptivo y más diagnósticos
* **Services documentados** — con sliders en la UI de HA
* **Arquitectura moderna** — usa `ConfigEntry.runtime_data`, sin `hass.data` legacy
* **Fix de JSON** — repara respuestas malformadas del firmware del cargador automáticamente
* **Peticiones serializadas** — las lecturas y órdenes nunca se solapan, algo
  especialmente importante en enlaces PLC o WiFi débiles
* **IP reconfigurable** — la dirección puede cambiarse desde la UI sin eliminar
  la integración ni perder nombres, áreas o automatizaciones
* **Varios cargadores** — las acciones permiten seleccionar el cargador de destino
* **Diagnósticos seguros** — Home Assistant puede generar un informe que oculta
  IP, SSID e identificador del equipo

## 📋 Requisitos Previos

* **IP Estática:** Es **obligatorio** asignar una IP fija (estática) a tu cargador V2C Trydan desde la configuración de tu router. Si la IP cambia, la integración dejará de funcionar.
* **Firmware actualizado:** Se recomienda tener el cargador actualizado a la última versión oficial de V2C.

## 🚀 Instalación

1. **HACS:** Añade este repositorio como "Repositorio Personalizado" de tipo
   "Integración" en HACS.
2. **Reinicia:** Reinicia Home Assistant.
3. **Configuración:** Ve a Ajustes → Dispositivos y Servicios → Añadir Integración → Busca **V2C Trydan**.
4. **IP:** Introduce la IP estática de tu cargador.

-----

## 📊 Entidades Disponibles

### Controles (Acción)

| Nombre | Tipo | Descripción |
| :--- | :--- | :--- |
| `Pausar Carga` | Switch | Pausa o reanuda la carga actual. |
| `Bloquear Cargador` | Switch | Bloquea el hardware del cargador. |
| `Carga Dinámica` | Switch | Activa/Desactiva la modulación dinámica de potencia. |
| `Intensidad de Carga` | Number | Ajusta los Amperios manualmente (6A - 32A). |
| `Intensidad Máxima` | Number | Límite superior para el modo dinámico. |
| `Intensidad Mínima` | Number | Límite inferior para el modo dinámico. |
| `Modo de Potencia Dinámica` | Select | Selector de modos (Exclusivo Solar, Red+FV, Mínimo, etc.). |

### 🔌 Sensores Binarios (Estados)
Ideales para disparar automatizaciones (Encendido/Apagado).

| Nombre | Icono | Descripción |
|---|---|---|
| `Manguera Conectada` | 🔌 | On cuando el coche está enchufado físicamente. |
| `Cargando` | ⚡ | On solo cuando hay flujo de energía hacia el coche. |
| `Listo para Cargar` | ✅ | On cuando el cargador está operativo y sin errores. |

### 📈 Monitoreo (Sensores)

| Nombre | Clase | Descripción |
| :--- | :--- | :--- |
| `Potencia de Carga` | Power (W) | Potencia real que está entrando al coche. |
| `Energía de Carga` | Energy (kWh) | Energía acumulada en la sesión actual. |
| `Estado de Carga` | Enum | Manguera desconectada, Conectada o Cargando. |
| `Tiempo de Carga` | Tiempo (s) | Duración de la sesión actual. |
| `Potencia de Casa` | Power (W) | Consumo total de la vivienda. |
| `Potencia Fotovoltaica` | Power (W) | Producción de placas solares. |
| `Potencia de Batería` | Power (W) | Potencia de batería doméstica. |
| `Intensidad de Carga` | Current (A) | Intensidad actual de carga. |
| `Intensidad Mínima` | Current (A) | Límite inferior configurado. |
| `Intensidad Máxima` | Current (A) | Límite superior configurado. |
| `Voltaje de Instalación` | Voltage (V) | Voltaje real en la línea. |
| `Potencia Contratada` | Power (W) | Potencia contratada con la compañía eléctrica. |

### 🔧 Diagnóstico

| Nombre | Descripción |
| :--- | :--- |
| `Versión de Firmware` | Versión del firmware del cargador. |
| `Dirección IP` | IP actual del cargador. |
| `Red WiFi` | SSID de la red conectada. |
| `Estado de Señal WiFi` | Calidad de la señal. |
| `ID del Dispositivo` | Identificador único del cargador. |
| `Estado Listo` | Estado interno de preparación. |
| `Error de Medidor` | Código de error del medidor. |
| `Carga Dinámica` | Estado del modo dinámico. |
| `Modo de Potencia Dinámica` | Modo dinámico activo. |
| `Cargador Bloqueado` | Estado de bloqueo. |
| `Carga Pausada` | Estado de pausa. |
| `Pausa Dinámica` | Estado de pausa dinámica. |
| `Temporizador` | Estado del temporizador interno. |

-----

## 🛠️ Servicios para Automatizaciones

| Servicio | Descripción |
| :--- | :--- |
| `v2c_trydan.set_intensity` | Ajusta los amperios de carga (6-32A). |
| `v2c_trydan.set_min_intensity` | Ajusta la intensidad mínima (6-32A). |
| `v2c_trydan.set_max_intensity` | Ajusta la intensidad máxima (6-32A). |
| `v2c_trydan.set_dynamic_power_mode` | Cambia el modo de potencia dinámica (0-5). |

Todos los servicios aparecen con descripción y sliders en **Herramientas para Desarrolladores → Acciones**.
Cuando hay más de un cargador configurado, selecciona el cargador en el campo
`config_entry_id`. Para automatizaciones nuevas se recomienda actuar directamente
sobre las entidades `number`, `select` y `switch`; las acciones anteriores se
mantienen por compatibilidad.

-----

## ⚙️ Parámetros Técnicos

| Parámetro | Valor |
| :--- | :--- |
| Intervalo de polling | 15 segundos |
| Timeout de conexión | 20 segundos |
| Reintentos por ciclo | 3 (con 2s de espera) |
| Concurrencia | Una única petición al cargador a la vez |

## 🔄 Cambiar la IP

En **Ajustes → Dispositivos y servicios → V2C Trydan**, abre el menú de la
integración y selecciona **Reconfigurar**. La integración comprueba que la nueva
dirección corresponde al mismo cargador antes de guardar el cambio.

## 🩺 Diagnóstico y solución de problemas

* Verifica que `http://IP_DEL_CARGADOR/RealTimeData` responde desde la misma red.
* Reserva la IP en el servidor DHCP; no es necesario borrar la integración si la
  dirección cambia, ya que puede reconfigurarse.
* Desde el menú de la integración, descarga los diagnósticos para adjuntarlos a
  una incidencia. Los datos de red y el identificador se ocultan automáticamente.
* Los fallos temporales dejan las entidades como no disponibles y Home Assistant
  vuelve a intentarlo; no es necesario reiniciar.

La arquitectura y las reglas para contribuir están documentadas en
[`docs/architecture.md`](docs/architecture.md).

-----

## ⚖️ Créditos y Agradecimientos

* A **Rain1971** por crear la base original de esta integración.
* A la comunidad de Home Assistant y las herramientas de **IA** por ayudar a un "no programador" a mantener vivo este proyecto para uso personal.

-----
