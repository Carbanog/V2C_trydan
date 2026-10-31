# V2C Trydan para Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Stable release](https://img.shields.io/github/v/release/Carbanog/V2C_trydan.svg)](https://github.com/Carbanog/V2C_trydan/releases/)
[English](README.md) · [Español](README.es.md) · [Français](README.fr.md)

Control local del cargador, seguimiento completo de las sesiones y herramientas
opcionales para gestionar la carga desde Home Assistant.

V2C Trydan combina controles de uso diario, sesiones persistentes entre pausas y
reinicios, diagnósticos y ejemplos de automatización. La rama beta incorpora
programación semanal por tarifas, sin depender de una comercializadora.

## Versiones y alcance

| Canal | Versión | Uso |
| --- | --- | --- |
| Estable | [1.3.3](https://github.com/Carbanog/V2C_trydan/releases/tag/v1.3.3) | Monitorización, controles y sesiones. |
| Beta voluntaria | [1.4.0b3](https://github.com/Carbanog/V2C_trydan/releases/tag/v1.4.0b3) | Añade programación opcional; solo para pruebas. |

La beta no sustituye la última estable. Sus funciones se describen aquí como
experimentales, no como disponibles en 1.3.3. Consulta el [historial de cambios](CHANGELOG.md).
Este repositorio se instala en HACS como **repositorio personalizado**; no se
presenta como incluido en su catálogo predeterminado.

## Funciones principales

- HTTP local: no necesita cuenta de V2C Cloud ni Octopus/OCPP para funcionar.
- Controles de pausa, bloqueo e intensidad; ajustes avanzados opcionales.
- Energía y tiempo activo de toda la sesión, incluso si el cargador reinicia
  contadores parciales durante las pausas.
- Restauración de la sesión después de reiniciar HA.
- Peticiones compartidas y serializadas, reintentos acotados y diagnóstico de
  comunicación, útiles también en conexiones PLC o Wi-Fi limitadas.
- Cambio de IP sin recrear la integración y diagnósticos con campos sensibles ocultos.
- Blueprints, paneles de ejemplo e interfaz en español, inglés y francés.

La tolerancia a fallos no elimina problemas de red ni garantiza la conexión.

## Requisitos y compatibilidad

Necesitas acceso HTTP local al Trydan desde HA. Reserva su dirección en el router
y comprueba `http://IP_DEL_CARGADOR/RealTimeData` desde la misma red.
No expongas esa API a Internet.

Las pruebas incluyen respuestas reales anonimizadas de firmware 2.4.6 y 2.5.1;
no equivalen a validar físicamente todas las versiones o instalaciones. Los campos
opcionales se detectan por su presencia, no solo por el número de firmware.
La versión 2.5.2 y los montajes Trydan Pro maestro/secundario no están validados.

Las medidas L1 de corriente y tensión aparecen si el cargador las devuelve.
El proyecto no expone medidas L2/L3 ni controles de luces; estos últimos se
retiraron por estados locales inconsistentes. El icono local requiere HA 2026.3
o posterior para mostrarse mediante la API de marcas.

## Instalación

[![Añadir a HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Carbanog&repository=V2C_trydan&category=integration)

1. Haz una copia de seguridad de HA.
2. Usa el botón o añade `https://github.com/Carbanog/V2C_trydan` en HACS como
   repositorio personalizado de tipo **Integración**.
3. Descarga la estable **1.3.3** y reinicia HA.
4. Ve a **Ajustes → Dispositivos y servicios → Añadir integración → V2C Trydan**.
5. Introduce la IP local del cargador.

Sin HACS: descarga una release y copia únicamente `custom_components/v2c_trydan`
en `/config/custom_components/v2c_trydan`; reinicia y sigue desde el paso 4.
No instales a la vez dos componentes que utilicen el dominio `v2c_trydan`.
Evita controladores o automatizaciones que envíen órdenes contradictorias.

## Actualizar, probar una beta y volver atrás

Actualiza desde HACS y reinicia HA. No borres ni recrees la integración: conserva
identificadores, personalizaciones y sesión almacenada. Si cambia la IP, utiliza
**Reconfigurar**. Para novedades de firmware, recarga la integración y descubre
los campos opcionales disponibles.

Para probar **1.4.0b3**, selecciónala expresamente al volver a descargar en HACS,
mostrando prereleases si hace falta, solo en el HA de pruebas. No habilites betas
en producción ni dejes dos instancias gobernando el mismo cargador.

Para volver a estable, revisa la pausa real, deshabilita la programación si la
estabas usando, descarga **1.3.3** y reinicia. Deshabilitar o descargar el módulo
no reanuda automáticamente la carga. Las entidades exclusivas de una beta pueden
quedar no disponibles al volver atrás; no se borran registros de usuario.

## Entidades y configuración

| Grupo | Contenido |
| --- | --- |
| Controles diarios | Pausar carga, bloquear cargador e intensidad manual. |
| Sesión | Energía de la sesión, tiempo activo y botón opcional de reinicio. |
| Monitorización | Potencia y energía parcial, estado de carga, potencia de casa, manguera y cargando. |
| Configuración opcional | Límites de intensidad, carga/modo dinámico, temporizador y pausa dinámica. |
| Diagnóstico y medidas opcionales | Medidor, firmware, red, Wi-Fi, estados internos, tensión y corriente L1. |
| Programación beta | Modo, tarifa actual y estado; solo al habilitar el módulo. |

En instalaciones nuevas los ajustes avanzados, datos solares/de batería y muchos
diagnósticos comienzan deshabilitados. Las elecciones de instalaciones existentes
se conservan. Habilita lo necesario en **Ajustes → Dispositivos y servicios →
Entidades**, incluyendo las deshabilitadas en el filtro. Habilitar una entidad
no modifica el cargador hasta utilizar su control.

Selecciona tu idioma en el perfil de HA. No se renombran identificadores existentes,
nombres personalizados ni textos escritos manualmente en paneles.

## Cómo se contabilizan las sesiones

**Energía de carga** es el contador parcial del cargador. **Energía de la sesión**
y **Tiempo activo de la sesión** acumulan los incrementos entre pausas y reinicios
de esos contadores. No dependen de Octopus: también sirven con carga manual.

Al desenchufar se conservan los totales; al detectar la siguiente conexión se
inicia una sesión nueva. Un fallo del cargador no se interpreta como una nueva
conexión. El estado se guarda independientemente de Recorder.
El botón opcional de reinicio permite corregir una sesión excepcional.

La presentación usa dos decimales; el tiempo se conserva internamente en segundos.
Si una entidad antigua muestra segundos, puedes elegir horas en su configuración
sin reiniciar el acumulado. La energía borrada por el cargador mientras HA estaba
apagado no puede reconstruirse.

## Programación por tarifas — solo beta 1.4

Módulo separado, opcional y **desactivado inicialmente**, sin crear ayudantes ni
automatizaciones. Permite varios tramos por día, horarios distintos según el día,
periodos Punta/Llano/Valle y pasos por medianoche. No presupone horarios comerciales
ni calcula festivos o precios.

En **Configurar**, añade o edita tramos, elige tarifas permitidas y habilita el módulo.
**Guardar y aplicar** muestra un resumen de activación, horarios y huecos; confirma
antes de aplicar. Los solapamientos se rechazan y los huecos no permiten cargar.

| Modo | Comportamiento |
| --- | --- |
| Automático | Permite cargar solo en los periodos seleccionados. |
| Cargar ahora | Ignora las tarifas hasta observar conexión y después desenchufado. |
| Pausado | Mantiene la parada hasta elegir otro modo. |

La primera activación comienza en Pausado. El módulo solo actúa sobre `Paused`:
no desbloquea ni cambia intensidad o carga dinámica. Al habilitarlo, el interruptor
habitual de pausa selecciona Pausado al activarse y Cargar ahora al desactivarse.
El estado explica la espera, incluye la próxima franja como atributo y genera
un aviso en **Reparaciones** si una orden sigue sin confirmarse durante un minuto.

**HA debe estar encendido y comunicado.** Una caída puede impedir detenerse a la
hora prevista; un ciclo de desenchufado completo durante la caída puede pasar
inadvertido. La próxima franja es una previsión, no una garantía de arranque.
No combines esta política con OCPP/Octopus u otros horarios de carga, y mantén
activas la regulación dinámica y las protecciones.

[Guía completa de configuración, pruebas y recuperación de la beta](https://github.com/Carbanog/V2C_trydan/blob/v1.4.0b3/docs/scheduling.es.md).
Su promoción a estable sigue pendiente de pruebas físicas de carga.

## Blueprints y automatizaciones

Son opcionales y se importan por separado desde [blueprints/automation](blueprints/automation).
No se instalan ni activan automáticamente.

**Resumen y avisos de sesión**

[![Importar en Home Assistant](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FCarbanog%2FV2C_trydan%2Fblob%2Fv1.4.0b3%2Fblueprints%2Fautomation%2Fsession_summary.yaml)

[Ver YAML](blueprints/automation/session_summary.yaml). Avisa al comenzar y después
de desconectar, sin duplicar avisos por cada pausa. Sus acciones pueden usar
`session_kwh`, `session_seconds`, `session_hours`, `session_duration`,
`estimated_percent`, `estimated_cost` y `estimated_range_km`.

Ejemplo para la acción de fin; sustituye el servicio de notificación:
```yaml
action: notify.mobile_app_tu_movil
data:
  title: Carga finalizada
  message: "{{ session_kwh }} kWh · {{ session_duration }}"
```

**Alerta de potencia elevada**

[![Importar en Home Assistant](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FCarbanog%2FV2C_trydan%2Fblob%2Fv1.4.0b3%2Fblueprints%2Fautomation%2Fhigh_power_alert.yaml)

[Ver YAML](blueprints/automation/high_power_alert.yaml). Ejecuta acciones tras superar
un umbral durante el tiempo elegido; permite usar `measured_power`.

Capacidad, eficiencia, precio y consumo del vehículo son entradas opcionales del
blueprint. Sus porcentajes, coste y autonomía son estimaciones para los avisos,
no el SOC comunicado por el coche ni sensores nuevos.

## Paneles

- [Nativo](dashboards/native.es.yaml): tarjetas estándar de HA.
- [Mushroom](dashboards/mushroom.es.yaml): requiere Mushroom y Mini Graph Card.

Copia el YAML en una tarjeta manual y adapta los identificadores a tu instalación.
El proyecto no modifica tus paneles automáticamente.

| Panel nativo | Panel Mushroom |
| :---: | :---: |
| [![Panel nativo](docs/images/dashboard-native.png)](docs/images/dashboard-native.png) | [![Panel Mushroom](docs/images/dashboard-mushroom.png)](docs/images/dashboard-mushroom.png) |

## Acciones compatibles

Para automatizaciones nuevas, utiliza preferentemente entidades `switch`,
`number` y `select`. También se conservan estas acciones:
`v2c_trydan.set_intensity`, `v2c_trydan.set_min_intensity`,
`v2c_trydan.set_max_intensity` y `v2c_trydan.set_dynamic_power_mode`.
Permiten indicar `config_entry_id` cuando hay varios cargadores.

No sustituyen todos los ajustes de la app V2C. No modifiques límites, carga
dinámica o modos avanzados si forman parte de la protección de tu instalación.

## Diagnóstico y límites

Una lectura compartida cada **15 s**, timeout de **20 s** y hasta **3 intentos**
para fallos transitorios, separados por **2 s**. Las peticiones se serializan por
cargador. Los errores HTTP permanentes, redirecciones y respuestas inválidas no
se ocultan. Las órdenes requieren `OK` y no se repiten a ciegas.

Ante un problema, habilita el registro de depuración desde la integración,
espera al fallo y recuperación, desactívalo y descarga el registro y los diagnósticos.
Estos incluyen duración, intentos, último fallo y recuperación observada.
Una recuperación automática no demuestra por sí sola que el origen sea la red.
La IP, SSID e ID se ocultan en los campos conocidos del diagnóstico, pero revisa
cualquier registro o captura antes de publicarlo.

No incluye SOC real, objetivo de carga en kilómetros, PVPC ni optimización
automática de precios. La programación beta tampoco ofrece garantías de seguridad
o de cumplimiento de tarifa durante caídas de HA o de comunicación.

## Contribuir y preparar HACS

Publica problemas en [Issues](https://github.com/Carbanog/V2C_trydan/issues) con
versión de integración, HA, firmware, pasos y datos revisados para evitar información privada.
Los idiomas mantenidos son español, inglés y francés; se agradecen correcciones
nativas. Añadiremos otros cuando exista demanda y mantenimiento.

[Arquitectura y desarrollo](docs/architecture.md) ·
[Lista de preparación del catálogo HACS](docs/hacs-readiness.md) — en inglés.

Las comprobaciones incluyen Ruff, pytest, hassfest y HACS. La rama beta añade
pruebas con HA real y cargador simulado; no sustituyen pruebas físicas.
La incorporación al catálogo HACS requiere una solicitud y revisión separadas.

## Licencia y créditos

Proyecto independiente mantenido por [Carbanog](https://github.com/Carbanog),
no afiliado a V2C ni a Home Assistant. El punto de partida fue el trabajo de
[Rain1971](https://github.com/Rain1971/V2C_trydant); el desarrollo actual conserva
ese reconocimiento y ha evolucionado con sus propias funciones y estructura.

[Licencia MIT](LICENSE), con los avisos de los autores originales y de Carbanog
conservados. Agradecimientos a la comunidad y a las herramientas de IA utilizadas
durante el desarrollo y la revisión. La procedencia del icono está documentada
en [brand-assets](docs/brand-assets.md).
Apoyo opcional en **Sponsor this project**, en el lateral del repositorio.
