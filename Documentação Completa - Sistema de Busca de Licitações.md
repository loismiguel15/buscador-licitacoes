# Documentação Completa - Sistema de Busca de Licitações

## 1. Introdução

Este documento fornece uma visão completa do Sistema de Busca de Licitações, desenvolvido como uma alternativa focada em Diários Oficiais (DO) e no Portal Nacional de Contratações Públicas (PNCP), inspirado na funcionalidade do conlicitacao.com.br. O sistema é uma aplicação web Flask que permite a busca, visualização e gerenciamento de informações sobre licitações públicas, com controle de acesso por clientes e usuários.

## 2. Requisitos do Sistema (Resumo)

*   **Fontes de Dados:** Diários Oficiais (União, Estados, Municípios - a definir) e PNCP.
*   **Funcionalidades:**
    *   Busca por palavra-chave no objeto, modalidade, órgão, UF.
    *   Visualização de detalhes da licitação.
    *   Gerenciamento de Clientes e Usuários (Master e Comum).
    *   Interface Web responsiva.
*   **Não Funcionais:** Desempenho, escalabilidade, segurança, atualização de dados, manutenibilidade.

*(Para detalhes completos, consulte o arquivo `requisitos_sistema.md`)*

## 3. Arquitetura do Sistema (Resumo)

*   **Modelo:** Aplicação web monolítica com Flask.
*   **Componentes:**
    1.  **Coletores de Dados:** Scripts para buscar dados (implementação futura/separada).
    2.  **Processador de Dados:** Limpeza e estruturação dos dados coletados (implementação futura/separada).
    3.  **Banco de Dados:** MySQL com SQLAlchemy para persistência.
    4.  **Backend (API Flask):** Lógica de negócios, autenticação, endpoints RESTful (`/api/auth`, `/api/licitacoes`).
    5.  **Frontend:** HTML/CSS/JS renderizados via Jinja2 (protótipo estático fornecido).
*   **Fluxo:** Coleta -> Processamento -> Armazenamento -> Requisição Frontend -> Processamento Backend -> Resposta -> Exibição Frontend.
*   **Tecnologias:** Python, Flask, MySQL, SQLAlchemy, HTML, CSS, JS, Jinja2.

*(Para detalhes completos, consulte o arquivo `arquitetura_sistema.md`)*

## 4. Estrutura do Banco de Dados (Resumo)

*   **Tecnologia:** MySQL
*   **Tabelas Principais:**
    *   `clientes`: Armazena dados das empresas clientes (id, nome_empresa, cnpj, etc.).
    *   `usuarios`: Armazena dados dos usuários (id, cliente_id, nome, email, senha_hash, tipo - master/comum, etc.). Relaciona-se com `clientes`.
    *   `licitacoes`: Armazena detalhes das licitações (id, numero_processo, orgao_licitante, modalidade, objeto, datas, fonte, link, etc.).
*   **Índices:** Definidos para otimizar buscas comuns (ex: por data, modalidade, órgão, UF, palavra-chave no objeto via FULLTEXT - a configurar no MySQL).

*(Para detalhes completos, consulte o arquivo `estrutura_banco_dados.md`)*

## 5. Instruções de Instalação e Execução

1.  **Pré-requisitos:**
    *   Python 3.11+
    *   Servidor MySQL acessível.
    *   `pip` (gerenciador de pacotes Python).
2.  **Configuração do Ambiente:**
    *   Clone ou copie o diretório do projeto (`buscador_licitacoes`).
    *   Navegue até o diretório raiz do projeto.
    *   Crie e ative um ambiente virtual: `python3 -m venv venv` e `source venv/bin/activate` (Linux/macOS) ou `venv\Scripts\activate` (Windows).
    *   Instale as dependências: `pip install -r requirements.txt`.
3.  **Configuração do Banco de Dados:**
    *   Certifique-se de que o servidor MySQL esteja rodando.
    *   Crie um banco de dados (ex: `licitacoes_db`).
    *   Configure as variáveis de ambiente para conexão com o banco de dados (ou ajuste diretamente em `src/main.py` - não recomendado para produção):
        *   `DB_USERNAME`: Usuário do MySQL (padrão: `root`)
        *   `DB_PASSWORD`: Senha do MySQL (padrão: `password`)
        *   `DB_HOST`: Endereço do servidor MySQL (padrão: `localhost`)
        *   `DB_PORT`: Porta do MySQL (padrão: `3306`)
        *   `DB_NAME`: Nome do banco de dados criado (padrão: `mydb`, **ajuste para o nome criado**).
    *   Verifique se as linhas de configuração do SQLAlchemy em `src/main.py` estão descomentadas.
