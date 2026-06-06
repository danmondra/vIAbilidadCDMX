# Documento Maestro: Asesor Virtual de Viabilidad y Trámites CDMX

## 1. Introducción y Visión del Producto
El objetivo de la herramienta es fungir como un **Asesor Virtual de Viabilidad**. No es únicamente un "llenador de formularios", sino una guía inteligente basada en lenguaje natural. El usuario plantea su idea de negocio y la herramienta se encarga de:
1. Evaluar la competencia y rentabilidad.
2. Validar que la zona permita dicho negocio (Uso de Suelo).
3. Entregar una receta paso a paso de los trámites legales que se deben cumplir en el orden correcto, minimizando redundancias y visitas innecesarias a plataformas del gobierno.

---

## 2. Fase 0: Entrevista y Diagnóstico de Viabilidad (Chatbot)
Esta es la fase de interacción inicial donde se recaban los datos en lenguaje natural y se cruzan con diversas bases de datos públicas.

### 2.1 Perfilamiento del Usuario
El bot debe hacer preguntas clave para entender el negocio:
- **Giro comercial:** ¿Qué tipo de negocio deseas abrir? (ej. tortillería, estética, gimnasio, bar).
- **Ubicación:** ¿Tienes un local en mente? (Alcaldía, colonia o dirección exacta).
- **Dimensiones (Aproximadas):** ¿Cuál es el aforo esperado (más de 100 personas) o el tamaño del local (más de 250 m2)? *Esto es vital para Protección Civil.*

### 2.2 Análisis de Viabilidad y Mercado
Antes de mandarlo a hacer trámites, se le muestra un panorama comercial:
- **Nivel de Competencia:** Uso del DENUE para decirle exactamente cuántos negocios del mismo giro (SCIAN) hay en su cuadra, colonia y alcaldía. 
- **Rentabilidad y Afluencia:** Cruce con datos de SECTUR (ocupación hotelera y afluencia), SEDECO (derrama en eventos) y Censos Económicos para mostrar el tiempo de vida promedio del giro o el poder adquisitivo de la zona.

