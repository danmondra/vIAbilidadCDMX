# REPORTE COMPLETO: ViableCDMX

**Asistente Inteligente de Viabilidad y Trámites para Negocios en CDMX**

**Fecha:** Junio 2026  
**Versión:** 1.0  
**Objetivo:** Resolver las principales barreras de los emprendedores e inversionistas en la Ciudad de México.

---

## 🎯 Problema Identificado

Los emprendedores enfrentan dos barreras principales:
1. **Desconocimiento de viabilidad** en la zona elegida (afluencia, competencia, uso de suelo, riesgo regulatorio).
2. **Falta de claridad en trámites**: qué documentos necesitan, en qué orden, a qué ventanillas ir y tiempos reales.

Esto genera retrasos, gastos innecesarios, clausuras y sanciones.

---

## 💡 Solución Propuesta: ViableCDMX

Plataforma inteligente (Bot de Telegram @vIAbilibot) que permite:
- Evaluar viabilidad del negocio por giro y ubicación.
- Obtener guía paso a paso de trámites oficiales.
- Conocer programas de apoyo (FONDESO, SEDECO, etc.).
- Recibir checklist personalizado y enlaces directos.

---

## 📚 Fuentes Oficiales Integradas

- **RETYS**: https://www.registrodetramitesyservicios.cdmx.gob.mx/
- **SIAPEM (Ventanilla Única)**: https://siapem.cdmx.gob.mx/
- **Consulta Uso de Suelo**: http://ciudadmx.cdmx.gob.mx:8080/seduvi/
- **Certificado de Uso de Suelo**: Trámite SEDUVI
- **Ley de Establecimientos Mercantiles CDMX** (2025)
- **Reglamento de la Ley de Establecimientos Mercantiles**

---

## 📊 Clasificación Oficial de Giros (Ley de Establecimientos)

| Tipo de Impacto     | Ejemplos                              | Trámite en SIAPEM              | Tiempo aproximado     | Costo     |
|---------------------|---------------------------------------|--------------------------------|-----------------------|-----------|
| **Bajo Impacto**    | Cafeterías sin alcohol, tiendas, salones de belleza, oficinas | Aviso de Funcionamiento       | Inmediato (10 min)    | Gratuito  |
| **Impacto Vecinal** | Restaurantes, gimnasios, consultorios | Permiso de Funcionamiento      | 5-15 días             | Medio     |
| **Impacto Zonal**   | Bares, discotecas, venta principal de alcohol | Permiso + dictámenes extras   | 15-45 días            | Alto      |

---

## 🔄 Flujo General de Trámites (Orden Recomendado)

1. **Constitución del Negocio**
   - Persona Física: RFC + e.firma (SAT)
   - Persona Moral: Acta constitutiva + RPC

2. **Uso de Suelo**
   - Consulta en SEDUVI → Certificado Único de Zonificación (CUS)

3. **SIAPEM**
   - Aviso o Permiso según impacto

4. **Dictámenes Complementarios**
   - Protección Civil, COFEPRIS, Bomberos (según caso)

5. **Trámites Laborales**
   - IMSS, INFONAVIT, Registro de Marca (IMPI)

---

## 🤖 Flujo del Bot (Diseño Lógico y Optimizado)

### Menú Principal (Después de /start)
- 🔍 Evaluar Viabilidad ← **Más utilizado**
- 📋 Trámites y Permisos
- 💰 Programas de Apoyo
- 📁 Mi Negocio (guardados)

### Flujo Detallado de Viabilidad (Recomendado)

1. Pedir **Giro del negocio** (con botones sugeridos)
2. Pedir **Alcaldía + Colonia**
3. Pedir **Tamaño (m²)** y **¿Vende alcohol?**
4. Generar **Reporte Inteligente**
5. Ofrecer **Checklist completo de trámites**
6. Opción de guardar o exportar PDF

**¿Por qué este flujo es el más lógico?**
- Da valor rápido (reporte en pocos mensajes).
- Usa botones para reducir fricción.
- Recopila datos progresivamente.
- Personaliza según giro y zona.
- Cierra con acción concreta (checklist + enlaces).

---

## 📈 Ejemplo de Reporte de Viabilidad

**Negocio:** Cafetería specialty  
**Ubicación:** Condesa, Cuauhtémoc  
**Tamaño:** 60 m² | Alcohol: No

**Resultado:**
- **Score de Viabilidad:** **88/100** → Muy Recomendado
- **Impacto:** Bajo → Aviso inmediato en SIAPEM
- **Fortalezas:** Alta afluencia, zona mixta compatible, demanda millennial/turística
- **Riesgos:** Competencia media (diferenciarse con specialty)
- **Siguiente paso recomendado:** Iniciar Uso de Suelo + SIAPEM

**Enlaces directos:**
- Uso de Suelo → [SEDUVI](http://ciudadmx.cdmx.gob.mx:8080/seduvi/)
- SIAPEM → [Iniciar trámite](https://siapem.cdmx.gob.mx/)

---

## 🛠️ Stack Tecnológico Recomendado

- **Bot Telegram:** `python-telegram-bot` v22 (ConversationHandler)
- **IA:** Grok / Claude 3.5 / GPT-4o
- **Datos:** JSON + RAG sobre PDFs oficiales
- **Base de datos:** SQLite (inicial)
- **Hosting:** Railway / Render
- **Canal:** Telegram @vIAbilibot
