import pytest

from src.domain.entities.instruction import Instruction


def make(name: str) -> Instruction:
    return Instruction(moodle_id=1, course_id=9460, name=name)


@pytest.mark.parametrize(
    "name",
    [
        "Tarea No.1",
        "Guía del Proyecto Final",
        "Práctica de laboratorio",  # acento
        "PRÁCTICA 2",               # acento + mayúsculas
        "Avance 1",
        "Examen parcial",
    ],
)
def test_deliverable_pdfs_are_kept(name: str):
    assert make(name).is_deliverable() is True


@pytest.mark.parametrize(
    "name",
    [
        "Foro No.1",
        "03634 Foro 1",
        "Foro de debate 2",
    ],
)
def test_forum_pdfs_are_discarded(name: str):
    """Los PDF de foro no se notifican como instrucción: el foro abierto se
    avisa como evento [Foro] con su fecha, y su PDF (sin fecha) solo metía ruido
    porque los foros abren/cierran por ventanas."""
    assert make(name).is_deliverable() is False


@pytest.mark.parametrize(
    "name",
    [
        "Reglamento general estudiantil",
        "Normas APA. Edition 6",
        "Lineamientos en caso de plagio",
        "Manual SAIE, Usuario Estudiante 1.2",
        "Orientación Académica",
        "Estándar IEEE 830",
        "Guía de inducción a la UNED",
    ],
)
def test_generic_resources_are_discarded(name: str):
    assert make(name).is_deliverable() is False


@pytest.mark.parametrize(
    "name",
    [
        # Contienen palabra clave de entregable pero son manuales/lecturas:
        # no son la instrucción de una tarea concreta, así que se descartan.
        "01- STFG_88-Manual-informe-escrito-Proyecto v1.pdf",
        "02- STFG_88-Manual-informe-escrito-Practica Dirigida IS_2026.pdf",
        "Desarrollo de proyectos TIC – Consejos y Técnicas.pdf",
    ],
)
def test_manuals_and_readings_are_discarded(name: str):
    assert make(name).is_deliverable() is False


# --- is_superseded_by: el PDF queda absorbido por su espacio de entrega ---

@pytest.mark.parametrize(
    "pdf_name,assignment_name",
    [
        ("Instrucciones Tarea 1", "Tarea 1"),
        ("Tarea No.1", "Tarea 1"),                  # relleno "No." ignorado
        ("03634 Foro 1", "Foro 1"),                 # código de curso sobra
        ("PRÁCTICA 2 - enunciado", "Práctica 2"),   # acentos + mayúsculas
        ("Guía del Proyecto Final", "Proyecto Final"),
    ],
)
def test_pdf_is_superseded_by_matching_assignment(pdf_name: str, assignment_name: str):
    assert make(pdf_name).is_superseded_by(assignment_name) is True


@pytest.mark.parametrize(
    "pdf_name,assignment_name",
    [
        ("Tarea 1", "Tarea 2"),          # número distinto
        ("Tarea 10", "Tarea 1"),         # "1" no es token de "Tarea 10"
        ("Foro 1", "Tarea 1"),           # tipo distinto
        ("Instrucciones Tarea 1", ""),   # nombre vacío no empareja nada
    ],
)
def test_pdf_is_not_superseded_by_unrelated_assignment(pdf_name: str, assignment_name: str):
    assert make(pdf_name).is_superseded_by(assignment_name) is False
