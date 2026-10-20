# sdd-taskanalyzer

Módulo Python de análise de tarefas e produtividade, desenvolvido com **Spec-Driven Development (SDD)**
e código gerado por IA sob governança (`CONTEXT_RULES.md`) e homologação humana.

**Bootcamp III — ADS (CEUB EAD)** · Autora: Renata Teixeira de Jesus

## Estrutura
```
sdd-taskanalyzer/
├── README.md
├── CONTEXT_RULES.md
├── requirements.txt
├── .gitignore
├── specs/task_analyzer_spec.md
├── tests/test_harness.py
└── src/task_analyzer.py
```

## Como executar
Requer Python 3.11+.
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
pytest -v                       # roda o Test Harness
pytest --cov=src --cov-report=term-missing
```

## Exemplo de uso
```python
from datetime import datetime, timezone
from src.task_analyzer import Tarefa, analyze_tasks

utc = timezone.utc
t = Tarefa(1, "Entregar relatório", "alta",
           data_criacao=datetime(2026, 1, 5, 8, tzinfo=utc),
           prazo=datetime(2026, 1, 5, 12, tzinfo=utc),
           status="concluida",
           data_inicio=datetime(2026, 1, 5, 9, tzinfo=utc),
           data_conclusao=datetime(2026, 1, 5, 11, tzinfo=utc))
print(analyze_tasks([t]))
```

## Status
Fase 2: 43 testes, 100% aprovados, 100% de cobertura de `src/task_analyzer.py`.
