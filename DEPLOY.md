# 🚂 Guia de Deploy na Railway

## Passo a Passo Completo

### 1. Preparar o Repositório GitHub

```bash
# 1. Criar repositório no GitHub
# Vá para github.com e crie um novo repositório

# 2. Inicializar git localmente (se ainda não fez)
cd patent-api
git init

# 3. Adicionar todos os arquivos
git add .

# 4. Commit inicial
git commit -m "Initial commit - Patent Scraper API"

# 5. Conectar ao repositório remoto
git remote add origin https://github.com/SEU_USERNAME/patent-api.git

# 6. Push para GitHub
git branch -M main
git push -u origin main
```

### 2. Deploy na Railway

#### Opção A: Via Dashboard (Mais Fácil)

1. **Acesse Railway**
   - Vá para [railway.app](https://railway.app)
   - Faça login com GitHub

2. **Criar Novo Projeto**
   - Clique em "New Project"
   - Selecione "Deploy from GitHub repo"
   - Autorize Railway a acessar seus repositórios
   - Selecione o repositório `patent-api`

3. **Configuração Automática**
   - Railway detecta automaticamente:
     - `railway.json` para configurações
     - `Procfile` para comando de inicialização
     - `requirements.txt` para dependências
     - `runtime.txt` para versão do Python

4. **Deploy Automático**
   - Railway faz build e deploy automaticamente
   - Aguarde ~2-3 minutos
   - URL pública será gerada automaticamente

5. **Verificar Deploy**
   - Clique na URL gerada (ex: `https://patent-api-production.up.railway.app`)
   - Acesse `/docs` para ver a documentação
   - Teste com `/health`

#### Opção B: Via CLI Railway

```bash
# 1. Instalar Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Inicializar projeto
railway init

# 4. Deploy
railway up

# 5. Abrir no navegador
railway open
```

### 3. Configurar Variáveis de Ambiente (Opcional)

No dashboard da Railway:

1. Selecione seu projeto
2. Vá para "Variables"
3. Adicione variáveis:
   ```
   PORT=8000 (Railway define automaticamente)
   ENVIRONMENT=production
   ```

### 4. Configurar Domínio Customizado (Opcional)

1. No dashboard, vá para "Settings"
2. Clique em "Domains"
3. Clique em "Generate Domain" para URL da Railway
4. Ou adicione seu domínio customizado

### 5. Testar a API em Produção

```bash
# Substitua pela sua URL do Railway
export API_URL="https://seu-app.railway.app"

# Health check
curl "$API_URL/health"

# Buscar patentes
curl -X POST "$API_URL/search" \
  -H "Content-Type: application/json" \
  -d '{
    "molecule": "aspirin",
    "page": 1,
    "page_size": 5
  }'

# Acessar documentação
open "$API_URL/docs"
```

## Monitoramento e Logs

### Ver Logs em Tempo Real

**No Dashboard:**
1. Selecione seu projeto
2. Clique em "Deployments"
3. Clique no deployment ativo
4. Veja logs em tempo real

**Via CLI:**
```bash
railway logs
```

### Métricas

No dashboard da Railway você pode ver:
- CPU Usage
- Memory Usage
- Network Traffic
- Request Count

## Troubleshooting

### Problema: Deploy Falhou

**Solução 1: Verificar Logs**
```bash
railway logs
```

**Solução 2: Verificar requirements.txt**
```bash
# Certifique-se que todas as dependências estão listadas
cat requirements.txt
```

**Solução 3: Rebuild**
```bash
railway up --force
```

### Problema: API não responde

**Verificar:**
1. Porta está correta? (Railway define $PORT automaticamente)
2. Procfile está correto?
3. Logs mostram erros?

**Procfile correto:**
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Problema: Timeout nas requisições

**Soluções:**
1. Aumentar timeout no scraper (app/scraper.py):
   ```python
   timeout=60.0  # Era 30.0
   ```

2. Usar background tasks para requisições longas

3. Implementar cache

### Problema: 502 Bad Gateway

**Causas comuns:**
1. Aplicação não iniciou corretamente
2. Porta incorreta
3. Erro no código

**Solução:**
```bash
# Ver logs detalhados
railway logs

# Verificar que app está escutando na porta correta
# No main.py deve ter:
port = int(os.getenv("PORT", "8000"))
```

## Updates e Redeploy

### Fazer Update do Código

```bash
# 1. Fazer mudanças no código
# 2. Commit
git add .
git commit -m "Update: descrição da mudança"

# 3. Push para GitHub
git push

# Railway faz redeploy automaticamente!
```

### Rollback para Versão Anterior

No dashboard da Railway:
1. Vá para "Deployments"
2. Selecione deployment anterior
3. Clique em "Redeploy"

## Otimizações para Produção

### 1. Adicionar Cache

```python
# Instalar redis
# No requirements.txt adicione: redis==5.0.8

# No código
import redis
r = redis.from_url(os.getenv('REDIS_URL'))
```

### 2. Rate Limiting

```python
# Instalar slowapi
# No requirements.txt adicione: slowapi==0.1.9

from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

### 3. Logging

```python
# Adicionar logging estruturado
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### 4. Monitoramento

```python
# Adicionar Sentry para error tracking
# No requirements.txt: sentry-sdk[fastapi]==1.39.0

import sentry_sdk
sentry_sdk.init(dsn=os.getenv('SENTRY_DSN'))
```

## Custos

Railway oferece:
- **$5 de créditos grátis por mês**
- **$0.000231 por minuto de CPU**
- **$0.000231 por MB de RAM por minuto**

Para esta API simples:
- Uso estimado: ~$3-5/mês (dentro do free tier!)

## Scaling

Railway escala automaticamente até os limites definidos.

Para aumentar limites:
1. Dashboard → Settings
2. Ajuste CPU e RAM limits
3. Configure Auto-scaling

## Backup e Manutenção

### Backup do Código
- Sempre no GitHub (já está configurado!)

### Manutenção
```bash
# Update de dependências
pip list --outdated
pip install -U nome-do-pacote
pip freeze > requirements.txt
git commit -am "Update dependencies"
git push
```

## URLs Úteis

- **Dashboard Railway**: https://railway.app/dashboard
- **Docs Railway**: https://docs.railway.app
- **Status Railway**: https://status.railway.app
- **Community**: https://discord.gg/railway

## Próximos Passos

1. ✅ Deploy na Railway (você está aqui!)
2. 📝 Teste a API
3. 🔒 Adicione autenticação (opcional)
4. 📊 Configure monitoramento
5. 🚀 Compartilhe sua API!

---

**Dúvidas?** Abra uma issue no GitHub ou consulte a documentação da Railway!
