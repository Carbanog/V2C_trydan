# Programación de carga — beta 1.4.0b1

Esta función es opcional y experimental. La estable sigue siendo **1.3.3**.
La beta no actualiza el firmware del cargador ni cambia la carga dinámica.

## Instalación aislada

1. Haz una copia de seguridad del HA de pruebas.
2. Solo en ese HA, abre la integración en HACS y el menú de volver a descargar.
   Muestra las versiones beta/prerelease si hace falta y elige **1.4.0b1**.
3. Reinicia HA. Comprueba la versión y que tus entidades/sesiones siguen presentes.
4. En producción conserva 1.3.3 y no habilites actualizaciones beta. La beta se
   publica como prerelease, sin sustituir la última release estable.

No pruebes órdenes desde dos instancias de HA que gobiernen el mismo cargador.
Desactiva los horarios/OCPP/automatizaciones que puedan enviar órdenes de carga
concurrentes. No basta con cerrar sus aplicaciones. No desactives la regulación
dinámica ni las protecciones del cargador.

## Configuración sin ayudantes

Abre **Ajustes → Dispositivos y servicios → V2C Trydan → Configurar**.
Todo lo editado es un borrador hasta **Guardar y aplicar**; cancelar no lo aplica.

1. **Añadir tramo horario**: selecciona días, hora de inicio, fin y tarifa
   (Punta, Llano o Valle). Repite para los demás tramos/días.
2. **Ajustes y tarifas permitidas**: habilita la función y elige en qué tarifas
   permites cargar. Puedes dejar la selección vacía para no autorizar ninguna.
3. **Guardar y aplicar**: HA recarga la integración. Para corregir un tramo,
   elimínalo y vuelve a añadirlo antes de guardar.

No se presupone ninguna tarifa comercial. Horas y días son los que tú indiques;
los festivos no se calculan automáticamente. Máximo 100 bloques, sin solapamientos,
incluso entre días. Se permiten varios tramos por día y extremos contiguos.

* Las horas siguen la zona horaria de HA, con precisión de minutos.
* Inicio incluido y fin excluido: 08:00 termina justo a las 08:00.
* Un fin anterior al inicio cruza medianoche; los días elegidos son los de inicio.
* De **00:00 a 00:00** significa el día completo. Otras horas iguales no son válidas.
* Fuera de los tramos configurados, la tarifa es **Sin asignar** y se pausa.
* En cambios de hora, se aplica el horario local: una hora repetida tiene la
  misma tarifa; una hora que no existe no se ejecuta artificialmente.

Por ejemplo, para una prueba define un tramo Valle que empiece dentro de unos
minutos y termine pocos minutos después, sin copiar supuestos horarios oficiales.

## Tres entidades nuevas solo al habilitar

* Selector **Modo de programación de carga**: Automático / Cargar ahora / Pausado.
* Sensor **Tarifa actual**: Punta / Llano / Valle / Sin asignar.
* Sensor **Estado de programación**: explica el permiso o motivo de espera.

La primera activación empieza en **Pausado**. Selecciona Automático para empezar
a obedecer horarios. Los siguientes arranques restauran el modo guardado.

**Cargar ahora** permite ignorar tarifas hasta detectar una desconexión física
de la manguera; entonces vuelve a Automático. Puede prepararse antes de enchufar:
no caduca hasta que se haya visto conectar y después desconectar. Una pausa,
un fallo o una pérdida de red no cuentan como desenchufar. Puedes cancelarlo
eligiendo Automático o Pausado. No anula el candado ni el temporizador V2C.

Con programación habilitada, el interruptor de pausa existente también respeta
el módulo: activar pausa selecciona Pausado; quitarla selecciona Cargar ahora.
Si el cargador pasa inesperadamente a pausa, se conserva como parada manual y
hay que seleccionar un modo para reanudar. No atribuye automáticamente el motivo
a una persona concreta: también podría ser otro controlador o el propio firmware.

## Límites y fallos

La función solo escribe `Paused`, no `Dynamic`, intensidades, `Locked` o `Timer`.
Si detecta el candado, un temporizador V2C activo, un fallo o datos incompletos,
no reanuda. Configuración y modo sobreviven a los reinicios de HA.

Una orden sin confirmar no se repite a ciegas. Una lectura posterior puede
confirmarla; si el estado sigue sin coincidir, revisa el cargador y selecciona
explícitamente el modo para reintentar. Los fallos de almacenamiento también
impiden enviar una orden sin guardar primero la intención.

HA debe estar encendido y comunicado. Si se apaga o falla la red, el cargador
mantiene su estado; **no se garantiza detenerse a la hora límite**. Al recuperarse
se recalcula. Al enchufar puede haber un retraso de detección por el sondeo y
una breve carga antes de que HA consiga pausarla. Si desenchufas y reenchufas
íntegramente durante una caída, HA no puede detectar ese ciclo con certeza.
Esto no es un mecanismo de seguridad ni una garantía contractual de tarifa.

## Pruebas antes de usarlo habitualmente

1. Deshabilitado: mismo comportamiento que 1.3.3, sin entidades de programación.
2. Habilita un horario corto: primero Pausado, después Automático; verifica pausa
   y reanudación reales y el contador acumulado al cruzar el límite.
3. Fuera de horario: Cargar ahora carga; una pausa normal no cancela la excepción.
   Al desenchufar, vuelve a Automático; fuera de horario no debe reanudar al conectar.
4. Pulsa pausa manual y cambia de franja: debe seguir pausado.
5. Reinicia HA dentro/fuera de un tramo y durante Cargar ahora; revisa el modo
   restaurado, la sesión acumulada y que no haya órdenes repetidas.
6. Comprueba un tramo nocturno, fin de semana y rechazo de solapamientos.
7. Simula una pérdida de comunicación solo de forma segura: no cambies protecciones
   ni cortes red durante una operación crítica. Verifica disponibilidad y recuperación.

No se ha validado físicamente en tu instalación: esa es la finalidad de esta beta.

## Deshabilitar o volver a estable

Desmarca Habilitar programación y Guarda. No se envía una reanudación automática:
el cargador puede seguir pausado y debes revisarlo antes de reanudar manualmente.
Para volver a estable, descarga **1.3.3** desde HACS y reinicia HA. Conserva la copia
de seguridad. La sesión usa el mismo almacenamiento de antes; el estado del
programador está separado. Las entidades exclusivas de la beta pueden quedar
no disponibles en el registro al volver atrás; no se borran registros de usuario.
