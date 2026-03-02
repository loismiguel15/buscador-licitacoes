# Detalhamento do Algoritmo de Funcionamento do Sistema de Busca de Licitações

## 1. Detalhamento do Fluxo de Coleta e Processamento de Dados

### 1.1. Coleta de Dados dos Diários Oficiais
```
FUNÇÃO coletor_de_dados(fonte="diario_oficial")
  INICIALIZAR lista_dados_coletados = []
  
  # Identificação das fontes específicas
  SE fonte = "diario_oficial_uniao" ENTÃO
    url = "https://www.in.gov.br/..."
  SENÃO SE fonte = "diario_oficial_estado_sp" ENTÃO
    url = "https://www.imprensaoficial.com.br/..."
  # ... outros diários oficiais ...
  FIM-SE
  
  # Processo de web scraping
  página_html = HTTP_GET(url)
  PARA CADA seção_licitações EM página_html
    PARA CADA item_licitação EM seção_licitações
      dados_brutos = EXTRAIR_DADOS(item_licitação)
      ADICIONAR dados_brutos À lista_dados_coletados
    FIM-PARA
  FIM-PARA
  
  RETORNAR lista_dados_coletados
FIM-FUNÇÃO
```

### 1.2. Coleta de Dados do PNCP
```
FUNÇÃO coletor_de_dados(fonte="pncp")
  INICIALIZAR lista_dados_coletados = []
  
  # Verificar se existe API oficial
  SE existe_api_pncp ENTÃO
    # Usar API oficial
    resposta_api = HTTP_GET("https://pncp.gov.br/api/licitacoes", 
                          parâmetros={data_inicio: data_última_coleta})
    PARA CADA licitação EM resposta_api.dados
      ADICIONAR licitação À lista_dados_coletados
    FIM-PARA
  SENÃO
    # Usar web scraping como alternativa
    página_html = HTTP_GET("https://pncp.gov.br/...")
    # Processo similar ao dos Diários Oficiais
    # ...
  FIM-SE
  
  RETORNAR lista_dados_coletados
FIM-FUNÇÃO
```

### 1.3. Processamento dos Dados Coletados
```
FUNÇÃO processador_de_dados(dado_bruto)
  INICIALIZAR dado_processado = {}
  
  # Limpeza de dados
  texto_limpo = REMOVER_HTML_TAGS(dado_bruto.texto)
  texto_limpo = REMOVER_CARACTERES_ESPECIAIS(texto_limpo)
  
  # Extração de informações estruturadas
  dado_processado.numero_processo = EXTRAIR_REGEX(texto_limpo, padrão_numero_processo)
  dado_processado.orgao_licitante = EXTRAIR_REGEX(texto_limpo, padrão_orgao)
  dado_processado.modalidade = IDENTIFICAR_MODALIDADE(texto_limpo)
  dado_processado.objeto = EXTRAIR_OBJETO(texto_limpo)
  dado_processado.data_publicacao = CONVERTER_DATA(dado_bruto.data_publicacao)
  dado_processado.data_abertura_propostas = EXTRAIR_E_CONVERTER_DATA(texto_limpo, padrão_data_abertura)
  
  # Extração de localidade
  localidade = EXTRAIR_LOCALIDADE(texto_limpo)
  dado_processado.localidade_uf = localidade.uf
  dado_processado.localidade_municipio = localidade.municipio
  
  # Metadados
  dado_processado.fonte_dados = dado_bruto.fonte
  dado_processado.link_fonte = dado_bruto.url
  dado_processado.texto_integral_aviso = texto_limpo
  dado_processado.valor_estimado = EXTRAIR_VALOR(texto_limpo)
  dado_processado.situacao = "Aberta" # Estado inicial padrão
  
  # Validação básica
  SE NÃO dado_processado.numero_processo OU NÃO dado_processado.orgao_licitante OU NÃO dado_processado.objeto ENTÃO
    RETORNAR null # Dado inválido, faltam informações essenciais
  FIM-SE
  
  RETORNAR dado_processado
FIM-FUNÇÃO
```

## 2. Detalhamento do Fluxo de Autenticação e Autorização

