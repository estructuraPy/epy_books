"""Editorial apparatus for a book: preface, glossary, guide and appendix."""

# ruff: noqa: E501

from __future__ import annotations


def preface(title: str) -> str:
    """Build the preface."""
    return f"""# Prefacio

Este volumen, *{title}*, forma parte de la colección El arte estructural. Reúne el fundamento técnico, los casos y la práctica de una disciplina que se aprende leyendo obras, verificando decisiones y documentando la evidencia.

El libro no sustituye la norma, el contrato ni la memoria de cálculo de una obra real. Ofrece un mapa para decidir qué información necesita un proyecto y cómo comprobarla.

## Cómo está organizado

Cada capítulo abre con un problema, desarrolla el fundamento, lo aplica a casos y cierra con una práctica verificable. Las tablas comparan decisiones; las figuras muestran el sistema; las ecuaciones conectan la magnitud con la consecuencia.

## Qué se espera del lector

El lector debe poder explicar una decisión, reconocer sus límites y dejar un registro que otra persona pueda revisar. La calidad del libro se mide por la claridad de esa cadena, no por el número de páginas.
"""


def glossary(title: str, chapters: list[str]) -> str:
    """Build the glossary."""
    terms = [
        (
            "Estructura",
            "Sistema que conduce las cargas hasta el terreno y mantiene su forma.",
        ),
        ("Carga", "Acción exterior que solicita la estructura."),
        ("Esfuerzo", "Fuerza interna por unidad de área."),
        ("Deformación", "Cambio de forma o de longitud bajo carga."),
        ("Rigidez", "Capacidad de resistir deformación."),
        ("Resistencia", "Capacidad de soportar una solicitación sin fallar."),
        ("Estabilidad", "Capacidad de mantener el equilibrio."),
        ("Ductilidad", "Capacidad de deformarse antes de la falla."),
        ("Tolerancia", "Desviación aceptada por el proyecto."),
        ("Incertidumbre", "Rango en el que se espera el valor medido."),
        ("Evidencia", "Dato, ensayo o registro que sostiene una afirmación."),
        ("Trazabilidad", "Capacidad de reconstruir una decisión."),
    ]
    lines = [
        "# Glosario\n",
        "Los términos se usan con el mismo sentido en todos los capítulos.\n",
    ]
    for term, definition in terms:
        lines.append(f"**{term}.** {definition}\n")
    lines.append("## Términos por capítulo\n")
    for chapter in chapters:
        lines.append(f"### {chapter}\n")
        lines.append(
            f"El capítulo desarrolla los términos propios de {chapter.lower()} y los conecta con el glosario común.\n"
        )
    return "\n".join(lines)


def study_guide(title: str, chapters: list[str]) -> str:
    """Build the study guide."""
    lines = [
        "# Guía de estudio\n",
        f"Esta guía acompaña *{title}* y propone una lectura activa.\n",
    ]
    for i, chapter in enumerate(chapters, 1):
        lines += [
            f"## Sesión {i}. {chapter}\n",
            f"La sesión desarrolla {chapter.lower()} con un problema, un desarrollo y una práctica.\n",
            "### Ideas centrales\n",
            f"- El problema que resuelve {chapter.lower()}.\n",
            "- Las hipótesis que el modelo necesita.\n",
            "- La evidencia que permite verificarlo.\n",
            "### Ejercicio\n",
            f"Reconstruya una decisión de {chapter.lower()} y escriba qué dato, qué criterio y qué registro la sostienen.\n",
            "### Criterio de aceptación\n",
            "La respuesta debe distinguir el cálculo, la construcción, la verificación y el límite del modelo.\n",
        ]
    return "\n".join(lines)


def appendix(title: str, chapters: list[str]) -> str:
    """Build the formula appendix."""
    lines = ["# Apéndice. Tablas y ecuaciones de consulta\n"]
    for i, chapter in enumerate(chapters, 1):
        lines += [
            f"## A.{i}. {chapter}\n",
            "| Concepto | Pregunta | Evidencia |\n",
            "|---|---|---|\n",
            f"| Fundamento | ¿Qué relación gobierna {chapter.lower()}? | Derivación |\n",
            "| Caso | ¿Qué decisión permite? | Ejemplo |\n",
            "| Límite | ¿Qué deja fuera el modelo? | Verificación |\n",
            "\n",
        ]
    return "\n".join(lines)


def assemble(title: str, chapters: list[str]) -> str:
    """Assemble the editorial apparatus."""
    return (
        "\n\n".join(
            [
                preface(title),
                glossary(title, chapters),
                study_guide(title, chapters),
                appendix(title, chapters),
            ]
        )
        + "\n"
    )
