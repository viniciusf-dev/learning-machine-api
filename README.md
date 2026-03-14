# Agno Memory Bridge API

Uma API Python robusta e type-safe para extrair e recuperar memórias de conversas entre canais usando Agno Learning Machines.

## ✨ Características

- **Type Safety E2E**: Validação completa de tipos com Pydantic v2
- **Error Handling Robusto**: Exceções estruturadas com logging seguro
- **Configuração Centralizada**: Todas as settings em um único lugar
- **Separação de Responsabilidades**: Service layer desacoplado de FastAPI
- **Dependency Injection**: Inicialização e cleanup automático de recursos
- **Logging Estruturado**: Rastreamento completo de operações
- **Documentação OpenAPI**: Schemas automáticos com exemplos

## 🏗️ Arquitetura

```
main.py                  ← FastAPI endpoints + exception handlers
├─ api_schemas.py        ← Modelos Pydantic de request/response
├─ service.py            ← Lógica de negócio (processors, curators)
├─ errors.py             ← Exceções tipadas e handlers
├─ dependencies.py       ← Inicialização e lifespan
├─ config.py             ← Variáveis de ambiente validadas
├─ logging_config.py     ← Setup de logging
└─ schemas.py            ← Extensões Agno (perfis, memórias)
```

## 🚀 Quickstart

### 1. Preparar Ambiente

```bash
# Clone e entre no diretório
cd agno-api

# Copiar exemplo de env
cp .env.example .env

# Editar .env com suas credenciais
# DATABASE_URL=postgresql://user:password@localhost:5432/agno_memory
# (Outras variáveis já têm valores padrão)
```

### 2. Instalar Dependências

```bash
# Com pip
pip install -r requirements.txt

# Ou com poetry
poetry install
```

### 3. Rodar Localmente

```bash
# Modo desenvolvimento com auto-reload
uvicorn main:app --reload --port 8000

# Modo produção (com múltiplos workers)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Acesse:
- **API**: http://localhost:8000
- **Documentação (Swagger)**: http://localhost:8000/docs
- **Documentação (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📦 Docker

```bash
# Build
docker build -t agno-api .

# Run
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:password@localhost/agno_memory" \
  -e LOG_LEVEL="INFO" \
  agno-api

# Com docker-compose (create docker-compose.yml)
docker-compose up
```

## 📚 Endpoints

### Health Check
```bash
GET /health
```
Retorna `{"status": "ok"}`

### Process Conversation
```bash
POST /process
Content-Type: application/json

{
  "user_id": "user_12345",
  "session_id": "session_abc",
  "channel": "whatsapp",
  "messages": [
    {
      "role": "user",
      "content": "Meu nome é João Silva e trabalho na empresa XYZ"
    },
    {
      "role": "assistant",
      "content": "Entendi, João! Vou lembrar disso para próximas conversas."
    }
  ]
}
```

**Resposta** (200 OK):
```json
{
  "status": "processed"
}
```

**Erros possíveis**:
- `400 Bad Request`: Validação falhou (veja `error_code`)
- `500 Internal Server Error`: Erro no serviço

### Recall Context
```bash
POST /recall
Content-Type: application/json

{
  "user_id": "user_12345",
  "session_id": "session_xyz",
  "channel": "slack"
}
```

**Resposta** (200 OK):
```json
{
  "user_id": "user_12345",
  "context": "• Nome: João Silva\n• Empresa: XYZ\n• Timezone: America/Sao_Paulo",
  "has_memory": true
}
```

### Clear Memory
```bash
DELETE /memory/user_12345
```

**Resposta** (200 OK):
```json
{
  "status": "cleared",
  "user_id": "user_12345"
}
```

## ⚙️ Configuração

Todas as settings vêm de variáveis de ambiente (via `.env`):

```env
# Banco de dados (obrigatório)
DATABASE_URL=postgresql://user:password@localhost/db

# API
API_HOST=0.0.0.0
API_PORT=8000
API_TITLE=OpenClaw <> Agno Memory Bridge
API_VERSION=1.0.0

# LLM
LLM_MODEL_ID=claude-haiku-4-5
LLM_REQUEST_TIMEOUT=30  # segundos

# Learning Machine
LEARNING_MODE=always  # always | never | smart
ENABLE_ENTITY_MEMORY=true

# Recall
RECALL_MAX_TOKENS=300
RECALL_MIN_RELEVANCE_DAYS=30

# Validação de requisições
MAX_MESSAGES_PER_REQUEST=100
MAX_MESSAGE_LENGTH=10000
MAX_SESSION_ID_LENGTH=255

# Logging
LOG_LEVEL=INFO  # DEBUG | INFO | WARNING | ERROR | CRITICAL

# Feature flags
ENABLE_PROFILING=false
ENABLE_METRICS=true
```

## 🔍 Exemplos Práticos

### Python
```python
import httpx

async def process_message():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/process",
            json={
                "user_id": "user_123",
                "session_id": "sess_abc",
                "channel": "whatsapp",
                "messages": [
                    {
                        "role": "user",
                        "content": "Prefiro respostas diretas e técnicas"
                    }
                ]
            }
        )
        print(response.json())
