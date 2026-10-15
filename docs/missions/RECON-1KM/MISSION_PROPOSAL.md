# CognitiveOps — RECON-1KM
## Autonomous Terrain Reconnaissance
*Goal-Directed Traversability Assessment in an Unknown Rural Environment*

| Campo | Valor |
|---|---|
| Documento | Proyecto de demostración experimental |
| Versión | 0.1 — 15 de octubre de 2026 |
| Estado | **Propuesta: RECON-1KM aún no validada en campo** |
| Plazo | Tres semanas |
| Plataforma | Axial SCX10 II 4×4; Raspberry Pi; cámara frontal; GPS |
| Repositorio | https://github.com/jbruks/CognitiveOps |
| Línea base | `fieldtest-2026-10-15-goto-point-success` |

> **Objetivo:** evaluar si CognitiveOps puede desplazarse hacia un destino GPS situado aproximadamente a 1 km, **sin ruta ni waypoints intermedios precargados**, utilizando percepción visual para seleccionar maniobras locales y registrando evidencias de navegación y del terreno observado, en un entorno rural sencillo, autorizado y supervisado.

## 1. Resumen ejecutivo

CognitiveOps es una plataforma experimental de autonomía cognitiva terrestre con niveles diferenciados de gestión de misión, guiado, decisión táctica y control físico. El 15 de octubre de 2026 completó una misión `GO_TO_POINT` según su criterio de llegada GPS [E1]. RECON-1KM busca ampliar esa capacidad a un desplazamiento prolongado con una finalidad adicional: observar y documentar las condiciones del terreno recorrido.

La misión se inspira en el **reconocimiento terrestre de rutas** descrito en publicaciones doctrinales [D1–D3] y en la investigación sobre **evaluación de transitabilidad** de vehículos autónomos [S1–S3]. Se trata de una **adaptación robótica civil, no armada y experimental**, no de una operación militar ni de una clasificación técnica certificada de carreteras.

La prioridad es **reutilizar el software funcional**, medir sus límites e implementar únicamente cambios pequeños justificados por pruebas. **El kilómetro es una meta experimental, no una capacidad demostrada.**

## 2. CognitiveOps: situación actual

### 2.1. Plataforma y arquitectura

El rover utiliza un Axial SCX10 II 4×4, Raspberry Pi, cámara frontal de posición baja y GPS. La percepción observa el terreno visible delante del vehículo; el GPS estima la posición y la separación respecto al destino. Ambos presentan incertidumbre.

| Componente | Función |
|---|---|
| **L4 — Mission Management** | Objetivo y estado de misión |
| **L3 — Guidance & Navigation** | Guiado hacia el destino GPS |
| **L2 — Tactical Planning** | Selección de maniobras locales |
| **L1 — Actuator Control** | Ejecución de acciones físicas |
| **Perception / World Model** | Interpretación visual y contexto disponible |

### 2.2. Línea base demostrada

Prueba `GO_TO_POINT` del **15/10/2026** [E1]:

| Indicador | Resultado |
|---|---:|
| Distancia GPS inicial | 45,24 m |
| Distancia GPS final | 4,86 m |
| Precisión GPS final indicada | ~2,39 m |
| Ciclos | 185 |
| Duración | ~30 min 6 s |
| Movimientos hacia delante | 134 |
| Retrocesos | 26 |
| Finalización | Por tolerancia GPS |

**Interpretación:** la prueba valida la integración funcional y la llegada conforme al criterio GPS. **No demuestra** seguimiento de una ruta exacta, descubrimiento robusto de caminos ni navegación sostenida durante 1 km. El progreso lento, las interrupciones de guiado y los retrocesos sin percepción trasera son limitaciones relevantes.

La versión probada está preservada mediante la etiqueta Git `fieldtest-2026-10-15-goto-point-success` [E2]. Los cambios para RECON-1KM deben ser trazables y no alterar este hito.

## 3. Justificación operativa y doctrinal

