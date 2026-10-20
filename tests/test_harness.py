"""Test Harness do TaskAnalyzer (pytest).

Traduz os cenários de aceite 1 a 5 da seção 2.1 da especificação.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.task_analyzer import (  # noqa: E402
    InvalidDateRangeError,
    InvalidPriorityError,
    Tarefa,
    TaskValidationError,
    analyze_tasks,
    converter_para_utc,
)

UTC = timezone.utc
BASE = datetime(2026, 1, 5, 8, 0, tzinfo=UTC)


def hora(h: int, m: int = 0) -> datetime:
    """Cria um datetime UTC no dia-base com a hora indicada."""
    return BASE.replace(hour=h, minute=m)


def tarefa(id_tarefa: int = 1, **kwargs) -> Tarefa:
    """Fábrica de tarefa válida (pendente) com overrides."""
    dados = {
        "id_tarefa": id_tarefa,
        "titulo": f"Tarefa {id_tarefa}",
        "prioridade": "media",
        "data_criacao": hora(8),
        "prazo": hora(18),
        "status": "pendente",
    }
    dados.update(kwargs)
    return Tarefa(**dados)


def concluida(id_tarefa: int, prioridade: str, inicio: datetime,
              conclusao: datetime, prazo: datetime) -> Tarefa:
    """Fábrica de tarefa concluída."""
    return tarefa(
        id_tarefa, prioridade=prioridade, status="concluida",
        data_inicio=inicio, data_conclusao=conclusao, prazo=prazo,
    )


@pytest.fixture
def tarefas_mistas() -> list[Tarefa]:
    """Conjunto do Cenário 1: concluídas, pendente e cancelada."""
    return [
        concluida(1, "alta", hora(9), hora(11), hora(12)),        # 120 min
        concluida(2, "alta", hora(9), hora(10), hora(9, 30)),     # 60, atraso
        concluida(3, "media", hora(9), hora(12), hora(18)),       # 180
        concluida(4, "baixa", hora(9), hora(9, 30), hora(9)),     # 30, atraso
        tarefa(5, prioridade="media", status="pendente"),
        tarefa(6, prioridade="baixa", status="cancelada"),
    ]


# --------------------------- Cenário 1: sucesso --------------------------- #
class TestCenario1Sucesso:
    """Cálculo geral de métricas."""

    def test_metricas_gerais(self, tarefas_mistas):
        r = analyze_tasks(tarefas_mistas)
        assert r["tempo_medio_conclusao_min"] == 97.5
        assert r["taxa_atraso_percentual"] == 50.0
        assert r["quantidade_total_tarefas"] == 6

    def test_indicadores_por_prioridade(self, tarefas_mistas):
        ind = analyze_tasks(tarefas_mistas)["indicadores_por_prioridade"]
        assert ind["alta"] == {
            "quantidade": 2, "tempo_medio_conclusao_min": 90.0,
            "taxa_atraso_percentual": 50.0}
        assert ind["media"] == {
            "quantidade": 2, "tempo_medio_conclusao_min": 180.0,
            "taxa_atraso_percentual": 0.0}
        assert ind["baixa"] == {
            "quantidade": 2, "tempo_medio_conclusao_min": 30.0,
            "taxa_atraso_percentual": 100.0}

    def test_distribuicao_por_status(self, tarefas_mistas):
        dist = analyze_tasks(tarefas_mistas)["distribuicao_por_status"]
        assert dist == {"concluida": 4, "pendente": 1, "cancelada": 1}

    def test_arredondamento_duas_casas(self):
        tarefas = [
            concluida(1, "alta", hora(9), hora(9, 10), hora(18)),
            concluida(2, "alta", hora(9), hora(9, 10), hora(18)),
            concluida(3, "alta", hora(9), hora(9, 11), hora(18)),
        ]
        assert analyze_tasks(tarefas)["tempo_medio_conclusao_min"] == 10.33

    def test_conclusao_no_prazo_exato_nao_e_atraso(self):
        t = concluida(1, "alta", hora(9), hora(10), hora(10))
        assert analyze_tasks([t])["taxa_atraso_percentual"] == 0.0

    def test_fuso_horario_convertido_para_utc(self):
        br = timezone(timedelta(hours=-3))
        # 08:00-03:00 == 11:00 UTC; inicio 09:00 UTC => 120 min, prazo 11:30
        t = concluida(1, "alta", hora(9),
                      datetime(2026, 1, 5, 8, 0, tzinfo=br), hora(11, 30))
        r = analyze_tasks([t])
        assert r["tempo_medio_conclusao_min"] == 120.0
        assert r["taxa_atraso_percentual"] == 0.0

    def test_datetime_sem_fuso_assumido_utc(self):
        naive = datetime(2026, 1, 5, 9, 0)
        assert converter_para_utc(naive) == hora(9)

    def test_concluida_sem_inicio_conta_no_atraso_mas_nao_no_tempo(self):
        sem_inicio = tarefa(1, status="concluida", data_conclusao=hora(20))
        com_inicio = concluida(2, "media", hora(9), hora(10), hora(18))
        r = analyze_tasks([sem_inicio, com_inicio])
        assert r["tempo_medio_conclusao_min"] == 60.0
        assert r["taxa_atraso_percentual"] == 50.0

    @pytest.mark.parametrize("prioridade", ["baixa", "media", "alta"])
    @pytest.mark.parametrize("status", ["concluida", "pendente", "cancelada"])
    def test_quantidade_por_prioridade_ignora_status(self, prioridade, status):
        extra = {"data_conclusao": hora(10)} if status == "concluida" else {}
        t = tarefa(1, prioridade=prioridade, status=status, **extra)
        ind = analyze_tasks([t])["indicadores_por_prioridade"]
        assert ind[prioridade]["quantidade"] == 1
        assert sum(g["quantidade"] for g in ind.values()) == 1


# ----------------------- Cenário 2: datas inválidas ----------------------- #
class TestCenario2DatasInvalidas:
    """Datas inconsistentes disparam exceção específica."""

    def test_conclusao_antes_do_inicio(self):
        t = concluida(7, "alta", hora(10), hora(9), hora(18))
        with pytest.raises(InvalidDateRangeError, match="data_conclusao anterior") as exc:
            analyze_tasks([t])
        assert exc.value.id_tarefa == 7
        assert "7" in str(exc.value)

    def test_inicio_antes_da_criacao(self):
        t = tarefa(8, status="pendente", data_inicio=hora(7))
        with pytest.raises(InvalidDateRangeError, match="data_inicio anterior") as exc:
            analyze_tasks([t])
        assert exc.value.id_tarefa == 8

    def test_conclusao_antes_da_criacao_sem_inicio(self):
        t = tarefa(9, status="concluida", data_conclusao=hora(7))
        with pytest.raises(InvalidDateRangeError):
            analyze_tasks([t])

    def test_uma_invalida_entre_validas_interrompe(self, tarefas_mistas):
        tarefas_mistas.append(concluida(10, "baixa", hora(11), hora(9), hora(18)))
        with pytest.raises(InvalidDateRangeError):
            analyze_tasks(tarefas_mistas)

    def test_exce_especificas_herdam_de_task_validation_error(self):
        assert issubclass(InvalidDateRangeError, TaskValidationError)
        assert issubclass(InvalidPriorityError, TaskValidationError)
        t = concluida(1, "alta", hora(10), hora(9), hora(18))
        with pytest.raises(TaskValidationError):
            analyze_tasks([t])


# ---------------- Cenário 3: ausência de tarefas concluídas --------------- #
class TestCenario3SemConcluidas:
    """Retorno 0.0 sem ZeroDivisionError e com aviso em log."""

    def test_lista_vazia(self, caplog):
        with caplog.at_level(logging.WARNING):
            r = analyze_tasks([])
        assert r["tempo_medio_conclusao_min"] == 0.0
        assert r["taxa_atraso_percentual"] == 0.0
        assert r["quantidade_total_tarefas"] == 0
        assert "Nenhuma tarefa concluída" in caplog.text

    def test_somente_pendentes_e_canceladas(self, caplog):
        tarefas = [tarefa(1, status="pendente"),
                   tarefa(2, prioridade="alta", status="cancelada")]
        with caplog.at_level(logging.WARNING):
            r = analyze_tasks(tarefas)
        assert r["tempo_medio_conclusao_min"] == 0.0
        assert r["taxa_atraso_percentual"] == 0.0
        assert r["quantidade_total_tarefas"] == 2
        for grupo in r["indicadores_por_prioridade"].values():
            assert grupo["tempo_medio_conclusao_min"] == 0.0
            assert grupo["taxa_atraso_percentual"] == 0.0
        assert caplog.records


# ------------------- Cenário 4: prioridade inválida ----------------------- #
class TestCenario4PrioridadeInvalida:
    """Prioridade fora do enum gera InvalidPriorityError."""

    @pytest.mark.parametrize("valor", ["urgente", "ALTA", "", "média", None])
    def test_prioridade_invalida(self, valor):
        with pytest.raises(InvalidPriorityError, match="prioridade inválida"):
            analyze_tasks([tarefa(3, prioridade=valor)])


# ----------------- Cenário 5: pendente sem data de conclusão -------------- #
class TestCenario5PendenteSemConclusao:
    """Pendente conta no total, mas não nos cálculos."""

    def test_pendente_contabilizada_e_excluida_dos_calculos(self):
        tarefas = [
            concluida(1, "alta", hora(9), hora(10), hora(18)),
            tarefa(2, prioridade="alta", status="pendente", data_conclusao=None),
        ]
        r = analyze_tasks(tarefas)
        assert r["quantidade_total_tarefas"] == 2
        assert r["tempo_medio_conclusao_min"] == 60.0
        assert r["taxa_atraso_percentual"] == 0.0
        assert r["indicadores_por_prioridade"]["alta"]["quantidade"] == 2


# ------------------ Validações adicionais do contrato --------------------- #
class TestValidacoesContrato:
    """Demais violações do contrato de entrada."""

    def test_concluida_sem_data_conclusao(self):
        with pytest.raises(TaskValidationError, match="data_conclusao é obrigatória"):
            analyze_tasks([tarefa(1, status="concluida")])

    @pytest.mark.parametrize("id_invalido", [0, -1, "1", True, None])
    def test_id_invalido(self, id_invalido):
        with pytest.raises(TaskValidationError, match="id_tarefa"):
            analyze_tasks([tarefa(id_invalido)])

    def test_id_duplicado(self):
        with pytest.raises(TaskValidationError, match="duplicado"):
            analyze_tasks([tarefa(1), tarefa(1)])

    @pytest.mark.parametrize("titulo", ["", "   ", None])
    def test_titulo_vazio(self, titulo):
        with pytest.raises(TaskValidationError, match="titulo"):
            analyze_tasks([tarefa(1, titulo=titulo)])

    def test_status_invalido(self):
        with pytest.raises(TaskValidationError, match="status inválido"):
            analyze_tasks([tarefa(1, status="em_andamento")])

    @pytest.mark.parametrize("campo", ["data_criacao", "prazo"])
    def test_datas_obrigatorias(self, campo):
        with pytest.raises(TaskValidationError, match="obrigatórios"):
            analyze_tasks([tarefa(1, **{campo: None})])