### 2.1. Registro de Cliente e Usuário Master
```
FUNÇÃO registrar_cliente_e_usuario(dados_requisição)
  # Validação de dados do cliente
  SE NÃO é_válido(dados_requisição.nome_empresa) OU 
     NÃO é_válido_cnpj(dados_requisição.cnpj) OU 
     NÃO é_válido_email(dados_requisição.email_contato) ENTÃO
    RETORNAR {erro: "Dados do cliente inválidos", status: 400}
  FIM-SE
  
  # Validação de dados do usuário master
  SE NÃO é_válido(dados_requisição.nome_master) OU 
     NÃO é_válido_email(dados_requisição.email_master) OU 
     NÃO é_válido_senha(dados_requisição.senha_master) OU
     dados_requisição.senha_master != dados_requisição.confirma_senha_master ENTÃO
    RETORNAR {erro: "Dados do usuário master inválidos", status: 400}
  FIM-SE
  
  # Verificar duplicidade
  SE existe_cliente_com_cnpj(dados_requisição.cnpj) ENTÃO
    RETORNAR {erro: "CNPJ já cadastrado", status: 409}
  FIM-SE
  
  SE existe_usuario_com_email(dados_requisição.email_master) ENTÃO
    RETORNAR {erro: "Email já cadastrado", status: 409}
  FIM-SE
  
  # Criar registros no banco de dados
  INICIAR_TRANSAÇÃO
    novo_cliente = CRIAR_CLIENTE(
      nome_empresa: dados_requisição.nome_empresa,
      cnpj: dados_requisição.cnpj,
      email_contato: dados_requisição.email_contato,
      telefone_contato: dados_requisição.telefone_contato,
      data_cadastro: DATA_ATUAL(),
      ativo: true
    )
    
    novo_usuario = CRIAR_USUARIO(
      cliente_id: novo_cliente.id,
      nome_completo: dados_requisição.nome_master,
      email: dados_requisição.email_master,
      senha_hash: HASH_SENHA(dados_requisição.senha_master),
      tipo: "master",
      data_criacao: DATA_ATUAL(),
      ativo: true
    )
  CONFIRMAR_TRANSAÇÃO
  
  RETORNAR {mensagem: "Conta criada com sucesso", status: 201}
FIM-FUNÇÃO
```

### 2.2. Login de Usuário
```
FUNÇÃO login_usuario(email, senha)
  # Buscar usuário pelo email
  usuario = BUSCAR_USUARIO_POR_EMAIL(email)
  
  # Verificar se usuário existe e está ativo
  SE NÃO usuario OU NÃO usuario.ativo ENTÃO
    RETORNAR {erro: "Credenciais inválidas ou usuário inativo", status: 401}
  FIM-SE
  
  # Verificar senha
  SE NÃO VERIFICAR_HASH_SENHA(senha, usuario.senha_hash) ENTÃO
    RETORNAR {erro: "Credenciais inválidas ou usuário inativo", status: 401}
  FIM-SE
  
  # Atualizar último login
  ATUALIZAR_ULTIMO_LOGIN(usuario.id, DATA_ATUAL())
  
  # Criar sessão
  sessão = CRIAR_SESSÃO(
    user_id: usuario.id,
    user_email: usuario.email,
    user_tipo: usuario.tipo,
    cliente_id: usuario.cliente_id
  )
  
  RETORNAR {
    mensagem: "Login bem-sucedido",
    usuario: {
      id: usuario.id,
      email: usuario.email,
      nome: usuario.nome_completo,
      tipo: usuario.tipo
    },
    status: 200
  }
FIM-FUNÇÃO
```

### 2.3. Verificação de Autenticação em Requisições
```
FUNÇÃO verificar_autenticação(requisição, nível_acesso_requerido=null)
  # Verificar se existe sessão ativa
  SE NÃO requisição.sessão OU NÃO requisição.sessão.user_id ENTÃO
    RETORNAR {autenticado: false, erro: "Não autenticado", status: 401}
  FIM-SE
  
  # Se for necessário verificar nível de acesso específico
  SE nível_acesso_requerido = "master" E requisição.sessão.user_tipo != "master" ENTÃO
    RETORNAR {autenticado: true, autorizado: false, erro: "Acesso negado", status: 403}
  FIM-SE
  
  RETORNAR {autenticado: true, autorizado: true, user_id: requisição.sessão.user_id, status: 200}
FIM-FUNÇÃO
```

## 3. Detalhamento do Fluxo de Busca e Visualização de Licitações