El reconocimiento de un itinerario busca obtener información sobre las condiciones que afectan al movimiento: superficie, obstáculos, restricciones y continuidad del paso. **Su producto no es solo la llegada al destino, sino la información verificable obtenida durante el recorrido.**

- **ATP 3-20.98 — *Reconnaissance Platoon*** [D1]: referencia conceptual sobre misiones de reconocimiento terrestre, incluido el reconocimiento de rutas.
- **ATP 3-34.81 / MCRP 3-34.3 — *Engineer Reconnaissance*, con Change 1** [D2]: referencia sobre observación de características físicas, obstáculos y restricciones de movilidad.
- **FM 3-25.26 — *Map Reading and Land Navigation*** [D3]: referencia general sobre posición, orientación y navegación terrestre; CognitiveOps aplica una adaptación computacional basada en GPS.

**Delimitación:** una ruta prescrita para reconocer y el **descubrimiento de una trayectoria entre dos coordenadas** no son equivalentes. RECON-1KM combina la finalidad del reconocimiento de rutas con un desafío tecnológico añadido: **no facilitar al rover la trayectoria**. Los manuales fundamentan la finalidad operativa, pero no especifican nuestro algoritmo ni garantizan su resultado.

La transitabilidad observada se referirá a **este rover y a las condiciones concretas del ensayo**, no a la aptitud general del terreno para otros vehículos. La distancia de 1 km es una decisión experimental, no un requisito doctrinal.

## 4. Fundamento científico y tecnológico

La evaluación de transitabilidad (*terrain traversability assessment*) y la navegación en entornos no estructurados son problemas conocidos de robótica terrestre [S1–S3]. El vehículo debe interpretar información del entorno, elegir movimientos y actualizar sus decisiones.

La cámara frontal de CognitiveOps no permite medir con fiabilidad todas las distancias, pendientes, profundidades o propiedades mecánicas del suelo. El GPS tampoco garantiza una posición exacta. Por ello se distinguirá entre **terreno aparentemente transitable**, **terreno efectivamente atravesado** y **condición desconocida**.

La demostración se centra en navegación **reactiva y orientada a un objetivo**, no en SLAM ni planificación global de rutas.

## 5. Definición de la misión RECON-1KM

### 5.1. Escenario y entradas

Terreno rural **autorizado, controlado y relativamente abierto**, con pendiente suave, obstáculos moderados, buena recepción GPS y ausencia de tráfico. El equipo humano conocerá los límites y riesgos para supervisar la seguridad, pero **el rover no recibirá una ruta ni waypoints intermedios**.

**Entradas:** posición inicial A, coordenadas de destino B (aproximadamente a 1 km) y parámetros operativos de seguridad.

### 5.2. Orden de misión

> Desde A, intenta alcanzar B utilizando el guiado GPS y la percepción visual disponibles. No se proporciona trayectoria precargada. Selecciona maniobras localmente transitables; registra condiciones observadas, obstáculos relevantes y decisiones ejecutadas. Finaliza al cumplir el criterio de llegada o detente si no puedes continuar de forma segura, conservando la evidencia de la ejecución.

### 5.3. Objetivos verificables

| ID | Objetivo |
|---|---|
| OBJ-01 | Orientar el desplazamiento hacia B mediante GPS |
| OBJ-02 | Seleccionar maniobras mediante guiado y percepción frontal |
| OBJ-03 | Mantener progreso autónomo durante distancias crecientes |
| OBJ-04 | Registrar posiciones, observaciones, acciones e incidencias |
| OBJ-05 | Alcanzar el umbral GPS definido **o** terminar de forma segura |
| OBJ-06 | Elaborar un informe trazable a los logs |

**Exclusiones:** llegada garantizada, exploración de redes complejas de caminos, planificación global óptima, SLAM, clasificación técnica certificada de rutas, vigilancia de personas, operaciones armadas y ejecución sin supervisión humana.

## 6. Concepto de ejecución