4.  **Execução:**
    *   No diretório raiz do projeto, execute: `python src/main.py`
    *   A aplicação estará acessível em `http://0.0.0.0:5000` ou `http://localhost:5000`.
    *   O Flask criará automaticamente as tabelas no banco de dados na primeira execução (`db.create_all()`).

## 6. Guia de Uso (Baseado no Protótipo)

1.  **Acesso Inicial:** Acesse a URL base (`/`). Você verá a página inicial com uma busca rápida.
2.  **Cadastro:**
    *   Clique em "Cadastro" na navegação.
    *   Preencha os dados da empresa (Cliente) e do Usuário Master.
    *   Clique em "Criar Conta".
3.  **Login:**
    *   Clique em "Login".
    *   Insira o email e senha do usuário (Master ou Comum).
    *   Clique em "Entrar".
4.  **Busca de Licitações:**
    *   Clique em "Buscar Licitações".
    *   Utilize o formulário de busca avançada para filtrar por palavra-chave, modalidade, órgão ou UF.
    *   Clique em "Buscar". Os resultados serão exibidos em uma tabela paginada.
5.  **Detalhes da Licitação:**
    *   Nos resultados da busca, clique em "Ver Detalhes" para uma licitação específica.
    *   A página exibirá todas as informações disponíveis sobre a licitação.
6.  **Painel Administrativo (Usuário Master):**
    *   Se logado como Master, um link "Painel Admin" aparecerá na navegação.
    *   Neste painel, o usuário Master pode visualizar e adicionar novos usuários comuns associados à sua conta de cliente.
7.  **Logout:** Clique em "Sair" na navegação (quando logado).

## 7. Detalhes Técnicos

*   **Estrutura do Projeto:**
    *   `buscador_licitacoes/`
        *   `venv/`: Ambiente virtual.
        *   `src/`: Código fonte da aplicação.
            *   `models.py`: Definições dos modelos SQLAlchemy (Cliente, Usuario, Licitacao).
            *   `routes/`: Blueprints do Flask.
                *   `auth.py`: Rotas de autenticação (/register, /login, /logout, /status).
                *   `licitacao.py`: Rotas de busca (/buscar, /<id>).
            *   `static/`: Arquivos estáticos do frontend (HTML, CSS, JS - protótipo).
            *   `main.py`: Ponto de entrada da aplicação Flask, configuração e registro de blueprints.
        *   `requirements.txt`: Lista de dependências Python.
*   **Principais Bibliotecas:**
    *   `Flask`: Framework web.
    *   `Flask-SQLAlchemy`: Integração SQLAlchemy com Flask.
    *   `SQLAlchemy`: ORM para interação com o banco de dados.
    *   `PyMySQL`: Driver MySQL para SQLAlchemy.
    *   `Werkzeug`: Utilitários WSGI, incluindo hash de senhas.

## 8. Limitações e Melhorias Futuras

*   **Coleta e Processamento de Dados:** A implementação atual **não inclui** os coletores e processadores de dados. Estes precisam ser desenvolvidos separadamente para popular o banco de dados com licitações dos Diários Oficiais e PNCP (via scraping ou APIs, se disponíveis).
*   **Frontend:** O frontend fornecido é um protótipo estático em HTML. Para uma aplicação funcional, ele precisa ser integrado dinamicamente com o backend Flask (usando Jinja2 ou um framework JS como React/Vue).
*   **Busca:** A busca por palavra-chave é básica (`ILIKE`). Implementar busca Full-Text no MySQL e no SQLAlchemy pode melhorar significativamente a relevância e performance.
*   **Gerenciamento de Usuários:** O painel admin do protótipo permite apenas adicionar usuários. Funcionalidades como editar, desativar/ativar (implementado parcialmente no backend), e resetar senhas precisam ser completadas no backend e frontend.
*   **Validação:** As validações no backend são básicas. Adicionar validações mais robustas (ex: CNPJ completo, complexidade de senha) é recomendado.
*   **Alertas/Notificações:** Implementar um sistema de alertas por email para novas licitações que correspondam a critérios salvos pelos usuários.
*   **Testes:** Adicionar testes unitários e de integração para garantir a robustez do código.
*   **Segurança:** Implementar medidas de segurança adicionais (ex: CSRF protection, rate limiting, HTTPS).
*   **Deploy:** Preparar a aplicação para deploy em produção (ex: usando Gunicorn/Waitress, configuração de servidor web, gerenciamento de variáveis de ambiente).

