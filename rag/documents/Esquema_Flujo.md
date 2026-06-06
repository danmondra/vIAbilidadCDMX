# Esquema de Flujo del Asesor Virtual

El siguiente diagrama modela el journey del usuario a través del asesor virtual. Está construido en lenguaje `mermaid` para facilitar modificaciones futuras.

```mermaid
graph TD
    %% Estilos de fases
    classDef fase0 fill:#ffe0b2,stroke:#f57c00,stroke-width:2px;
    classDef fase1 fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef fase2 fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px;
    classDef fase3 fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef db fill:#cfd8dc,stroke:#607d8b,stroke-width:2px,stroke-dasharray: 5 5;

    %% Bases de Datos / Fuentes
    DB1[(DENUE / Censos \n Económicos)]:::db
    DB2[(SEDUVI \n Uso de Suelo)]:::db
    DB3[(Ley de Establ. \n Mercantiles CDMX)]:::db

    A([Inicio: Interacción por Chat]) --> B[Paso 1: Entrevista de Perfilamiento \n Giro, Ubicación, Aforo]:::fase0
    
    B --> C[Paso 2: Análisis de Viabilidad Comercial]:::fase0
    DB1 -.-> C
    C --> C1[Mostrar Nivel de Competencia \n Local, Zonal y de Alcaldía]:::fase0
    C --> C2[Proyección de Rentabilidad / \n Demanda Estimada]:::fase0
    
    C1 --> D{Paso 3: Validación de \n Uso de Suelo}:::fase0
    C2 --> D
    DB2 -.-> D
    
    D -->|Incompatible| E[Sugerir nuevas zonas o \n cambio de giro comercial]:::fase0
    E --> B
    D -->|Compatible| F[Paso 4: Clasificación del Negocio \n Bajo, Vecinal o Zonal]:::fase0
    DB3 -.-> F
    
    F --> G[Presentación del \n Roadmap de Trámites]:::fase1
    
    G --> H[Fase 1: Obtener Documentos Base \n Llave CDMX, Certificado SEDUVI]:::fase1
    H --> I{Evaluación de Protección Civil \n ¿Más de 100 personas o > 250 m2?}:::fase1
    I -->|Sí| J[Obligatorio: Prog. Interno Prot. Civil]:::fase1
    I -->|No| K[Exento de Prog. Prot. Civil]:::fase1
    
    J --> L{Tipo de Impacto Legal \n detectado}:::fase2
    K --> L
    
    L -->|Bajo Impacto| M[Fase 2 Directa: \n Registro SIAPEM]:::fase3
    L -->|Impacto Vecinal / Zonal| N[Requisito Previo: Constancias de \n No Adeudo Agua y Predial]:::fase2
    
    N --> O[Fase 2: Registro SIAPEM]:::fase3
    
    M --> M1[Llenar Formato EM-03 \n Aviso de Funcionamiento]:::fase3
    O --> O1{Selección de Formato}:::fase3
    
    O1 -->|Vecinal| V1[Formato EM-11 \n Aviso de Funcionamiento]:::fase3
    O1 -->|Zonal| Z1[Formato EM-08 \n Solicitud de Permiso]:::fase3
    
    V1 --> P[Pago de Derechos art. 191 f. I]:::fase3
    Z1 --> R[Pago de Derechos art. 191 f. II \n + Esperar Autorización Alcaldía]:::fase3
    
    M1 --> Q([Fin: Descargar Acuse e Imprimir])
    P --> Q
    R --> Q
```