```text
       DESTINO B (GPS)
              │
       L4: misión/estado
              │
       L3: guiado GPS ────────┐
                             ▼
       Percepción frontal → L2: decisión local
                             │
                       L1: actuadores
                             │
                       Movimiento rover
                             │
                   Nueva observación → repetir

          Registro de estado, percepción y acciones
```

1. **Inicio:** configurar destino, límites de seguridad y logging.
2. **Guiado:** calcular dirección y distancia estimadas a B.
3. **Observación:** interpretar el terreno frontal visible.
4. **Decisión:** seleccionar y ejecutar una maniobra mediante L2 y L1.
5. **Reevaluación:** actualizar posición y percepción y repetir.
6. **Cierre:** registrar llegada, interrupción o resultado parcial.

**Precisión funcional:** no se afirmará que el rover recuerda caminos fallidos o elige entre rutas lejanas: esas capacidades no están demostradas. Se verificará qué observaciones pueden recuperarse de los logs actuales antes de prometer un inventario estructurado del terreno.

## 7. Capacidades existentes y desarrollo necesario

**Regla:** preservar la línea base; inspeccionar el código real antes de modificarlo; justificar cada cambio con evidencia; hacer pruebas sin motores conectados antes de salir al campo.

| Necesidad | Tratamiento |
|---|---|
| `GO_TO_POINT`, GPS, L1–L4 y percepción | **Reutilizar** |
| Logs de posición, percepción y acciones | **Verificar** cobertura y formato actuales |
| Detección de estancamiento | **Mejora candidata** si las pruebas la justifican |
| Retroceso sin visión trasera | **Revisión prioritaria de seguridad** |
| Límites de tiempo, batería, comunicación y parada | **Verificar** e implementar solo lo imprescindible |
| Informe de terreno y trayectoria | Preferir **posprocesado externo** de logs |
| Cognitive Runtime, memoria avanzada, RAG, SLAM | **Aplazados** |

No se presupone una lista cerrada de nuevas funcionalidades: las pruebas determinarán si son necesarias.

## 8. Plan experimental y evaluación

### 8.1. Hipótesis

> En un entorno rural sencillo y supervisado, CognitiveOps puede mantener progreso autónomo hacia un destino GPS durante distancias superiores a la demostrada, utilizando percepción frontal para seleccionar movimientos y conservando evidencia verificable.

### 8.2. Validación progresiva

| Etapa | Distancia objetivo | Propósito |
|---|---:|---|
| P1 | 50 m | Reproducir comportamiento de referencia |
| P2 | 100–150 m | Medir progreso sostenido |
| P3 | 300 m | Identificar límites de continuidad |
| P4 | 500 m | Evaluar tiempo, energía y fiabilidad |
| P5 | 1.000 m | Intentar demostración objetivo |

Solo se ampliará la distancia cuando el ensayo anterior sea seguro y suficientemente estable. La prueba de referencia tardó unos 30 minutos para un destino inicialmente a 45 m: **la viabilidad temporal de 1 km aún no está acreditada**.

### 8.3. Métricas y resultados

Se registrarán, cuando los datos lo permitan: distancia inicial y final al objetivo; precisión y trayectoria GPS; duración; progreso por unidad de tiempo; acciones, paradas y retrocesos; periodos sin guiado o percepción; observaciones visuales; intervenciones humanas; causa de finalización; y versión/configuración de software.

- **Completada:** llegada al umbral GPS con ejecución verificable y sin incidencias de seguridad.
- **Parcial:** progreso autónomo significativo sin llegada.
- **Interrumpida:** parada por seguridad, fallo o intervención.

La llegada por tolerancia GPS **no prueba por sí sola** que se haya reconocido sistemáticamente toda la ruta.

### 8.4. Seguridad

Ensayos con autorización, supervisión humana, parada de emergencia, comunicación fiable y límites operativos. Evitar tráfico, personas, agua, zanjas y desniveles. No explorar fuera del área permitida. Ante percepción o guiado insuficientes, priorizar una parada segura. Revisar especialmente los retrocesos sin percepción trasera.