```

### JavaScript/Node.js
```javascript
const response = await fetch('http://localhost:8000/recall', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'user_123',
    session_id: 'sess_xyz',
    channel: 'slack'
  })
});

const data = await response.json();
console.log(data.context);  // Imprime memórias do usuário
```

### cURL
```bash
# Process
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "session_id": "session_1",
    "channel": "whatsapp",
    "messages": [
      {"role": "user", "content": "Olá!"}
    ]
  }'

# Recall
curl -X POST http://localhost:8000/recall \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "session_id": "session_2",
    "channel": "slack"
  }'
```

## 🧪 Testing

```bash
# Rodar testes
pytest

# Com coverage
pytest --cov=. --cov-report=html

# Apenas um arquivo
pytest tests/test_service.py -v
```

## 📊 Logging

Logs estruturados com contexto completo:

```
[INFO] 2026-03-14 10:30:45 [agno.main] Application started
[INFO] 2026-03-14 10:30:45 [agno.dependencies] Initializing database...
[INFO] 2026-03-14 10:30:46 [agno.main] POST /process from 127.0.0.1
[INFO] 2026-03-14 10:30:47 [agno.service] Successfully processed messages for user=user_123
[ERROR] 2026-03-14 10:30:48 [agno.main] API Error [database_error]: Connection timeout
```

Nível configurável via `LOG_LEVEL`:
- `DEBUG`: Tudo, incluindo requests HTTP detalhadas
- `INFO`: Operações principais (padrão)
- `WARNING`: Apenas avisos e erros
- `ERROR`: Apenas erros
- `CRITICAL`: Apenas falhas críticas

## 🛡️ Error Handling

Todos os erros retornam estrutura padrão:

```json
{
  "error": "validation_failed",
  "message": "Invalid session_id format",
  "detail": null  // Só em modo debug
}
```

Códigos de erro disponíveis:
- `invalid_request`: Formato da requisição inválido
- `validation_failed`: Falha na validação
- `message_limit_exceeded`: Muitas mensagens
- `message_too_long`: Mensagem muito grande
- `invalid_session_id`: session_id inválido
- `invalid_user_id`: user_id inválido
- `invalid_channel`: Channel não suportado
- `database_error`: Erro no banco de dados
- `learning_machine_error`: Erro na máquina de aprendizado
- `llm_error`: Erro do serviço LLM (Claude)
- `service_unavailable`: Serviço temporariamente indisponível
- `internal_error`: Erro inesperado

## 🔧 Troubleshooting

### "Service not initialized"
A app está rodando mas containers de dependências não foram inicializados. Isso acontece se:
- DB não conectou no startup
- Agno/Claude não respondeu

**Solução**: Cheque logs, valide DATABASE_URL e credenciais de API.

### "Database connection timeout"
```bash
# Teste conexão
psql postgresql://user:password@localhost/db

# Se não conecta, valide:
# 1. Server PostgreSQL está rodando?
# 2. Credenciais estão certas?
# 3. IP/porta acessível?
```

### "LLM timeout"
Se requests para Claude demoram muito:
- Aumentar `LLM_REQUEST_TIMEOUT` em `.env`
- Reduzir tamanho de mensagens (verificar `MAX_MESSAGE_LENGTH`)
- Checar latência de rede

### Mensagens muito grandes são rejeitadas
O limite é `MAX_MESSAGE_LENGTH` (default 10000 caracteres). Para aumentar:

```env
MAX_MESSAGE_LENGTH=50000
```

## 📚 Estrutura do Código

```python
# config.py - Todas as variáveis aqui
class Settings(BaseSettings):
    database_url: str
    llm_model_id: str
    recall_max_tokens: int
    # ... etc

settings = Settings()  # Loaded from .env

# service.py - Lógica de negócio
class ConversationProcessor:
    def process_messages(context, messages) -> None
    
class ContextRecall:
    def recall_context(context) -> str

# api_schemas.py - Modelos de API com validação
class ProcessRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)
    messages: List[MessageRequest] = Field(min_length=1)

# errors.py - Exceções tipadas
class ApiException(Exception):
    error_code: ErrorCode
    message: str
    status_code: int
    internal_detail: str

# main.py - Endpoints FastAPI
@app.post("/process")
async def process_messages(req: ProcessRequest) -> ProcessResponse:
    # Valida, converte, chama serviço, retorna
```

## 🎯 Próximos Passos

1. **Testes**: Adicionar testes unitários em `tests/`
2. **Monitoring**: Integrar Prometheus/Grafana
3. **Caching**: Redis para respostas frequentes
4. **Rate Limiting**: Proteção por user_id
5. **Async Processing**: Fila para operações longas
6. **Multi-tenancy**: Suportar múltiplas organizações

## 📖 Documentação Adicional

- `ANALYSIS.md` - Análise detalhada dos problemas identificados
- `.env.example` - Todas as variáveis de configuração
- Swagger: `/docs` (interativo)
- ReDoc: `/redoc` (legível)

## 📝 Licença

MIT

## 👥 Suporte

Encontrou um problema? Abra uma issue com:
1. O que tentou
2. Mensagem de erro exata
3. Configuração (.env sem credenciais)
4. Logs relevantes
# learning-machine-api
