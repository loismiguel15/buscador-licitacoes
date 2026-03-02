# Algoritmo de Funcionamento do Sistema de Busca de Licitações
## Explicação Didática

### Introdução

Este documento explica de forma didática como funciona o sistema de busca de licitações, descrevendo o fluxo de dados e operações desde a coleta de informações até a apresentação ao usuário final.

### 1. Visão Geral do Sistema

O sistema funciona como um ciclo contínuo com cinco processos principais:

1. **Coleta de Dados**: Busca informações de licitações em Diários Oficiais e no PNCP
2. **Processamento de Dados**: Organiza e estrutura as informações coletadas
3. **Armazenamento**: Guarda os dados em um banco de dados MySQL
4. **Busca e Visualização**: Permite aos usuários encontrar e visualizar licitações
5. **Gerenciamento de Usuários**: Controla acesso e permissões no sistema

![Diagrama de Fluxo](https://i.ibb.co/tKdnvKS/fluxo-sistema.png)

### 2. Como Funciona a Coleta de Dados

#### 2.1. Coleta Automática Periódica

O sistema executa diariamente (ou conforme configurado) um processo de coleta que:

1. **Acessa as fontes de dados**:
   - Diários Oficiais da União, Estados e Municípios
   - Portal Nacional de Contratações Públicas (PNCP)

2. **Extrai informações relevantes**:
   - Número do processo
   - Órgão licitante
   - Modalidade da licitação
   - Objeto (descrição do que está sendo licitado)
   - Datas de publicação e abertura
   - Localidade
   - Valor estimado
   - Link para o edital completo

**Exemplo prático**: Quando o Ministério da Saúde publica um novo pregão eletrônico no Diário Oficial da União, o sistema detecta essa publicação, extrai as informações e as prepara para processamento.

#### 2.2. Processamento dos Dados Coletados

Após a coleta, o sistema:

1. **Limpa os dados**: Remove tags HTML, formata textos
2. **Estrutura as informações**: Organiza em campos padronizados
3. **Valida os dados**: Garante que informações essenciais estão presentes
4. **Normaliza formatos**: Padroniza datas, valores monetários, etc.

**Exemplo prático**: O texto "PREGÃO ELETRÔNICO Nº 123/2025 - Aquisição de equipamentos hospitalares..." é processado para extrair "Pregão Eletrônico" como modalidade e "Aquisição de equipamentos hospitalares" como objeto.

### 3. Como Funciona o Acesso ao Sistema

#### 3.1. Cadastro de Empresas e Usuários

1. **Cadastro inicial**:
   - Uma empresa se cadastra fornecendo dados como nome, CNPJ e contato
   - Junto com o cadastro da empresa, é criado um usuário Master
   - O usuário Master tem permissões para gerenciar outros usuários

2. **Adição de usuários comuns**:
   - O usuário Master pode adicionar usuários comuns para sua empresa
   - Usuários comuns têm acesso às funcionalidades de busca e visualização

**Exemplo prático**: A empresa "Suprimentos Médicos Ltda" se cadastra no sistema e cria um usuário Master para o gerente. Posteriormente, o gerente adiciona três vendedores como usuários comuns para que possam buscar licitações.

#### 3.2. Autenticação e Controle de Acesso

1. **Login**:
   - Usuário fornece email e senha
   - Sistema verifica credenciais e cria uma sessão
   - Sessão armazena informações como tipo de usuário e empresa

2. **Verificação de permissões**:
   - Cada ação no sistema verifica se o usuário tem permissão
   - Usuários Master podem gerenciar usuários comuns
   - Usuários comuns podem apenas buscar e visualizar licitações

**Exemplo prático**: Quando um usuário comum tenta acessar o painel administrativo, o sistema verifica que ele não tem permissão de "Master" e redireciona para a página de login ou exibe uma mensagem de acesso negado.

### 4. Como Funciona a Busca de Licitações

#### 4.1. Processo de Busca

1. **Formulação da busca**:
   - Usuário preenche um ou mais filtros:
     - Palavra-chave no objeto
     - Modalidade de licitação
     - Órgão licitante
     - Estado (UF)

2. **Execução da busca**:
   - Sistema constrói uma consulta SQL com os filtros informados
   - Banco de dados retorna as licitações que correspondem aos critérios
   - Resultados são paginados para melhor visualização

**Exemplo prático**: Um usuário busca por "equipamentos médicos" como palavra-chave, "Pregão Eletrônico" como modalidade e "SP" como UF. O sistema retorna todas as licitações que atendem a esses três critérios.

#### 4.2. Visualização de Resultados e Detalhes

1. **Lista de resultados**:
   - Exibe informações resumidas de cada licitação
   - Mostra número do processo, órgão, modalidade, objeto resumido, datas

2. **Detalhes da licitação**:
   - Ao clicar em uma licitação específica, o sistema exibe todos os detalhes
   - Inclui o texto integral do aviso, link para o edital original
   - Apresenta informações como valor estimado e situação atual

**Exemplo prático**: Nos resultados da busca, o usuário vê 15 licitações que correspondem aos critérios. Ao clicar em uma delas, o sistema exibe uma página com todos os detalhes daquela licitação específica, incluindo o texto completo do aviso publicado.

### 5. Como Funciona o Gerenciamento de Usuários

#### 5.1. Funções do Usuário Master

1. **Visualização de usuários**:
   - Lista todos os usuários associados à sua empresa
   - Mostra informações como nome, email, tipo e status

2. **Adição de novos usuários**:
   - Cria usuários comuns fornecendo nome, email e senha inicial
   - Novos usuários são vinculados à mesma empresa

3. **Gerenciamento de status**:
   - Ativa ou desativa usuários conforme necessário
   - Usuários desativados não podem fazer login

**Exemplo prático**: O gerente da "Suprimentos Médicos Ltda" acessa o painel administrativo, visualiza os três vendedores cadastrados e percebe que um deles saiu da empresa. Ele então desativa esse usuário para impedir futuros acessos ao sistema.

### 6. Fluxo Completo de Uso do Sistema

Para ilustrar o funcionamento completo, vamos acompanhar um exemplo de uso do sistema do início ao fim:

1. **Coleta automática noturna**:
   - Durante a madrugada, o sistema coleta novos avisos de licitação
   - Processa e armazena os dados no banco de dados

2. **Acesso do usuário pela manhã**:
   - Um vendedor da "Suprimentos Médicos Ltda" faz login no sistema
   - Acessa a página de busca avançada

3. **Realização da busca**:
   - Busca por "equipamentos hospitalares" como palavra-chave
   - Filtra por "Pregão Eletrônico" como modalidade
   - Seleciona "SP" e "RJ" como estados de interesse

4. **Análise dos resultados**:
   - Sistema exibe 28 licitações correspondentes aos critérios
   - Vendedor navega pelas páginas de resultados
   - Identifica 5 licitações potencialmente interessantes

5. **Verificação de detalhes**:
   - Para cada licitação de interesse, o vendedor acessa a página de detalhes
   - Analisa informações completas, incluindo prazos e valores
   - Acessa o edital original através do link fornecido

6. **Tomada de decisão**:
   - Com base nas informações obtidas, o vendedor decide em quais licitações a empresa irá participar
   - Prepara a documentação necessária para cada processo

Este fluxo se repete diariamente, permitindo que a empresa identifique oportunidades de negócio com o governo de forma eficiente e organizada.

### 7. Considerações Técnicas Simplificadas

- **Banco de dados**: Todas as informações são armazenadas em um banco MySQL com tabelas para licitações, clientes e usuários
- **Segurança**: Senhas são armazenadas com criptografia e o acesso é controlado por sessões
- **Interface**: Páginas web responsivas que funcionam em computadores e dispositivos móveis
- **Atualizações**: Dados são atualizados regularmente através do processo automático de coleta

### Conclusão

O sistema de busca de licitações funciona como uma ponte entre as publicações oficiais do governo e as empresas interessadas em fornecer produtos ou serviços. Através de processos automatizados de coleta, processamento e armazenamento, combinados com uma interface intuitiva de busca e visualização, o sistema permite que usuários encontrem oportunidades de negócio de forma rápida e eficiente, economizando o tempo que seria gasto monitorando manualmente múltiplas fontes de informação.