### 3.1. Busca de Licitações com Filtros
```
FUNÇÃO buscar_licitacoes(parâmetros)
  # Extrair parâmetros de busca
  palavra_chave = parâmetros.palavra_chave
  modalidade = parâmetros.modalidade
  orgao = parâmetros.orgao
  uf = parâmetros.uf
  pagina = parâmetros.pagina OU 1
  itens_por_pagina = parâmetros.itens_por_pagina OU 10
  
  # Construir consulta base
  consulta = "SELECT * FROM licitacoes WHERE 1=1"
  
  # Adicionar filtros se fornecidos
  SE palavra_chave ENTÃO
    consulta += " AND objeto ILIKE '%" + palavra_chave + "%'"
  FIM-SE
  
  SE modalidade ENTÃO
    consulta += " AND modalidade ILIKE '%" + modalidade + "%'"
  FIM-SE
  
  SE orgao ENTÃO
    consulta += " AND orgao_licitante ILIKE '%" + orgao + "%'"
  FIM-SE
  
  SE uf ENTÃO
    consulta += " AND localidade_uf ILIKE '%" + uf + "%'"
  FIM-SE
  
  # Ordenação
  consulta += " ORDER BY data_publicacao DESC NULLS LAST, id DESC"
  
  # Executar consulta com paginação
  offset = (pagina - 1) * itens_por_pagina
  consulta += " LIMIT " + itens_por_pagina + " OFFSET " + offset
  
  # Executar consulta
  resultados = EXECUTAR_SQL(consulta)
  
  # Contar total para paginação
  consulta_contagem = SUBSTITUIR(consulta, "SELECT *", "SELECT COUNT(*)")
  consulta_contagem = REMOVER_SUBSTRING(consulta_contagem, "ORDER BY data_publicacao DESC NULLS LAST, id DESC")
  consulta_contagem = REMOVER_SUBSTRING(consulta_contagem, "LIMIT " + itens_por_pagina + " OFFSET " + offset)
  
  total_items = EXECUTAR_SQL(consulta_contagem)[0].count
  total_paginas = TETO(total_items / itens_por_pagina)
  
  # Formatar resultados
  resultados_formatados = []
  PARA CADA licitacao EM resultados
    resultado_formatado = {
      id: licitacao.id,
      numero_processo: licitacao.numero_processo,
      orgao_licitante: licitacao.orgao_licitante,
      modalidade: licitacao.modalidade,
      objeto: licitacao.objeto,
      data_publicacao: FORMATAR_DATA(licitacao.data_publicacao),
      data_abertura_propostas: FORMATAR_DATA_HORA(licitacao.data_abertura_propostas),
      localidade_uf: licitacao.localidade_uf,
      localidade_municipio: licitacao.localidade_municipio,
      fonte_dados: licitacao.fonte_dados,
      link_fonte: licitacao.link_fonte,
      valor_estimado: licitacao.valor_estimado,
      situacao: licitacao.situacao
    }
    ADICIONAR resultado_formatado À resultados_formatados
  FIM-PARA
  
  RETORNAR {
    resultados: resultados_formatados,
    paginacao: {
      pagina: pagina,
      itens_por_pagina: itens_por_pagina,
      total_items: total_items,
      total_paginas: total_paginas
    },
    status: 200
  }
FIM-FUNÇÃO
```

### 3.2. Visualização de Detalhes da Licitação
```
FUNÇÃO obter_detalhes_licitacao(licitacao_id)
  # Buscar licitação pelo ID
  licitacao = BUSCAR_LICITACAO_POR_ID(licitacao_id)
  
  # Verificar se a licitação existe
  SE NÃO licitacao ENTÃO
    RETORNAR {erro: "Licitação não encontrada", status: 404}
  FIM-SE
  
  # Formatar resultado incluindo o texto integral
  resultado = {
    id: licitacao.id,
    numero_processo: licitacao.numero_processo,
    identificador_unico_pncp: licitacao.identificador_unico_pncp,
    orgao_licitante: licitacao.orgao_licitante,
    modalidade: licitacao.modalidade,
    objeto: licitacao.objeto,
    data_publicacao: FORMATAR_DATA(licitacao.data_publicacao),
    data_abertura_propostas: FORMATAR_DATA_HORA(licitacao.data_abertura_propostas),
    localidade_uf: licitacao.localidade_uf,
    localidade_municipio: licitacao.localidade_municipio,
    fonte_dados: licitacao.fonte_dados,
    link_fonte: licitacao.link_fonte,
    texto_integral_aviso: licitacao.texto_integral_aviso,
    valor_estimado: licitacao.valor_estimado,
    situacao: licitacao.situacao,
    data_coleta: FORMATAR_DATA_HORA(licitacao.data_coleta),
    data_ultima_atualizacao: FORMATAR_DATA_HORA(licitacao.data_ultima_atualizacao)
  }
  
  RETORNAR {licitacao: resultado, status: 200}
FIM-FUNÇÃO
```

## 4. Detalhamento do Fluxo de Gerenciamento de Usuários

