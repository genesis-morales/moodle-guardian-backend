class SourceType:
    """Tipos de fuente rastreable de un campus Moodle.

    Un `source_type` identifica QUÉ clase de ítem es (tarea, evento, anuncio...).
    Junto con el id del ítem forma la identidad `(source_type, item_id)` que usa el
    diff y la persistencia; cuando exista multi-campus (feat 2) se le antepone el
    `connection_id` sin tocar nada de esto.

    Son constantes string (no Enum) para que viajen tal cual al JSONB del snapshot
    y a las llaves del diccionario `Snapshot.items`.
    """

    ASSIGNMENT = "assignment"
    EVENT = "event"
    INSTRUCTION = "instruction"

    # Reservados para feat 1b (aún sin implementar). Se listan para fijar el
    # vocabulario y que agregarlos sea solo enchufar la fuente, no inventar el nombre.
    ANNOUNCEMENT = "announcement"  # foro Novedades/News (mod_forum_get_forum_discussions)
    MESSAGE = "message"            # mensajes privados (core_message_get_conversations)
