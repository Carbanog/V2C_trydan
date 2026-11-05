# Revisión de la auditoría de 1.4.0b3

Contraste con el código publicado y correcciones del 5 de noviembre de 2026.
No es una auditoría de penetración ni una prueba del cargador físico.

| Observación recibida | Resultado del contraste | Respuesta |
| --- | --- | --- |
| Manguera desconectada durante estados de fallo | Confirmada: el binario usaba una interpretación distinta de la sesión. | Reutiliza el estado físico fiable persistido por el acumulador; los fallos no generan un desenchufado/reconexión ficticios. Sin observación fiable, permanece desconocido. |
| Doble recarga al reconfigurar IP | Confirmada por el código y la documentación oficial de HA. | `async_update_and_abort`; una sola recarga desde el listener. Prueba de cambio de IP con entrada cargada. |
| Espera máxima de 24 horas en el blueprint | Confirmada. | Retirada: la espera termina al cargar o desenchufar. No se repite el inicio por pausas. Un reinicio de HA o recarga de automatizaciones sigue cancelando las esperas, como en otras automatizaciones de HA; no se añade una cola persistente. |
| Servicios de intensidad sin validación cruzada | Confirmada. | Servicios y entidades validan el valor contra los límites observados del cargador; se rechazan límites desconocidos o contradictorios antes de escribir. No es una transacción con el firmware ni sustituye las protecciones eléctricas. |
| Temporizador V2C bloquea la programación HA | Confirmada, pero es una decisión conservadora, no un fallo que deba eliminarse. | Conservada y documentada: con `Timer` activo no se envían pausas ni reanudaciones, incluso fuera de tarifa. No se cambian horarios de la app automáticamente. |
| Campos L1 detectados solo al iniciar | Confirmada; descubrimiento opcional, no pérdida de telemetría principal. | Documentado que una recarga detecta capacidades nuevas. No se añade descubrimiento dinámico innecesario. |
| Diagnósticos exportan campos futuros desconocidos | Confirmada como riesgo preventivo, no filtración demostrada. | Lista explícita de telemetría revisada; campos desconocidos omitidos e identificadores conocidos ocultos. |
| Acciones CI siguiendo ramas móviles | Confirmada. | Fijadas a SHA consultados en sus repositorios; también checkout/setup-python. |
| Pruebas anteriores no demuestran compatibilidad con HA 2026.11 | Correcto. | La herramienta de fixtures aún fija 2026.10.4 y falla al arrancar contra 2026.11 por cambios en HTTPX y funciones internas de logger. Se conserva la base y se añade solo una prueba de importación con HA 2026.11 real, no equivalente a validar configuración/funcionamiento completo. No se parchean internals para aparentar compatibilidad. |

## Pruebas y criterios para publicar

Las regresiones cubren cambios 2 → fallo → 2 y 2 → fallo → 0, reinicio durante
fallo, reconfiguración IP, límites inválidos sin escritura, campos de diagnóstico
no revisados e inicio de carga tras 49 horas. El cargador de pruebas es simulado.

La batería rápida local tiene 219 pruebas. El resultado de HA, hassfest y HACS
debe consultarse para el commit concreto; no queda implícito por pasar las pruebas
rápidas. La versión instalable b3 no incorpora estas correcciones sin una nueva
publicación; tampoco se modifica una etiqueta existente.

Antes de promover 1.4 a estable siguen pendientes las comprobaciones físicas de
[la guía de programación](scheduling.es.md): límites horarios, pausa externa,
Cargar ahora/desenchufado, reinicio y recuperación de comunicación. No hay cambios
de navegación, migración de sesiones ni una nueva versión estable en esta revisión.

La API sigue siendo HTTP local sin cifrado: no exponerla a Internet. Conservar
copias de seguridad y la estable anterior para recuperación. Un fallo de HA o
red puede impedir pausar a tiempo; la integración no garantiza una tarifa.

Fuente de la deprecación: [Home Assistant Contributors](https://contributors.home-assistant.io/blog/2026/05/07/config-entry-listener-together-with-reloading-methods/).