### 4.1. Listagem de Usuários de um Cliente
```
FUNÇÃO listar_usuarios(cliente_id, sessao_usuario)
  # Verificar permissões
  verificacao = verificar_autenticação(sessao_usuario, "master")
  SE NÃO verificacao.autorizado ENTÃO
    RETORNAR {erro: verificacao.erro, status: verificacao.status}
  FIM-SE
  
  # Verificar se o usuário pertence ao cliente solicitado
  SE sessao_usuario.cliente_id != cliente_id ENTÃO
    RETORNAR {erro: "Acesso negado", status: 403}
  FIM-SE
  
  # Buscar usuários do cliente
  usuarios = BUSCAR_USUARIOS_POR_CLIENTE_ID(cliente_id)
  
  # Formatar resultados (sem incluir senha_hash por segurança)
  usuarios_formatados = []
  PARA CADA usuario EM usuarios
    usuario_formatado = {
      id: usuario.id,
      nome_completo: usuario.nome_completo,
      email: usuario.email,
      tipo: usuario.tipo,
      data_criacao: FORMATAR_DATA_HORA(usuario.data_criacao),
      ultimo_login: FORMATAR_DATA_HORA(usuario.ultimo_login),
      ativo: usuario.ativo
    }
    ADICIONAR usuario_formatado À usuarios_formatados
  FIM-PARA
  
  RETORNAR {usuarios: usuarios_formatados, status: 200}
FIM-FUNÇÃO
```

### 4.2. Adição de Novo Usuário Comum
```
FUNÇÃO adicionar_usuario_comum(dados_requisição, sessao_usuario)
  # Verificar permissões
  verificacao = verificar_autenticação(sessao_usuario, "master")
  SE NÃO verificacao.autorizado ENTÃO
    RETORNAR {erro: verificacao.erro, status: verificacao.status}
  FIM-SE
  
  # Validação de dados
  SE NÃO é_válido(dados_requisição.nome) OU 
     NÃO é_válido_email(dados_requisição.email) OU 
     NÃO é_válido_senha(dados_requisição.senha) ENTÃO
    RETORNAR {erro: "Dados inválidos", status: 400}
  FIM-SE
  
  # Verificar duplicidade de email
  SE existe_usuario_com_email(dados_requisição.email) ENTÃO
    RETORNAR {erro: "Email já cadastrado", status: 409}
  FIM-SE
  
  # Criar usuário comum
  novo_usuario = CRIAR_USUARIO(
    cliente_id: sessao_usuario.cliente_id,
    nome_completo: dados_requisição.nome,
    email: dados_requisição.email,
    senha_hash: HASH_SENHA(dados_requisição.senha),
    tipo: "comum",
    data_criacao: DATA_ATUAL(),
    ativo: true
  )
  
  RETORNAR {
    mensagem: "Usuário adicionado com sucesso",
    usuario: {
      id: novo_usuario.id,
      nome_completo: novo_usuario.nome_completo,
      email: novo_usuario.email,
      tipo: novo_usuario.tipo,
      ativo: novo_usuario.ativo
    },
    status: 201
  }
FIM-FUNÇÃO
```

### 4.3. Alteração de Status de Usuário
```
FUNÇÃO alterar_status_usuario(usuario_id, novo_status, sessao_usuario)
  # Verificar permissões
  verificacao = verificar_autenticação(sessao_usuario, "master")
  SE NÃO verificacao.autorizado ENTÃO
    RETORNAR {erro: verificacao.erro, status: verificacao.status}
  FIM-SE
  
  # Buscar usuário
  usuario = BUSCAR_USUARIO_POR_ID(usuario_id)
  
  # Verificar se usuário existe
  SE NÃO usuario ENTÃO
    RETORNAR {erro: "Usuário não encontrado", status: 404}
  FIM-SE
  
  # Verificar se o usuário pertence ao mesmo cliente do usuário master
  SE usuario.cliente_id != sessao_usuario.cliente_id ENTÃO
    RETORNAR {erro: "Acesso negado", status: 403}
  FIM-SE
  
  # Não permitir desativar a si mesmo
  SE usuario.id = sessao_usuario.user_id E novo_status = false ENTÃO
    RETORNAR {erro: "Não é possível desativar seu próprio usuário", status: 400}
  FIM-SE
  
  # Atualizar status
  ATUALIZAR_STATUS_USUARIO(usuario_id, novo_status)
  
  RETORNAR {
    mensagem: "Status do usuário atualizado com sucesso",
    usuario_id: usuario_id,
    novo_status: novo_status,
    status: 200
  }
FIM-FUNÇÃO
```

