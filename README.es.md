# V2C Trydan para Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://www.hacs.xyz/)
[![GitHub release](https://img.shields.io/github/v/release/Carbanog/V2C_trydan.svg)](https://github.com/Carbanog/V2C_trydan/releases/)
[![English](https://img.shields.io/badge/lang-en-red.svg)](README.md)
[![Español](https://img.shields.io/badge/lang-es-yellow.svg)](README.es.md)

Integración local para monitorizar y controlar cargadores **V2C Trydan** desde
Home Assistant. Está diseñada especialmente para conexiones PLC o Wi-Fi que
necesitan peticiones espaciadas, serializadas y tolerantes a fallos puntuales.

> [!IMPORTANT]
> Proyecto comunitario independiente, sin relación oficial con V2C. Deriva del
> trabajo original de [Rain1971](https://github.com/Rain1971/V2C_trydant) y se
> proporciona sin garantías. Prueba las versiones beta en una instalación de
> Home Assistant de pruebas antes de utilizarlas en producción.

## Funciones destacadas

- Comunicación HTTP completamente local y sin dependencias Python externas.
- Una lectura coordinada cada 15 segundos para todas las entidades.
- Reintentos y peticiones serializadas para proteger conexiones débiles.
- Controles de pausa, bloqueo, intensidad y luces compatibles.
- **Energía completa de la sesión**, incluso cuando OCPP o la aplicación pausa,
  reanuda y reinicia el contador parcial del cargador.
- Persistencia de la sesión entre reinicios de Home Assistant.
- Estado de carga descriptivo y detección inmediata de problemas del medidor.
- Cambio de IP desde la interfaz sin recrear entidades ni automatizaciones.
- Diagnósticos que ocultan IP, SSID e identificadores sensibles.
- Blueprints y ejemplos de panel opcionales.

## Instalación

1. En HACS, añade `https://github.com/Carbanog/V2C_trydan` como repositorio
   personalizado de tipo **Integración**.
2. Instala V2C Trydan y reinicia Home Assistant.
3. Abre **Ajustes → Dispositivos y servicios → Añadir integración**.
4. Busca **V2C Trydan** e introduce la dirección IP local del cargador.

Es muy recomendable reservar esa dirección en el DHCP del router. Si cambia,
utiliza **Reconfigurar** en el menú de la integración; no es necesario borrarla.

## Experiencia inicial deliberadamente sencilla

Una instalación nueva habilita únicamente las entidades de uso habitual. Los
ajustes internos, datos solares, batería doméstica y diagnóstico detallado siguen
disponibles desde la página del dispositivo, pero comienzan deshabilitados.

Deshabilitar una entidad en Home Assistant **no cambia la configuración del
cargador**. Por ejemplo, la carga dinámica continuará activa si así está
configurada en la aplicación V2C.

### Habilitadas inicialmente

| Entidad | Tipo | Uso |
| --- | --- | --- |
| Potencia de carga | Sensor | Potencia entregada al vehículo. |
| Energía de carga | Sensor | Contador parcial informado por el firmware. |
| Energía de la sesión | Sensor | Total local que suma todos los tramos hasta la siguiente conexión. |
| Estado de carga | Sensor | Estado detallado del cargador. |
| Tiempo de carga | Sensor | Tiempo indicado por el firmware. |
| Potencia de casa | Sensor | Consumo medido por el sistema dinámico. |
| Manguera conectada | Sensor binario | Disparador fiable para automatizaciones de sesión. |
| Cargando | Sensor binario | Indica flujo de carga activo. |
| Problema del medidor | Sensor binario | Advierte de cualquier código de error del medidor. |
| Pausar carga | Interruptor | Pausa o reanuda manualmente. |
| Bloquear cargador | Interruptor | Controla el bloqueo del cargador. |
| Intensidad de carga | Número | Ajusta la intensidad manual entre 6 y 32 A. |
| Luz del cargador | Luz | Encendido y apagado, si el firmware lo permite. |
| Luz del logotipo | Luz | Encendido y brillo, si el firmware lo permite. |

### Avanzadas o de diagnóstico

Permanecen deshabilitadas inicialmente: potencia fotovoltaica y de batería,
tensión, potencia contratada, intensidad mínima y máxima, carga dinámica, modo
dinámico, temporizador, pausa dinámica, estados internos duplicados, código del
medidor, firmware, IP, SSID, señal Wi-Fi e identificador del dispositivo.

Se pueden habilitar individualmente en **Ajustes → Dispositivos y servicios →
Entidades**. Los cambios de valores predeterminados no deshabilitan entidades que
un usuario ya hubiera activado en una versión anterior.

## Energía de la sesión

`Energía de Carga` reproduce el valor `ChargeEnergy` del cargador. Algunos
controladores externos, incluido OCPP, pueden dividir una conexión física en
varios tramos y reiniciar ese valor entre pausas.

`Energía de la Sesión` suma los incrementos de todos esos tramos mientras la
manguera permanece conectada. El resultado se conserva al desconectar para que
una automatización pueda leerlo posteriormente y se reinicia al conectar un
nuevo vehículo. Su estado se guarda periódicamente sin depender del Recorder.

El botón avanzado `Reiniciar Energía de Sesión` permite corregir manualmente un
caso excepcional sin volver a contar el valor parcial anterior.

> [!NOTE]
> Si Home Assistant permanece apagado durante varios tramos completos que el
> cargador posteriormente borra, la integración no puede recuperar esa energía.

## Automatizaciones reutilizables

Los blueprints no se instalan ni activan automáticamente. Se importan desde
**Ajustes → Automatizaciones y escenas → Blueprints → Importar blueprint**:

- [Resumen y avisos de sesión](blueprints/automation/session_summary.yaml):
  acciones configurables al iniciar y finalizar, con variables para kWh,
  porcentaje añadido estimado, coste y autonomía.
- [Alerta de potencia elevada](blueprints/automation/high_power_alert.yaml):
  umbral, duración y acciones configurables.

La capacidad de batería, eficiencia, precio y autonomía pertenecen al vehículo o
al contrato, no al cargador. Por eso forman parte del blueprint y no de las
entidades principales de la integración. Los porcentajes calculados representan
**energía añadida estimada**, no el estado real de carga comunicado por el coche.

## Paneles de ejemplo

- [Panel nativo](dashboards/native.es.yaml): solo utiliza tarjetas incluidas en
  Home Assistant.
- [Panel Mushroom](dashboards/mushroom.es.yaml): requiere Mushroom y Mini Graph
  Card.

Copia el YAML en una tarjeta manual y adapta los identificadores si Home
Assistant generó nombres diferentes. Estos ejemplos no modifican ningún panel
automáticamente.

## Acciones compatibles

| Acción | Descripción |
| --- | --- |
| `v2c_trydan.set_intensity` | Establece la intensidad manual. |
| `v2c_trydan.set_min_intensity` | Establece el límite dinámico inferior. |
| `v2c_trydan.set_max_intensity` | Establece el límite dinámico superior. |
| `v2c_trydan.set_dynamic_power_mode` | Cambia la estrategia dinámica entre 0 y 5. |

Para automatizaciones nuevas se recomienda controlar directamente las entidades
`number`, `select` y `switch`. Las acciones se conservan por compatibilidad y
permiten seleccionar el cargador cuando existe más de uno.

> [!WARNING]
> La aplicación V2C ofrece configuraciones que la API local no expone, como
> límites horarios de potencia. No cambies carga dinámica, temporizador o modos
> avanzados desde Home Assistant si forman parte de la protección de tu
> instalación o si un proveedor controla la carga mediante OCPP.

## Parámetros técnicos

| Parámetro | Valor |
| --- | --- |
| Actualización principal | 15 segundos |
| Timeout de lectura | 20 segundos |
| Reintentos | 3, con 2 segundos entre intentos |
| Concurrencia | Una petición por cargador |
| Lecturas LED opcionales | Cada 60 segundos y con caché |
| Persistencia de sesión | Al cambiar la conexión y durante cargas prolongadas |

## Diagnóstico

- Comprueba `http://IP_DEL_CARGADOR/RealTimeData` desde la misma red.
- Los fallos temporales dejan las entidades no disponibles y Home Assistant
  vuelve a intentarlo automáticamente.
- Descarga el informe desde el menú de la integración para adjuntarlo a una
  incidencia; los datos sensibles se ocultan.
- Consulta [`docs/architecture.md`](docs/architecture.md) para conocer módulos,
  invariantes, compatibilidad y criterios de contribución.

## Créditos

- [Rain1971](https://github.com/Rain1971/V2C_trydant), autor de la base original.
- La comunidad de Home Assistant y las herramientas de IA utilizadas durante el
  desarrollo y la revisión del proyecto.
