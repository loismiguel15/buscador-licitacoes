# Projeto da Arquitetura do Sistema de Busca de Licitações

## 1. Introdução

Este documento descreve a arquitetura proposta para o sistema de busca de licitações, baseado nos requisitos definidos anteriormente. O sistema será uma aplicação web construída com Flask, projetada para coletar, armazenar e fornecer acesso a dados de licitações dos Diários Oficiais (DO) e do Portal Nacional de Contratações Públicas (PNCP).

## 2. Visão Geral da Arquitetura

A arquitetura será baseada em um modelo de aplicação web monolítica com componentes bem definidos, utilizando o framework Flask em Python. A separação de responsabilidades será mantida através de módulos específicos para coleta de dados, processamento, acesso ao banco de dados, lógica de negócios (API) e interface do usuário.

**Componentes Principais:**

1.  **Coletores de Dados:** Módulos responsáveis por buscar dados das fontes (DOs e PNCP).
2.  **Processador de Dados:** Componente para limpar, normalizar e estruturar os dados coletados.
3.  **Banco de Dados:** Armazenamento persistente para licitações, clientes e usuários (MySQL).
4.  **Backend (API Flask):** Núcleo da aplicação, expondo endpoints para o frontend e gerenciando a lógica de negócios.
5.  **Frontend (Interface Web):** Interface com o usuário, renderizada pelo Flask usando templates (Jinja2).

## 3. Detalhamento dos Componentes

### 3.1. Coletores de Dados

*   **Responsabilidade:** Obter dados brutos de licitações dos Diários Oficiais e do PNCP.
*   **Implementação:** Scripts Python independentes ou módulos dentro da aplicação Flask.
    *   **Diários Oficiais:** Provavelmente exigirá web scraping, utilizando bibliotecas como `requests` e `BeautifulSoup4`. A complexidade varia conforme a estrutura de cada Diário Oficial.
    *   **PNCP:** Verificar a existência de uma API oficial. Caso contrário, utilizar web scraping.
*   **Execução:** Poderão ser executados periodicamente (ex: tarefas agendadas no servidor) para manter a base de dados atualizada.

### 3.2. Processador de Dados

*   **Responsabilidade:** Receber os dados brutos dos coletores, realizar a limpeza (remoção de HTML, caracteres inválidos), normalização (formatos de data, valores), extração de informações relevantes (órgão, objeto, modalidade, datas, número do processo) e estruturação para inserção no banco de dados.
*   **Implementação:** Funções ou classes Python dedicadas.

### 3.3. Banco de Dados

*   **Tecnologia:** MySQL, conforme sugerido pelo template Flask e adequado para dados relacionais.
*   **Estrutura:** Conterá tabelas para:
    *   `licitacoes`: Armazenar detalhes de cada licitação (ID, número, órgão, objeto, modalidade, datas, fonte, link/texto original, etc.).
    *   `clientes`: Informações sobre as empresas/clientes que utilizam o sistema.
    *   `usuarios`: Dados dos usuários (ID, ID do cliente, nome, email, hash da senha, tipo - master/comum).
*   **Acesso:** Realizado através do ORM SQLAlchemy, gerenciado pelo Flask.

### 3.4. Backend (API Flask)

*   **Framework:** Flask.
*   **Responsabilidades:**
    *   **Autenticação e Autorização:** Gerenciar login, registro, sessões de usuário e controle de acesso baseado nos papéis (master/comum).
    *   **Endpoints da API:** Expor rotas (URLs) para:
        *   Busca de licitações (com filtros por palavra-chave, modalidade, etc.).
        *   Visualização de detalhes de uma licitação.
        *   Gerenciamento de contas de clientes e usuários (acessível apenas por usuários master).
    *   **Lógica de Negócios:** Implementar as regras de validação, busca no banco de dados, e formatação dos dados para resposta.
*   **Estrutura:** Utilizar Blueprints do Flask para organizar as rotas por funcionalidade (ex: `auth`, `licitacoes`, `admin`).

### 3.5. Frontend (Interface Web)

*   **Tecnologia:** HTML, CSS, JavaScript.
*   **Renderização:** Utilizar o motor de templates Jinja2, integrado ao Flask, para gerar as páginas HTML dinamicamente.
*   **Funcionalidades:**
    *   Formulários de login e registro.
    *   Interface de busca com campos para filtros.
    *   Exibição dos resultados da busca em tabela ou lista.
    *   Página de detalhes da licitação.
    *   Painel de administração para usuários master (gerenciamento de usuários comuns).
    *   Design responsivo para boa visualização em diferentes tamanhos de tela.

## 4. Fluxo de Dados

1.  **Coleta:** Coletores buscam dados nas fontes (DO/PNCP).
2.  **Processamento:** Dados brutos são limpos e estruturados pelo Processador.
3.  **Armazenamento:** Dados processados são inseridos/atualizados no Banco de Dados MySQL via SQLAlchemy.
4.  **Requisição do Usuário:** Usuário acessa o Frontend via navegador.
5.  **Interação:** Frontend envia requisições (ex: busca) para o Backend Flask.
6.  **Processamento Backend:** Flask recebe a requisição, aplica a lógica de negócios (autenticação, busca no BD).
7.  **Resposta:** Flask retorna os dados formatados para o Frontend.
8.  **Exibição:** Frontend renderiza a página com os dados recebidos.

## 5. Tecnologias Propostas

*   **Linguagem:** Python 3
*   **Framework Backend:** Flask
*   **Banco de Dados:** MySQL
*   **ORM:** SQLAlchemy
*   **Web Scraping:** Requests, BeautifulSoup4
*   **Frontend:** HTML, CSS, JavaScript, Jinja2
*   **Servidor Web (para deploy):** Gunicorn/Waitress (gerenciados pela plataforma de deploy)

## 6. Próximos Passos

*   Definir a estrutura detalhada do banco de dados (próxima etapa do plano).
*   Criar protótipos da interface do usuário.
*   Iniciar a implementação dos componentes, começando pelo backend e estrutura do banco de dados.

