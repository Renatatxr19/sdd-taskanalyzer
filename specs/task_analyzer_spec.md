# Especificação SDD — TaskAnalyzer

Autora: Renata Teixeira de Jesus — ADS, Turma A — Bootcamp III

## 1. Visão geral e contrato de negócio
### 1.1 Propósito
Módulo que recebe uma lista de tarefas de um usuário ou equipe e gera métricas de desempenho
para identificar gargalos, acompanhar prazos e melhorar o fluxo de trabalho. Calcula:
- tempo médio de conclusão (geral e por prioridade);
- taxa de atraso das tarefas concluídas após o prazo;
- quantidade, tempo médio e taxa de atraso por prioridade (baixa, média, alta);
- total de tarefas analisadas e distribuição por status.

### 1.2 Contrato executável de interface
#### 1.2.1 Entradas — Tarefa
| Campo | Tipo | Obrigatório | Descrição / restrições |
|---|---|---|---|
| id_tarefa | int | Sim | Identificador único (> 0); não se repete na coleção |
| titulo | str | Sim | Não pode ser vazio |
| prioridade | str (enum) | Sim | "baixa", "media", "alta" |
| data_criacao | datetime | Sim | UTC (ISO 8601) |
| data_inicio | datetime | Não | Nula se a tarefa ainda não iniciou |
| data_conclusao | datetime | Não | Obrigatória apenas se status = "concluida" |
| prazo | datetime | Sim | Limite para conclusão |
| status | str (enum) | Sim | "concluida", "pendente", "cancelada" |

#### 1.2.2 Saídas — Relatório de métricas
| Campo | Tipo | Descrição |
|---|---|---|
| tempo_medio_conclusao_min | float | Média em minutos, só tarefas "concluida" com datas válidas |
| taxa_atraso_percentual | float | % (0–100) de concluídas com data_conclusao > prazo |
| quantidade_total_tarefas | int | Total recebido, independente do status |
| indicadores_por_prioridade | dict[str, dict] | Por prioridade: quantidade, tempo médio e taxa de atraso |

#### 1.2.3 Regras de negócio
1. Só concluídas com `data_inicio` e `data_conclusao` válidas entram no tempo médio.
2. Tempo de conclusão = `data_conclusao - data_inicio`, em minutos.
3. Atraso: concluídas com `data_conclusao > prazo`.
4. Pendentes/canceladas contam no total, mas não nos cálculos de tempo e atraso.
5. Quantidade por prioridade considera todas as tarefas, qualquer status.
6. Taxa de atraso por prioridade considera apenas as concluídas do grupo.
7. Toda tarefa deve ter prioridade válida.
8. Datas em UTC; outros fusos são convertidos antes do processamento.
9. Médias e percentuais arredondados a 2 casas decimais.
10. Sem tarefas concluídas: `tempo_medio_conclusao_min` e `taxa_atraso_percentual` = 0.0.
11. Datas inconsistentes (conclusão < início ou início < criação) geram exceção de validação.

## 2. Cenários de aceite (Dado–Quando–Então)
- **Cenário 1 — Sucesso:** dado um conjunto válido com concluídas, pendentes e canceladas, quando o
  TaskAnalyzer é executado, então retorna tempo médio, taxa de atraso e indicadores por prioridade
  conforme a seção 1.2.3.
- **Cenário 2 — Exceção (datas inválidas):** dado ao menos uma tarefa com conclusão < início ou
  início < criação, então lança `InvalidDateRangeError` informando `id_tarefa` e motivo.
- **Cenário 3 — Borda (sem concluídas):** dado lista vazia ou sem concluídas, então tempo médio e
  taxa de atraso = 0.0, sem `ZeroDivisionError`, registrando aviso em log.
- **Cenário 4 — Borda (prioridade inválida):** dado prioridade fora do enum, então lança
  `InvalidPriorityError`.
- **Cenário 5 — Borda (pendente sem conclusão):** dado status "pendente" e `data_conclusao` nula,
  então conta em `quantidade_total_tarefas`, mas fica fora dos cálculos de tempo e atraso.

## 3. Planejamento do Test Harness
Fixtures reutilizáveis, `pytest.mark.parametrize`, `pytest.raises`, cobertura mínima de 90% em
`task_analyzer.py`. `tests/test_harness.py` é o critério de homologação do código gerado por IA.

## 4. Premissas registradas na implementação (Fase 2)
Pontos que o contrato não define explicitamente e foram resolvidos de forma conservadora:
- Datetime sem fuso é interpretado como UTC.
- `TaskValidationError` é a classe base das exceções específicas (exigida pelo enunciado da Fase 2).
- Concluída sem `data_conclusao` → `TaskValidationError` (regra 1.2.1).
- Concluída sem `data_inicio`: entra na taxa de atraso, mas não no tempo médio.
- `data_conclusao < data_criacao` também é rejeitada (coerência cronológica).
- Saída inclui a chave extra `distribuicao_por_status` (prevista no propósito 1.1).
