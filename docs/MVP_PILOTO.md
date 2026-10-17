# MVP «Calibrador de alertas por costo»: protocolo de piloto

**Para quién:** gerente de mantenimiento de una flota con telemática (tractocamiones, autobuses, reparto) que recibe más alertas o códigos de falla de los que el taller puede revisar.
**Qué decide:** qué alertas mandar a taller, cuántas revisiones esperar por semana y cuándo sospechar que algo cambió en la telemática o en la flota.
**Dónde se usa:** demo de este repositorio → modo «Tus alertas». El archivo se procesa en el navegador; no se envía a ningún servidor.

## 1. Datos

| Columna | Obligatoria | Contenido |
|---|---|---|
| unidad | Sí | Número económico o placa |
| fecha | Sí | Día de la alerta (dd/mm/aaaa o aaaa-mm-dd) |
| tipo_alerta | Sí | Código DTC o nombre de la alerta, escrito siempre igual |
| puntaje | No | Puntaje de riesgo de la telemática (más alto = más riesgo). Sin él se prioriza por tipo |
| revisada | Sí | sí / no: ¿se mandó a taller por esta alerta? |
| falla | Sí | sí / no: falla confirmada en la revisión, o avería en ruta del mismo sistema en los 30 días siguientes |

Acepta Excel o CSV (coma o punto y coma), encabezados con sinónimos (económico, código, DTC, revisado, avería) y fechas como número de serie de Excel. Las filas con error se excluyen y se listan con su número de fila.

**El dato que hace funcionar el método es «falla» también para las alertas no revisadas.** Si el taller solo registra lo que encontró, no se puede saber cuánto cuesta ignorar una alerta: es el criterio de abandono número uno.

## 2. Cómo decide

1. **Costo de cada decisión:** revisar cuesta lo mismo encuentre o no la falla; no revisar cuesta el extra de una falla en ruta (grúa, carga, días parada) si la había.
2. **Prioridad:** el puntaje de la telemática; sin puntaje, la probabilidad de falla del tipo de alerta con contracción bayesiana empírica (un tipo con pocas alertas se acerca a la tasa global).
3. **Regla:** con puntaje, el corte que minimiza el costo total (búsqueda exacta del caso Scania); con tipo, se atiende todo tipo con P(falla) ≥ costo de revisión / (costo de revisión + costo de falla).
4. **Capacidad:** si el taller no alcanza, el corte sube hasta caber y se reporta lo que cuesta en fallas en ruta.
5. **Retrospectiva:** la regla se elige con las primeras dos terceras partes de las semanas y se mide en el último tercio contra lo que se hizo, con intervalo del 90 % por remuestreo de semanas.
6. **Monitor semanal:** carga de taller contra la banda binomial del 99 % para el número de alertas de esa semana, y mezcla de alertas y del puntaje contra la referencia (ji cuadrada para decidir, PSI para el tamaño del cambio). En 200 semanas tranquilas simuladas dio 2 % de falsas alarmas; detectó 44 de 50 semanas con un disparo de alertas por firmware.

## 3. Fases

| Fase | Duración | Actividad | Entregable |
|---|---|---|---|
| 0 · Acuerdo | 1 semana | Exportación de 6 meses de alertas y registro de taller y de grúas; costos por revisión y por falla en ruta | Historial en la plantilla |
| 1 · Retrospectiva | 1 semana | Regla, banda de carga y comparación con la práctica actual | Reporte de una página con intervalo |
| 2 · Sombra | 4 semanas | Cada lunes se sube la semana: lista y monitor, sin cambiar lo que hace el taller | Diferencia real entre la lista y lo revisado |
| 3 · Acción controlada | 8 semanas | La mitad de las unidades (por número económico par/impar) sigue la regla; la otra, la práctica actual | Fallas en ruta y revisiones sin falla por grupo |
| 4 · Cierre | 1 semana | Decisión de extender y ajuste de costos | Caso de estudio con autorización |

Durante la fase 2 conviene revisar al azar 1 de cada 20 alertas que la regla no manda a taller: así se mide la falla en lo que se deja pasar sin depender solo de las averías en ruta.

## 4. Criterios definidos antes de empezar

**Éxito:** menos revisiones sin falla sin más fallas en ruta, con intervalo del ahorro por encima de cero.

**Abandono:**
- el taller o el área de grúas no registran si hubo falla en las alertas no revisadas;
- en la retrospectiva el intervalo del ahorro incluye cero o es negativo;
- en la fase 3 el grupo con regla tiene más fallas en ruta que el de control.

## 5. Límites

- Una falla encontrada en revisión se cuenta como avería evitada. Si muchas se habrían resuelto solas, el beneficio real es menor.
- Las averías sin alerta previa no cambian con esta regla: solo decide entre alertas.
- El monitor levanta preguntas; nunca cambia la regla solo. Se recalibra con más historial cuando se entiende el cambio.