### 2.3 Validación de Uso de Suelo Inmediata
El bot mapea el giro deseado contra el **Sistema de Información Geográfica de SEDUVI**.
- **Regla de negocio:** Si el usuario quiere abrir un Bar (Impacto Zonal) en una calle que es exclusivamente Habitacional, el bot debe detenerlo y sugerir buscar otra ubicación antes de gastar dinero.
- *Tip técnico:* Consultar el uso de suelo directamente en: [http://ciudadmx.cdmx.gob.mx:8080/seduvi/](http://ciudadmx.cdmx.gob.mx:8080/seduvi/)

### 2.4 Clasificación del Impacto Legal
Con base en el Artículo 35, 19 y 27 Bis de la Ley de Establecimientos Mercantiles (LEM), el bot clasifica el negocio automáticamente en una de tres categorías:
1. **Bajo Impacto:** Tiendas de abarrotes, estéticas, florerías, papelerías, cafeterías, fondas.
2. **Impacto Vecinal:** Salones de fiesta, restaurantes (especialmente con venta de alcohol con alimentos), hoteles, clubes privados, cines.
3. **Impacto Zonal:** Bares, cantinas, antros, discotecas, casinos, cabarets.

---

## 3. Fase 1: Hoja de Ruta de Permisos Base (Para todos)
Una vez validada la viabilidad, inicia la guía de trámites. Estos requisitos se sacan antes de ir al SIAPEM.

1. **Cuenta Llave CDMX**
   - **Acción:** Crear o verificar acceso a la cuenta Llave CDMX. Es obligatorio para todo trámite en la ciudad.
2. **Certificado Único de Zonificación de Uso de Suelo**
   - **Importancia:** Vigencia máxima de un año. Dice expresamente que el giro está permitido.
   - **Link de trámite:** [Solicitar Certificado en SEDUVI](http://certificadodigital.cdmx.gob.mx:8080/CertificadoDigital/certificado/solicitaCertificado) o [Info del trámite](https://www.cdmx.gob.mx/public/InformacionTramite.xhtml?idTramite=806)
3. **Programa Interno de Protección Civil**
   - **Criterio de exención:** Establecimientos con menos de 100 personas de aforo **Y** con superficie menor o igual a 250 metros cuadrados **NO** presentan este programa (art. 10, apartado A, fracción X, LEM).

---

## 4. Fase 2: Pre-requisitos Específicos por Impacto
Para negocios que NO sean de Bajo Impacto, se debe obtener documentación extra.

- **Bajo Impacto:** Se salta esta fase directo al registro.
- **Impacto Vecinal y Zonal:**
  - **Requisito obligatorio:** *Constancia de no adeudo de predial y de agua*. 
  - **Links de trámite:** Se gestionan ante Tesorería y SACMEX mediante el formato de Finanzas: [https://data.finanzas.cdmx.gob.mx/formato_lc](https://data.finanzas.cdmx.gob.mx/formato_lc)

---

## 5. Fase 3: Registro en Plataforma (SIAPEM)
El usuario llega aquí ya con todos sus documentos digitalizados en PDF. El proceso en plataforma es lineal.

1. **Ingreso:** Entrar a [SIAPEM](https://siapem.cdmx.gob.mx/index.xhtml) con Llave CDMX.
2. **Alta del Negocio:**
   - Seleccionar **"Mis negocios"** -> **"Dar de alta nuevo negocio"**.
   - Seleccionar tipo de Persona (Física o Moral) y llenar datos.
3. **Selección del Trámite Específico:**
   - Ir a **"Mis trámites"** -> **"Registrar nuevo trámite"**.
   - Elegir el negocio.
   - Seleccionar el formato que le indicó el bot:
     - `EM-03` para **Bajo Impacto** (Aviso de funcionamiento).
     - `EM-11` para **Impacto Vecinal** (Aviso de funcionamiento).
     - `EM-08` para **Impacto Zonal** (OJO: Esto es una *Solicitud de Permiso*, no un aviso).
4. **Pago y Finalización:**
   - Para Bajo Impacto, solo se descarga el Acuse.
   - Para Impacto Vecinal/Zonal, se debe pagar la línea de captura de derechos (Art. 191 f. I o II del Código Fiscal CDMX).
   - Para **Impacto Zonal**, tras el pago, se debe esperar la *Autorización expresa de la Alcaldía*.

---

## 6. Tips y Casos Especiales (Migración)
Si el usuario ya tenía el registro en la plataforma SIAPEM anterior, el bot debe indicarle el flujo de "Migración":
- **NO** dar de alta nuevo negocio.
- Seleccionar **"Dar de alta un establecimiento que ya cuenta con Clave Única"**.
- Debe escanear en PDF los trámites anteriores (EM-03, EM-B, EM-11, EM-A, EM-08, etc.) y su Uso de Suelo original.
- Realizar el trámite correspondiente.

### Soporte Legal y Referencias
- **Centro Promotor de Inversión (CENPROIN):** Av. Cuauhtémoc 899, Col. Narvarte, Alcaldía Benito Juárez (L a V 9:00 a 14:30 hrs).
- **Dudas SIAPEM:** dudas.siapem@sedeco.cdmx.gob.mx
- **Leyes base:** [Ley de Establecimientos Mercantiles para la CDMX](https://prontuario.cdmx.gob.mx/pdf/Ley%20Establecimientos%20Mercantiles%2024122025.pdf) y su Reglamento.

---

## 7. Bases de Datos para Alimentar la Herramienta (Para el equipo de desarrollo)
Para que la Fase 0 funcione, debemos scrapear y conectar las siguientes bases a nuestra base de conocimientos:
1. **DENUE (INEGI):** Establecimientos Mercantiles (API o CSV).
2. **Catálogo RETYS CDMX:** Registro de Trámites y Servicios.
3. **SECTUR / Datatur:** Ocupación hotelera y afluencia.
4. **Cartelera CDMX y Datos Abiertos (SEDECO):** Para evaluar derrama de eventos masivos.
