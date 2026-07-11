"""Asuntos de notificación por tipo (canal-agnósticos).

Los canales con asunto (email) los usan; los que no (Telegram) los ignoran. Viven
acá para que los casos de uso los pasen a `dispatcher.dispatch(..., subject=...)` sin
depender de un canal concreto.
"""

SUBJECT_CHANGES = "CampusGuardian • Novedades en tu campus"
SUBJECT_WELCOME = "CampusGuardian • ¡Bienvenido!"
SUBJECT_RELINK = "CampusGuardian • Vínculo reactivado"
SUBJECT_DIGEST = "CampusGuardian • Tu resumen semanal"
SUBJECT_REMINDER = "CampusGuardian • Entregas próximas"
SUBJECT_TOKEN_EXPIRED = "CampusGuardian • Conexión expirada"
