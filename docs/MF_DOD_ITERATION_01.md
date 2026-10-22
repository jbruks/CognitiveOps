# CognitiveOps — Iteración 1: Mission First, Doctrine on Demand

**Estado:** análisis y diseño conceptual (no implementación)  
**Rama:** `analysis/doctrine-use-cases-20261022`  
**Principio:** **Mission First, Doctrine on Demand (MF-DoD)**

## 1. Visión

CognitiveOps aspira a ser un sistema de autonomía robótica de propósito general: recibe una misión no prevista durante su desarrollo y utiliza conocimiento externo para interpretarla y ejecutarla, **sin reprogramar el rover ni redactar prompts específicos para cada rol**.

> La misión determina **qué** se necesita conseguir. La doctrina y los procedimientos aportan conocimiento para razonar sobre **cómo** cumplirla, dentro de las capacidades y autorizaciones reales del rover.

**Autonomía de ejecución, no autonomía de mando.** La asignación de misiones, las prioridades de la unidad y la coordinación de varios rovers corresponden a un mando externo.

## 2. Recursos disponibles

- Arquitectura existente **L1–L4**, LLM/VLM, GPS, cámara, control de motores y registros de campo.
- Biblioteca inicial de **13 manuales PDF** en `docs/references/`: navegación, reconocimiento, logística, protección y C-UAS.
- Conocimiento ampliable: manuales, procedimientos locales y experiencia humana validada.

Los manuales son **fuentes de conocimiento**, no órdenes ejecutables ni autorización para acciones.

## 3. Casos de uso (nivel misión)

| ID | Misión | Resultado comprobable |
|---|---|---|
| CU-01 | Reconocer una ruta o recinto autorizado | Informe georreferenciado de transitabilidad, condiciones, obstáculos e incertidumbre |
| CU-02 | Transportar material de A a B | Entrega confirmada o causa de interrupción |
| CU-03 | Desplazar y estacionar una plataforma de observación no armada | Posicionamiento seguro y confirmación de estado |
| CU-04 | Observar un área autorizada | Registro de observaciones e informe al operador |

**Buscar ruta GPS, evitar obstáculos o tomar imágenes son capacidades internas**, no casos de uso de misión.

## 4. Flujo cognitivo propuesto

```text
Orden de misión
      ↓
L4: entender objetivo, límites y criterios de éxito
      ↕
Knowledge on Demand:
  identificar necesidad → recuperar pasajes pertinentes
  → comprobar fuente, vigencia y límites
      ↓
Context / Prompt Generator:
  misión + conocimiento + estado + capacidades + autorizaciones
      ↓
L4 (misión) → L3 (navegación) → L2 (decisión local) → L1 (control)
      ↓
Evidencias, informe, supervisión y escalado al operador
```

La recuperación de conocimiento puede repetirse cuando aparece una situación imprevista o una laguna de conocimiento. **No existe un rol rígido previo**: la función surge de la misión y de las capacidades disponibles.

## 5. Encaje provisional en L1–L4

| Nivel | Responsabilidad | Influencia del conocimiento |
|---|---|---|
| **L4 — Mission** | Interpretar la misión, descomponerla, evaluar progreso y conclusión | Alta |
| **L3 — Navigation/Guidance** | Elegir recorrido, puntos de paso y recuperación global | Media, según el objetivo |
| **L2 — Tactical** | Interpretar entorno inmediato y decidir maniobras locales seguras | Contextual |
| **L1 — Control** | Ejecutar primitivas físicas y límites de seguridad | Sin reconfiguración doctrinal directa |

El **Knowledge Framework** es un servicio transversal, no un quinto nivel de mando.

## 6. POC inicial: reconocimiento del aeródromo RC

**Orden de prueba:** «Inspecciona las zonas autorizadas del aeródromo RC y elabora un informe del estado del terreno, accesos y obstáculos».

**Entradas mínimas:** orden, perímetro autorizado, estado/capacidades del rover y criterios generales de seguridad. No proporcionar una secuencia de waypoints prediseñada como comportamiento específico del caso.

**Comportamiento esperado:** identificar el conocimiento documental relevante; proponer un plan de observación y recorrido; pedir aprobación humana antes del movimiento autónomo; inspeccionar de forma segura; registrar fotos y GPS; entregar un informe con evidencias e incertidumbres.

**Condiciones:** permiso del recinto, coordinación con responsables, exclusión de pista activa y personas, supervisión humana y parada segura. No realizar funciones de identificación de objetivos militares ni de empleo de armas.

**Demostración clave:** comparar la interpretación y el plan con y sin recuperación doctrinal, sin modificar el código ni escribir prompts de misión.

## 7. KISS: primera versión mínima

- Recuperación simple de fragmentos de **dos manuales** (reconocimiento y navegación).
- Una composición dinámica de contexto para **L4** inicialmente; ampliar a L3/L2 solo si aporta valor medible.
- Mantener los contratos existentes de L1–L4 y los límites deterministas.
- Sin aprendizaje automático persistente, entrenamiento de modelos ni cambios de hardware en esta iteración.
- Ante conocimiento insuficiente, ambigüedad o conflicto: **consultar al operador, no improvisar**.

## 8. Riesgos y preguntas abiertas

- **Calidad doctrinal:** fragmentos fuera de contexto, versiones obsoletas o recomendaciones inaplicables.
- **Alucinaciones:** exigir trazabilidad de fuente y distinguir hechos, inferencias y desconocidos.
- **Prompt injection:** los documentos se tratan como datos, no como instrucciones de mayor prioridad.
- **Seguridad/autoridad:** límites físicos y permisos prevalecen sobre cualquier sugerencia documental.
- **Latencia:** medir coste del acceso al conocimiento en el ciclo de decisión.

**Siguiente iteración:** definir el contrato mínimo `misión → necesidad de conocimiento → contexto → respuesta L4`, y un pequeño protocolo de evaluación en laboratorio antes de cualquier prueba de campo.

---
**Estado de este documento:** hipótesis de diseño para revisión; no equivale a validación doctrinal ni aprobación operativa.
