# APS failure intelligence: triaje de taller sensible al costo para camiones Scania

*[English](README.md) · Español*

**[Demo en vivo](https://huggingface.co/spaces/JesusRLGonzalez/aps-failure-intelligence)** | **[Página del proyecto](https://jesusgonzalezmexdata-ux.github.io/aps-failure-intelligence/)**

**Pregunta.** ¿Qué camiones deben ir al taller a revisar el sistema de presión de aire (APS), si una falla no detectada cuesta 500 y una revisión innecesaria cuesta 10? Son los costos oficiales que Scania publicó con los datos.

**Respuesta, en el conjunto de prueba oficial de Scania (16,000 camiones, evaluado una sola vez):**

| | Resultado |
|---|---|
| **Costo oficial** | **11,540** (intervalo 95 %: 7,940 – 15,661) frente a **187,500** sin triaje: **−94 %** |
| Fallas detectadas | 359 de 375 (**95.7 %**) |
| Carga de taller | **44.6 revisiones por cada 1,000 camiones**; una de cada dos encuentra una falla real |
| Referencia publicada | Tres primeros del reto IDA 2016: 9,920 / 10,900 / 11,480. Mismo rango; el intervalo no permite separarlos |
| Robustez | Ahorra 88–96 % frente a no hacer triaje con cualquier razón de costos entre 10 : 1 y 100 : 1 |

![Costo frente al umbral](reports/figures/cost_vs_threshold.png)

## Úsalo con las alertas de tu flota (MVP)

Las 170 lecturas de Scania son internas del fabricante; el producto es el **método**: decidir por costo qué alertas merecen revisión en taller y vigilar la carga cada semana. En la [demo](https://huggingface.co/spaces/JesusRLGonzalez/aps-failure-intelligence), modo **«Tus alertas»**:

1. Descarga la plantilla o sube la exportación de tu telemática (`.xlsx` o `.csv`): unidad, fecha, tipo de alerta, puntaje opcional, si se revisó y si se confirmó la falla (en taller o como avería en ruta en 30 días).
2. Captura el costo de una revisión, el costo extra de una falla en ruta y, si quieres, la capacidad semanal del taller.
3. Obtén la regla de menor costo, la banda de revisiones por semana, una retrospectiva temporal contra lo que se hizo (intervalo del 90 % por semanas) y un reporte de una página.
4. Cada lunes sube la semana nueva: sale la lista de unidades a taller y una alerta si la carga o la mezcla de alertas se mueve.

En la flota simulada de ejemplo (140 tractocamiones, 26 semanas), la regla elegida con las primeras 17 semanas habría costado **476 mil pesos menos** que la práctica actual en las últimas 9 (intervalo del 90 %: 206 a 724 mil), con 9 fallas en ruta en lugar de 23. El archivo se procesa en el navegador y no sale de él. Protocolo de piloto y criterios de abandono: [`docs/MVP_PILOTO.md`](docs/MVP_PILOTO.md).

## Por qué el resultado es confiable

- **Una sola mirada al test.** Está sellado en código (`load_holdout` falla salvo en la evaluación final) y un archivo de reserva impide una segunda evaluación. Las reglas de esa evaluación y el plan de análisis se publicaron **antes** de ejecutarla.
- **Umbral sin fuga.** En validación cruzada cada pliegue se califica con un umbral elegido solo en los demás pliegues. El umbral final sale de las puntuaciones fuera de pliegue del entrenamiento.
- **Decisiones pre-registradas.** Candidatos (fase 4) y un presupuesto fijo de 12 configuraciones (fase 5) se publicaron antes de tener resultados. El tuning ganó 0.5 %, dentro del ruido de semilla, y así se reporta.
- **Datos verificados byte a byte.** Los archivos oficiales se guardan comprimidos y su SHA256 coincide con el publicado; las pruebas rechazan cualquier byte editado.
- **Afirmaciones acotadas.** Clasifica lecturas actuales bajo una matriz de costos. No pronostica cuándo ocurrirá una falla, no afirma causas y los costos son unidades abstractas del reto, no dinero.

## Método por fases

| Fase | Resultado |
|---|---|
| 1 · Ingesta y auditoría | 60,000 camiones, 1.7 % de fallas; los faltantes son informativos |
| 2 · Contrato del problema | El costo oficial es la única métrica de selección |
| 3 · Baseline y protocolo | Regresión logística 52,100 frente a 500,000 trivial (CV de entrenamiento) |
| 4 · Candidatos | LightGBM + indicadores de faltantes, 34,600 |
| 5 · Tuning controlado | 34,440; dispersión por semilla 33,220 – 38,480 |
| 6 · Evaluación final única | 11,540 en el test oficial |
| 7 · Errores, incertidumbre, economía | Bootstrap, sensibilidad a la razón de costos, calibración, drivers |
| 8 · Model Card y release | [MODEL_CARD.md](MODEL_CARD.md) |
| 9 · Prueba de estrés y monitoreo | 8 defectos inyectados: 5 alertas, 1 aviso, 2 invisibles por diseño |
| 10 · Recalibración | Isotónica sobre OOF de entrenamiento; Brier 0.00497 → 0.00473, mismo orden |
| Siguiente · Datos reales | Datos públicos sucios y un socio real |

Los documentos de cada fase están en [`docs/`](docs) (en inglés).

## Stack y para qué sirve cada pieza

| Capa | Herramienta | Función |
|---|---|---|
| Contrato de datos | **SQL en DuckDB** | 11 controles de esquema, etiquetas, rangos y faltantes; el test se expone sin etiquetas |
| Modelado | **Python**: pandas, scikit-learn, **LightGBM** | Rasgos sin fuga, CV de costo anidada, gradient boosting |
| Decisión | Umbral óptimo por costo (búsqueda exacta) | Convierte la puntuación en revisar / no revisar |
| Explicaciones | Contribuciones de LightGBM | Lecturas que más empujan la puntuación de cada camión |
| Servicio | **FastAPI** + **Docker** | `/score` con puntuación, decisión, riesgo calibrado y drivers; `/health` con hash del modelo |
| Monitoreo | PSI, banda binomial de carga de taller, esquema | `/monitor` avisa de deriva, datos faltantes y carga de taller inesperada |
| Soporte a la decisión | **Streamlit** + Altair | Pon tus costos y tamaño de flota; el umbral se recalcula con datos de entrenamiento |
| Control de calidad | **pytest** + **GitHub Actions** | Integridad de datos, test sellado, costo óptimo, servicio, dashboard y Docker |

## Reproducir

Los comandos están en la sección *Reproduce* del [README en inglés](README.md#reproduce).

## Licencia y cita

Código: [Apache-2.0](LICENSE). Datos: Scania CV AB vía UCI Machine Learning Repository, [doi:10.24432/C51S51](https://doi.org/10.24432/C51S51). Ver [NOTICE](NOTICE) y [CITATION.cff](CITATION.cff).

---

**Jesús R. L. González** · Científico de Datos · Operaciones y calidad en manufactura
