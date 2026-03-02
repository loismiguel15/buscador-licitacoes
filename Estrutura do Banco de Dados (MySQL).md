# Estrutura do Banco de Dados (MySQL)

Este documento detalha a estrutura das tabelas do banco de dados MySQL para o Sistema de Busca de Licitações, utilizando sintaxe semelhante ao SQL para descrição.

## 1. Tabela `clientes`

Armazena informações sobre as empresas ou entidades que são clientes do sistema.

```sql
CREATE TABLE clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome_empresa VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18) UNIQUE, -- Formato XX.XXX.XXX/XXXX-XX
    email_contato VARCHAR(255) NOT NULL,
    telefone_contato VARCHAR(20),
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE
);
```

*   **Índices:** Chave primária em `id`, índice único em `cnpj`.

## 2. Tabela `usuarios`

Armazena informações sobre os usuários individuais associados a um cliente.

```sql
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,
    nome_completo VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL, -- Armazenar hash da senha
    tipo ENUM('master', 'comum') NOT NULL DEFAULT 'comum',
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_login TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
);
```

*   **Índices:** Chave primária em `id`, índice único em `email`, chave estrangeira em `cliente_id`.
*   **Relacionamento:** Muitos usuários pertencem a um cliente (`usuarios.cliente_id` -> `clientes.id`).

## 3. Tabela `licitacoes`

Armazena os detalhes das licitações coletadas dos Diários Oficiais e do PNCP.

```sql
CREATE TABLE licitacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    numero_processo VARCHAR(100), -- Pode variar em formato
    identificador_unico_pncp VARCHAR(100) UNIQUE, -- ID específico do PNCP, se aplicável
    orgao_licitante VARCHAR(500) NOT NULL,
    modalidade VARCHAR(100) NOT NULL, -- Ex: Pregão Eletrônico, Concorrência, etc.
    objeto TEXT NOT NULL, -- Descrição do objeto da licitação
    data_publicacao DATE,
    data_abertura_propostas DATETIME,
    localidade_uf CHAR(2), -- Estado (UF)
    localidade_municipio VARCHAR(255), -- Município
    fonte_dados VARCHAR(255) NOT NULL, -- Ex: 'DO União 2024-04-30', 'PNCP', 'DO SP 2024-04-29'
    link_fonte VARCHAR(2048), -- URL para o edital ou publicação original
    texto_integral_aviso LONGTEXT, -- Texto completo do aviso/edital, se coletado
    valor_estimado DECIMAL(15, 2), -- Valor estimado, se disponível
    situacao VARCHAR(50) DEFAULT 'Aberta', -- Ex: Aberta, Em Andamento, Suspensa, Revogada, Concluída, Fracassada, Deserta
    data_coleta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

*   **Índices:**
    *   Chave primária em `id`.
    *   Índice em `numero_processo`.
    *   Índice único em `identificador_unico_pncp` (permite nulos, pois nem toda licitação virá do PNCP).
    *   Índice em `orgao_licitante`.
    *   Índice em `modalidade`.
    *   Índice em `data_publicacao`.
    *   Índice em `data_abertura_propostas`.
    *   Índice em `localidade_uf`.
    *   Índice em `localidade_municipio`.
    *   Índice em `situacao`.
    *   Índice FULLTEXT em `objeto` para otimizar buscas por palavra-chave.
    *   Índice FULLTEXT em `texto_integral_aviso` (se a busca neste campo for necessária).

## 4. Considerações Adicionais

*   **Modalidades:** A coluna `modalidade` na tabela `licitacoes` é um `VARCHAR`. Uma alternativa seria criar uma tabela `modalidades` separada e usar uma chave estrangeira, caso as modalidades sejam estritamente definidas e fixas.
*   **Fontes:** A coluna `fonte_dados` pode ser padronizada para facilitar a identificação da origem.
*   **Otimização:** Índices adicionais podem ser necessários dependendo dos padrões de consulta mais frequentes.
*   **Web Scraping:** A estrutura da tabela `licitacoes` pode precisar de ajustes conforme os dados que for possível extrair de forma consistente das diferentes fontes (DOs e PNCP).

