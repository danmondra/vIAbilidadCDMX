# Estados FSM para el bot ViableCDMX
# Cada constante representa un estado de la conversación en el ConversationHandler

# Estados del flujo principal (0-5)
MENU, ASK_GIRO, ASK_UBICACION, ASK_M2, ASK_AFORO, ASK_ALCOHOL = range(6)

# Estados de procesamiento y viabilidad (6-8)
PROCESANDO, MOSTRAR_VIABILIDAD, CONFIRM_TRAMITES = range(6, 9)

# Estados del flujo de trámites (9-12)
FASE1, FASE2, FASE3_SIAPEM, CHECKLIST = range(9, 13)

# Estados especiales (13-14)
MIGRACION, APOYO = range(13, 15)