## 5. Detalhamento do Fluxo de Renderização da Interface

### 5.1. Renderização da Página Inicial
```
FUNÇÃO renderizar_pagina_inicial()
  # Verificar se há sessão ativa (opcional)
  sessao = OBTER_SESSAO_ATUAL()
  
  # Renderizar template com contexto apropriado
  RETORNAR RENDERIZAR_TEMPLATE("index.html", {
    usuario_logado: sessao ? {
      nome: sessao.nome,
      tipo: sessao.tipo
    } : null
  })
FIM-FUNÇÃO
```

### 5.2. Renderização da Página de Resultados de Busca
```
FUNÇÃO renderizar_pagina_resultados(parâmetros_busca)
  # Executar busca de licitações
  resultado_busca = buscar_licitacoes(parâmetros_busca)
  
  # Verificar se há sessão ativa (opcional)
  sessao = OBTER_SESSAO_ATUAL()
  
  # Renderizar template com resultados
  RETORNAR RENDERIZAR_TEMPLATE("resultados.html", {
    usuario_logado: sessao ? {
      nome: sessao.nome,
      tipo: sessao.tipo
    } : null,
    parametros_busca: parâmetros_busca,
    resultados: resultado_busca.resultados,
    paginacao: resultado_busca.paginacao
  })
FIM-FUNÇÃO
```

### 5.3. Renderização da Página de Detalhes da Licitação
```
FUNÇÃO renderizar_pagina_detalhes(licitacao_id)
  # Obter detalhes da licitação
  resultado = obter_detalhes_licitacao(licitacao_id)
  
  # Verificar se a licitação foi encontrada
  SE resultado.status = 404 ENTÃO
    RETORNAR RENDERIZAR_TEMPLATE("erro_404.html", {
      mensagem: "Licitação não encontrada"
    })
  FIM-SE
  
  # Verificar se há sessão ativa (opcional)
  sessao = OBTER_SESSAO_ATUAL()
  
  # Renderizar template com detalhes
  RETORNAR RENDERIZAR_TEMPLATE("detalhes_licitacao.html", {
    usuario_logado: sessao ? {
      nome: sessao.nome,
      tipo: sessao.tipo
    } : null,
    licitacao: resultado.licitacao
  })
FIM-FUNÇÃO
```

### 5.4. Renderização do Painel Administrativo
```
FUNÇÃO renderizar_painel_admin()
  # Verificar autenticação e autorização
  sessao = OBTER_SESSAO_ATUAL()
  SE NÃO sessao OU sessao.tipo != "master" ENTÃO
    REDIRECIONAR_PARA("/login")
    RETORNAR
  FIM-SE
  
  # Obter lista de usuários do cliente
  resultado = listar_usuarios(sessao.cliente_id, sessao)
  
  # Verificar se houve erro
  SE resultado.status != 200 ENTÃO
    RETORNAR RENDERIZAR_TEMPLATE("erro.html", {
      mensagem: resultado.erro
    })
  FIM-SE
  
  # Renderizar template do painel admin
  RETORNAR RENDERIZAR_TEMPLATE("painel_admin.html", {
    usuario_logado: {
      nome: sessao.nome,
      tipo: sessao.tipo
    },
    usuarios: resultado.usuarios,
    cliente_id: sessao.cliente_id
  })
FIM-FUNÇÃO
```

## 6. Tratamento de Erros e Exceções

```
FUNÇÃO tratar_erro(erro, requisição)
  # Registrar erro em log
  REGISTRAR_LOG(
    nivel: "ERRO",
    mensagem: erro.mensagem,
    stack_trace: erro.stack,
    url: requisição.url,
    metodo: requisição.metodo,
    ip_cliente: requisição.ip
  )
  
  # Determinar tipo de resposta baseado no tipo de requisição
  SE requisição.aceita_html ENTÃO
    # Requisição de página HTML
    RETORNAR RENDERIZAR_TEMPLATE("erro.html", {
      codigo: erro.codigo OU 500,
      mensagem: erro.mensagem OU "Ocorreu um erro interno no servidor"
    })
  SENÃO
    # Requisição de API
    RETORNAR {
      erro: erro.mensagem OU "Ocorreu um erro interno no servidor",
      status: erro.codigo OU 500
    }
  FIM-SE
FIM-FUNÇÃO
```

Este detalhamento do algoritmo de funcionamento abrange todos os principais fluxos do sistema de busca de licitações, desde a coleta e processamento de dados, autenticação e autorização, busca e visualização de licitações, gerenciamento de usuários, até a renderização da interface e tratamento de erros.
