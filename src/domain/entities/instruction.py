import re
import unicodedata
from dataclasses import dataclass
from typing import ClassVar, Optional

from src.domain.entities.source_type import SourceType

# Palabras clave que identifican un PDF como instrucción de un *entregable*
# (tarea, proyecto...), frente al ruido genérico del curso (reglamentos, normas
# APA, manuales, lineamientos...). Comparación sin acentos ni mayúsculas.
#
# OJO: "foro" NO está aquí a propósito. Un foro es un debate que abre/cierra por
# ventanas; su PDF de instrucciones (sin fecha) solo mete ruido. El foro abierto
# igual se avisa por el canal de eventos como "[Foro] ... — <fecha>".
_DELIVERABLE_KEYWORDS = (
    "tarea",
    "entrega",
    "proyecto",
    "practica",
    "laboratorio",
    "avance",
    "quiz",
    "examen",
    "parcial",
)

# Ruido que invalida a un PDF como instrucción de entregable AUNQUE contenga una
# palabra clave: manuales y lecturas/material de apoyo (p. ej. "Manual-informe-
# escrito-Proyecto" o "Consejos y Técnicas") no son la instrucción de una tarea
# concreta, así que no aportan valor como aviso. Comparación sin acentos.
_NOISE_KEYWORDS = (
    "manual",
    "consejos",
    "tecnica",   # cubre "técnica(s)"
    "lectura",   # cubre "lectura(s)"
)


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


# Relleno que aparece en los nombres pero no aporta identidad al entregable.
# Lo descartamos al tokenizar para que "Tarea No. 1" y "Tarea 1" coincidan.
_TOKEN_STOPWORDS = frozenset(
    {"de", "del", "la", "el", "los", "las", "y", "o", "u", "a",
     "no", "nro", "num", "numero", "n"}
)


def _tokens(text: str) -> frozenset[str]:
    """Tokens significativos de un nombre: sin acentos, en minúsculas, con la
    puntuación convertida en separador y descartando el relleno (`de`, `No`...).
    Un token numérico ("1") sí se conserva: distingue "Tarea 1" de "Tarea 2"."""
    normalized = _strip_accents(text).lower()
    raw = re.split(r"[^a-z0-9]+", normalized)
    return frozenset(t for t in raw if t and t not in _TOKEN_STOPWORDS)


@dataclass
class Instruction:
    """Recurso de archivo de un curso (p. ej. un PDF de instrucciones).

    Sigue el mismo patrón que Assignment/CalendarEvent: `moodle_id` es la
    identidad estable y `content_fingerprint` permite detectar si el contenido
    del fichero cambió sin descargarlo (se deriva del `timemodified` de Moodle).
    """

    moodle_id: int            # cmid del módulo (identidad estable)
    course_id: int
    name: str                 # nombre del recurso / filename
    url: str | None = None    # fileurl para abrir el PDF
    content_fingerprint: str | None = None  # str(timemodified) [+ filesize]
    kind: str = "resource"    # "resource" | "folder"
    id: Optional[int] = None
    # Presentation-only: never used in stable_key nor in diff comparison.
    course_name: str | None = None

    source_type: ClassVar[str] = SourceType.INSTRUCTION

    def stable_key(self) -> str:
        # Incluimos el nombre porque un módulo `folder` agrupa varios archivos
        # bajo el mismo cmid (moodle_id); el nombre los distingue.
        return f"instruction:{self.moodle_id}:{self.name.strip().lower()}"

    def dedup_key(self) -> tuple[int, frozenset[str]]:
        """Identidad para colapsar duplicados dentro de un mismo scan: mismo
        curso + mismos tokens de nombre. El profe a veces sube el mismo PDF dos
        veces (distinto cmid), y sin esto se avisaría repetido. "Tarea No.1" y
        "Tarea No. 1" comparten dedup_key. NO es la identidad de tracking (esa es
        `stable_key`, ligada al cmid para detectar cambios de contenido)."""
        return (self.course_id, _tokens(self.name))

    def changed_fields(self, other: "Instruction") -> list[str]:
        """El único cambio relevante sin descargar el PDF es la huella de
        contenido (derivada del timemodified de Moodle). Devuelve ["content"]
        cuando cambió; nunca desglosa otros campos."""
        if self.content_fingerprint != other.content_fingerprint:
            return ["content"]
        return []

    def to_dict(self) -> dict:
        return {
            "moodle_id": self.moodle_id,
            "course_id": self.course_id,
            "name": self.name,
            "url": self.url,
            "content_fingerprint": self.content_fingerprint,
            "kind": self.kind,
            "course_name": self.course_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Instruction":
        return cls(
            moodle_id=data["moodle_id"],
            course_id=data["course_id"],
            name=data["name"],
            url=data.get("url"),
            content_fingerprint=data.get("content_fingerprint"),
            kind=data.get("kind", "resource"),
            course_name=data.get("course_name"),
        )

    def is_deliverable(self) -> bool:
        """True si el PDF parece la instrucción de un entregable (tarea, foro,
        proyecto...) y no un recurso genérico del curso. Se decide por palabras
        clave en el nombre, sin distinguir acentos ni mayúsculas. Los manuales y
        lecturas se descartan aunque contengan una palabra clave."""
        # Un `mod_folder` es un basurero de material del curso (tutoriales, guías,
        # lecturas): un PDF que cae ahí y contiene "practica"/"proyecto" casi
        # siempre es material, no la instrucción de un entregable concreto. La
        # instrucción real es un `mod_resource` suelto que el profe enlaza aparte.
        # Si el entregable existe de verdad, igual se avisa por su assignment.
        if self.kind == "folder":
            return False
        normalized = _strip_accents(self.name).lower()
        if any(noise in normalized for noise in _NOISE_KEYWORDS):
            return False
        return any(keyword in normalized for keyword in _DELIVERABLE_KEYWORDS)

    def is_superseded_by(self, deliverable_name: str) -> bool:
        """True si este PDF queda absorbido por un entregable (Assignment) cuyo
        nombre `deliverable_name` está contenido, por tokens, en el nombre del
        recurso. Es decir, el espacio de entrega ya cubre lo que el PDF anunciaba
        ("Tarea 1" ⊆ "Instrucciones Tarea 1"), así que el PDF deja de ser noticia
        aparte. La validación de que ambos son del mismo curso se hace afuera."""
        target = _tokens(deliverable_name)
        if not target:
            return False
        return target <= _tokens(self.name)
