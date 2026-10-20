"""Módulo TaskAnalyzer: análise de tarefas e métricas de produtividade.

Implementa o contrato definido em ``specs/task_analyzer_spec.md``.
A função pública principal é :func:`analyze_tasks`.

Decisões de projeto (ver CONTEXT_RULES.md):
    * Somente biblioteca padrão do Python.
    * Entidade (``Tarefa``), motor de cálculo e utilitários de data separados.
    * Datas normalizadas para UTC; datas sem fuso são assumidas como UTC.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Sequence

logger = logging.getLogger(__name__)

PRIORIDADES_VALIDAS: tuple[str, ...] = ("baixa", "media", "alta")
STATUS_VALIDOS: tuple[str, ...] = ("concluida", "pendente", "cancelada")
CASAS_DECIMAIS: int = 2


# --------------------------------------------------------------------------- #
# Exceções
# --------------------------------------------------------------------------- #
class TaskValidationError(ValueError):
    """Erro base de validação de tarefas.

    Attributes:
        id_tarefa: Identificador da tarefa inválida (ou ``None``).
        motivo: Descrição do motivo da inconsistência.
    """

    def __init__(self, id_tarefa: int | None, motivo: str) -> None:
        """Inicializa a exceção.

        Args:
            id_tarefa: Identificador da tarefa que causou o erro.
            motivo: Explicação clara da inconsistência.
        """
        self.id_tarefa = id_tarefa
        self.motivo = motivo
        super().__init__(f"Tarefa {id_tarefa}: {motivo}")


class InvalidDateRangeError(TaskValidationError):
    """Datas inconsistentes (ex.: conclusão anterior ao início)."""


class InvalidPriorityError(TaskValidationError):
    """Prioridade fora de "baixa", "media" ou "alta"."""


# --------------------------------------------------------------------------- #
# Entidade
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Tarefa:
    """Entidade de tarefa conforme o contrato de entrada (seção 1.2.1).

    Attributes:
        id_tarefa: Identificador único (> 0).
        titulo: Título curto, não vazio.
        prioridade: "baixa", "media" ou "alta".
        data_criacao: Data/hora de criação.
        prazo: Data/hora limite de conclusão.
        status: "concluida", "pendente" ou "cancelada".
        data_inicio: Data/hora de início (opcional).
        data_conclusao: Data/hora de conclusão (obrigatória se concluída).
    """

    id_tarefa: int
    titulo: str
    prioridade: str
    data_criacao: datetime
    prazo: datetime
    status: str
    data_inicio: datetime | None = None
    data_conclusao: datetime | None = None


# --------------------------------------------------------------------------- #
# Utilitários de data
# --------------------------------------------------------------------------- #
def converter_para_utc(valor: datetime) -> datetime:
    """Converte um datetime para UTC.

    Datetimes sem fuso (naive) são interpretados como UTC.

    Args:
        valor: Data/hora a converter.

    Returns:
        Data/hora com fuso UTC.
    """
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _converter_opcional(valor: datetime | None) -> datetime | None:
    """Converte para UTC preservando ``None``.

    Args:
        valor: Data/hora ou ``None``.

    Returns:
        Data/hora em UTC ou ``None``.
    """
    return None if valor is None else converter_para_utc(valor)


def normalizar_datas(tarefa: Tarefa) -> Tarefa:
    """Retorna uma cópia da tarefa com todas as datas em UTC.

    Args:
        tarefa: Tarefa original.

    Returns:
        Nova tarefa com datas normalizadas.
    """
    return replace(
        tarefa,
        data_criacao=converter_para_utc(tarefa.data_criacao),
        prazo=converter_para_utc(tarefa.prazo),
        data_inicio=_converter_opcional(tarefa.data_inicio),
        data_conclusao=_converter_opcional(tarefa.data_conclusao),
    )


def diferenca_em_minutos(inicio: datetime, fim: datetime) -> float:
    """Calcula a diferença entre duas datas em minutos.

    Args:
        inicio: Data/hora inicial.
        fim: Data/hora final.

    Returns:
        Minutos entre ``inicio`` e ``fim``.
    """
    return (fim - inicio).total_seconds() / 60


# --------------------------------------------------------------------------- #
# Validação
# --------------------------------------------------------------------------- #
def _validar_campos(tarefa: Tarefa) -> None:
    """Valida campos obrigatórios e enums de uma tarefa.

    Args:
        tarefa: Tarefa a validar.

    Raises:
        InvalidPriorityError: Se a prioridade for inválida.
        TaskValidationError: Para id, título, status ou datas obrigatórias
            inválidos.
    """
    id_ = tarefa.id_tarefa
    if isinstance(id_, bool) or not isinstance(id_, int) or id_ <= 0:
        raise TaskValidationError(id_, "id_tarefa deve ser um inteiro > 0")
    if not isinstance(tarefa.titulo, str) or not tarefa.titulo.strip():
        raise TaskValidationError(id_, "titulo não pode ser vazio")
    if tarefa.prioridade not in PRIORIDADES_VALIDAS:
        raise InvalidPriorityError(
            id_, f"prioridade inválida: {tarefa.prioridade!r}"
        )
    if tarefa.status not in STATUS_VALIDOS:
        raise TaskValidationError(id_, f"status inválido: {tarefa.status!r}")
    if tarefa.data_criacao is None or tarefa.prazo is None:
        raise TaskValidationError(id_, "data_criacao e prazo são obrigatórios")
    if tarefa.status == "concluida" and tarefa.data_conclusao is None:
        raise TaskValidationError(
            id_, "data_conclusao é obrigatória para tarefas concluídas"
        )


def _validar_datas(tarefa: Tarefa) -> None:
    """Valida a coerência cronológica das datas (já em UTC).

    Args:
        tarefa: Tarefa com datas normalizadas.

    Raises:
        InvalidDateRangeError: Se houver inconsistência cronológica.
    """
    id_ = tarefa.id_tarefa
    inicio, conclusao = tarefa.data_inicio, tarefa.data_conclusao
    if inicio is not None and inicio < tarefa.data_criacao:
        raise InvalidDateRangeError(id_, "data_inicio anterior à data_criacao")
    if conclusao is not None and inicio is not None and conclusao < inicio:
        raise InvalidDateRangeError(id_, "data_conclusao anterior à data_inicio")
    if conclusao is not None and conclusao < tarefa.data_criacao:
        raise InvalidDateRangeError(
            id_, "data_conclusao anterior à data_criacao"
        )


def _validar_unicidade(tarefas: Sequence[Tarefa]) -> None:
    """Garante que não existam ``id_tarefa`` repetidos.

    Args:
        tarefas: Coleção de tarefas.

    Raises:
        TaskValidationError: Se houver id duplicado.
    """
    vistos: set[int] = set()
    for tarefa in tarefas:
        if tarefa.id_tarefa in vistos:
            raise TaskValidationError(tarefa.id_tarefa, "id_tarefa duplicado")
        vistos.add(tarefa.id_tarefa)


def _preparar_tarefas(tarefas: Sequence[Tarefa]) -> list[Tarefa]:
    """Valida e normaliza (UTC) todas as tarefas.

    Args:
        tarefas: Tarefas de entrada.

    Returns:
        Lista de tarefas válidas com datas em UTC.
    """
    for tarefa in tarefas:
        _validar_campos(tarefa)
    _validar_unicidade(tarefas)
    normalizadas = [normalizar_datas(t) for t in tarefas]
    for tarefa in normalizadas:
        _validar_datas(tarefa)
    return normalizadas


# --------------------------------------------------------------------------- #
# Cálculo de métricas
# --------------------------------------------------------------------------- #
def _filtrar_concluidas(tarefas: Sequence[Tarefa]) -> list[Tarefa]:
    """Seleciona apenas tarefas com status "concluida".

    Args:
        tarefas: Tarefas normalizadas.

    Returns:
        Tarefas concluídas.
    """
    return [t for t in tarefas if t.status == "concluida"]


def _calcular_tempo_medio(concluidas: Sequence[Tarefa]) -> float:
    """Calcula o tempo médio de conclusão em minutos.

    Considera apenas tarefas com ``data_inicio`` e ``data_conclusao``.

    Args:
        concluidas: Tarefas concluídas.

    Returns:
        Média arredondada em 2 casas; ``0.0`` se não houver amostras.
    """
    tempos = [
        diferenca_em_minutos(t.data_inicio, t.data_conclusao)
        for t in concluidas
        if t.data_inicio is not None and t.data_conclusao is not None
    ]
    if not tempos:
        return 0.0
    return round(sum(tempos) / len(tempos), CASAS_DECIMAIS)


def _calcular_taxa_atraso(concluidas: Sequence[Tarefa]) -> float:
    """Calcula o percentual de tarefas concluídas após o prazo.

    Args:
        concluidas: Tarefas concluídas.

    Returns:
        Percentual (0-100) arredondado em 2 casas; ``0.0`` se vazio.
    """
    if not concluidas:
        return 0.0
    atrasadas = sum(
        1
        for t in concluidas
        if t.data_conclusao is not None and t.data_conclusao > t.prazo
    )
    return round(atrasadas / len(concluidas) * 100, CASAS_DECIMAIS)


def _indicadores_prioridade(
    tarefas: Sequence[Tarefa], prioridade: str
) -> dict[str, float | int]:
    """Calcula os indicadores de um grupo de prioridade.

    Args:
        tarefas: Todas as tarefas normalizadas.
        prioridade: Prioridade do grupo.

    Returns:
        Dicionário com quantidade, tempo médio e taxa de atraso do grupo.
    """
    grupo = [t for t in tarefas if t.prioridade == prioridade]
    concluidas = _filtrar_concluidas(grupo)
    return {
        "quantidade": len(grupo),
        "tempo_medio_conclusao_min": _calcular_tempo_medio(concluidas),
        "taxa_atraso_percentual": _calcular_taxa_atraso(concluidas),
    }


def _distribuicao_por_status(tarefas: Sequence[Tarefa]) -> dict[str, int]:
    """Conta as tarefas por status.

    Args:
        tarefas: Tarefas normalizadas.

    Returns:
        Dicionário status -> quantidade (todos os status presentes).
    """
    return {s: sum(1 for t in tarefas if t.status == s) for s in STATUS_VALIDOS}


# --------------------------------------------------------------------------- #
# API pública
# --------------------------------------------------------------------------- #
def analyze_tasks(tasks: Sequence[Tarefa]) -> dict[str, Any]:
    """Analisa uma coleção de tarefas e gera o relatório de métricas.

    Args:
        tasks: Tarefas a analisar (pode ser vazia).

    Returns:
        Dicionário com as chaves ``tempo_medio_conclusao_min``,
        ``taxa_atraso_percentual``, ``quantidade_total_tarefas``,
        ``indicadores_por_prioridade`` e ``distribuicao_por_status``.

    Raises:
        InvalidPriorityError: Se alguma prioridade for inválida.
        InvalidDateRangeError: Se houver datas inconsistentes.
        TaskValidationError: Para demais violações do contrato.
    """
    tarefas = _preparar_tarefas(tasks)
    concluidas = _filtrar_concluidas(tarefas)
    if not concluidas:
        logger.warning(
            "Nenhuma tarefa concluída: métricas retornadas como 0.0."
        )
    return {
        "tempo_medio_conclusao_min": _calcular_tempo_medio(concluidas),
        "taxa_atraso_percentual": _calcular_taxa_atraso(concluidas),
        "quantidade_total_tarefas": len(tarefas),
        "indicadores_por_prioridade": {
            p: _indicadores_prioridade(tarefas, p) for p in PRIORIDADES_VALIDAS
        },
        "distribuicao_por_status": _distribuicao_por_status(tarefas),
    }