## 9. Plan de trabajo y entregables

| Periodo | Trabajo | Entrega |
|---|---|---|
| Semana 1 | Analizar log del 15/10, seguridad y pruebas cortas | Línea base y riesgos priorizados |
| Semana 2 | Ensayos crecientes y correcciones mínimas justificadas | Evidencias de autonomía sostenida |
| Semana 3 | Mejor ensayo viable y preparación de reunión | Vídeo, trayectoria, métricas e informe |

**Entregables:** commit/tag utilizado, orden de misión, configuración, logs originales, trayectoria GPS, muestras de percepción, métricas, informe y vídeo. Si no se alcanza 1 km, se informará de la distancia validada y de sus limitaciones.

## 10. Evolución futura

RECON-1KM servirá como línea base para un futuro **Cognitive Runtime**: memoria de trabajo, episódica, espacial y procedimental; gestión dinámica de tareas; registro de capacidades; y consulta de documentación técnica para planificación de misiones. La evolución deberá mantener barreras deterministas de seguridad en los niveles inferiores.

**Esta visión no forma parte del desarrollo comprometido para RECON-1KM.**

## 11. Referencias y trazabilidad

### Publicaciones doctrinales

- **[D1]** Department of the Army. *ATP 3-20.98 — Reconnaissance Platoon* (2013). `docs/references/ATP 3-20.98 Reconnaissance Platoon 2013.pdf`.
- **[D2]** *ATP 3-34.81 / MCRP 3-34.3 — Engineer Reconnaissance*, con Change 1. `docs/references/MCRP 3-34.3 (W CH 1) (SECURED).pdf`. **Pendiente de verificar portada, edición y designaciones exactas.**
- **[D3]** Department of the Army. *FM 3-25.26 — Map Reading and Land Navigation*. `docs/references/fm_3-25.26_map_reading_and_land_navigation.pdf`; edición pendiente de comprobación.

### Literatura científica

- **[S1]** Borges et al. (2022). *A Survey on Terrain Traversability Analysis for Autonomous Ground Vehicles*. *Field Robotics*. https://doi.org/10.55417/fr.2022049
- **[S2]** Beycimen, Ignatyev y Zolotas (2023). *A Comprehensive Survey of Unmanned Ground Vehicle Terrain Traversability for Unstructured Environments and Sensor Technology Insights*. *Engineering Science and Technology, an International Journal*. https://doi.org/10.1016/j.jestch.2023.101457
- **[S3]** *Terrain Traversability Analysis Methods for Unmanned Ground Vehicles: A Survey* (2013). *Engineering Applications of Artificial Intelligence*. https://doi.org/10.1016/j.engappai.2013.01.006

### Evidencia del proyecto

- **[E1]** Prueba `GO_TO_POINT`, 15/10/2026. `goto_test_nav_cam_sol11_500tokens.log`. Informe: `docs/field_tests/2026-10-15_goto_point_success/REPORT.md`.
- **[E2]** Repositorio CognitiveOps: https://github.com/jbruks/CognitiveOps; etiqueta `fieldtest-2026-10-15-goto-point-success`.

> **Control bibliográfico:** las referencias doctrinales se utilizan aquí como fundamento conceptual, no como transcripción exhaustiva. **Antes de distribuir una versión académica o formal, cotejar directamente los PDF para verificar edición, páginas y apartados, y revisar los metadatos de los artículos científicos.**

---

## Conclusión

RECON-1KM propone una demostración de reconocimiento de terreno orientada a un destino, fundamentada en una necesidad operativa real y en problemas de robótica de campo. Su aportación será medir **hasta dónde llega CognitiveOps con la arquitectura ya validada**, sin ruta precargada, conservando evidencias de observación, decisión y movimiento.

La meta de 1 km es ambiciosa respecto a la línea base. El proyecto prioriza **seguridad, medición honesta y cambios mínimos**: demostrar primero, ampliar después.
