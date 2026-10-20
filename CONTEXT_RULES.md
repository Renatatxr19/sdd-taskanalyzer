# CONTEXT_RULES — Governança de IA para o TaskAnalyzer

Contexto **obrigatório** para qualquer assistente de IA que gere código para o TaskAnalyzer.
Autora: Renata Teixeira de Jesus — Bootcamp III (ADS).

## 1. Diretrizes arquiteturais (obrigatórias)
- Python 3.11 ou superior.
- Type hints em todas as funções e métodos.
- Princípio Single Responsibility (SRP) e PEP 8.
- Docstrings no padrão Google Style (módulos, classes, funções e parâmetros).
- Funções pequenas, organizadas e com uma única responsabilidade.
- Exceções específicas (`InvalidDateRangeError`, `InvalidPriorityError`) com mensagens claras.
- Usar o módulo `logging`; nunca `print` para depuração.
- Nomes descritivos, com português ou inglês de forma consistente.
- Separar a entidade `Tarefa`, o motor de cálculo `TaskAnalyzer` e os utilitários de data.

## 2. Proibições explícitas
- Não usar bibliotecas externas não autorizadas (apenas biblioteca padrão; `pytest` nos testes).
- Não alterar, remover ou adaptar os cenários de teste da seção 2.1 da especificação.
- Não modificar a estrutura de pastas da seção 4.1.
- Não persistir dados em arquivos ou bancos de dados nesta fase.
- Não alterar nome ou parâmetros das funções públicas sem autorização explícita.
- Não gerar novas funcionalidades sem os respectivos testes automatizados.
- Não inserir código duplicado ou desnecessário.
- Não assumir comportamentos fora do contrato; em caso de dúvida, **sinalizar** em vez de decidir.

## 3. Regras de interação com IA
- Fornecer o contexto completo (especificação + este arquivo) antes de pedir código.
- Verificar se a IA compreendeu o contrato e os cenários antes de aceitar o código.
- Solicitar explicações sobre qualquer trecho pouco claro.
- Revisar todo código gerado; a responsabilidade técnica é humana.
- Rejeitar e pedir nova versão se alguma regra ou parte do contrato for descumprida.
