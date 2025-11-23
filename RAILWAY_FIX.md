# 🔧 Railway Troubleshooting Guide

## Erro: "No start command was found"

### ✅ Solução (Já incluída neste ZIP)

O projeto agora inclui **3 formas** de o Railway detectar o comando de start:

1. **nixpacks.toml** (Recomendado) - Configuração específica do Nixpacks
2. **railway.toml** - Configuração do Railway
3. **Procfile** - Fallback compatível com Heroku

### 📁 Arquivos de Configuração

#### nixpacks.toml
```toml
[phases.setup]
nixPkgs = ["python311"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[start]
cmd = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

#### railway.toml
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

#### Procfile
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

## 🚀 Como Forçar Rebuild

Se mesmo com os arquivos corretos o erro persistir:

### 1. Via Dashboard
1. Vá para o projeto no Railway
2. Clique em "Settings"
3. Role até "Danger Zone"
4. Clique em "Redeploy"

### 2. Via CLI
```bash
railway up --force
```

### 3. Commit Vazio (Força Push)
```bash
git commit --allow-empty -m "Trigger rebuild"
git push
```

## 🔍 Verificar Logs

```bash
# Ver logs em tempo real
railway logs

# Ou no dashboard: Deployments → View Logs
```

## ⚠️ Checklist de Verificação

- [ ] Arquivo `nixpacks.toml` existe na raiz
- [ ] Arquivo `railway.toml` existe na raiz  
- [ ] Arquivo `Procfile` existe na raiz
- [ ] Arquivo `main.py` existe na raiz (entry point)
- [ ] Arquivo `requirements.txt` existe na raiz
- [ ] Pasta `app/` com `main.py` dentro existe

## 📂 Estrutura Esperada

```
patent-api/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app
│   ├── models.py
│   ├── parser.py
│   └── scraper.py
├── main.py              # Entry point (na raiz!)
├── requirements.txt
├── nixpacks.toml        # Configuração Nixpacks
├── railway.toml         # Configuração Railway
├── Procfile            # Fallback
└── runtime.txt
```

## 🐛 Outros Erros Comuns

### Erro: "Module not found"

**Causa:** Dependências não instaladas

**Solução:**
1. Verifique `requirements.txt`
2. Force rebuild
3. Verifique logs de build

### Erro: "Port already in use"

**Causa:** Variável PORT não configurada

**Solução:** Railway define `$PORT` automaticamente. Use sempre:
```python
port = int(os.getenv("PORT", 8000))
```

### Erro: "Application failed to start"

**Causa:** Erro no código Python

**Solução:**
1. Teste localmente primeiro:
```bash
python -m uvicorn app.main:app --reload
```
2. Verifique logs do Railway
3. Verifique imports e sintaxe

## ✅ Teste Local Antes de Deploy

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Rodar localmente
uvicorn app.main:app --reload

# 3. Testar health check
curl http://localhost:8000/health

# 4. Se funcionar local, funcionará na Railway!
```

## 🆘 Ainda com Problemas?

### Opção 1: Usar Template Railway

1. Delete o projeto atual no Railway
2. Use o template direto do Railway:
   - Vá para railway.app/new
   - Clique em "Deploy from GitHub repo"
   - Selecione seu repositório
   - Railway detectará automaticamente

### Opção 2: Deploy Manual via CLI

```bash
# 1. Instalar Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Link ao projeto
railway link

# 4. Deploy
railway up
```

### Opção 3: Verificar Configuração Railway

No dashboard Railway, vá para:
1. **Settings** → **Build Command**: deve estar vazio (auto-detect)
2. **Settings** → **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. **Settings** → **Root Directory**: deve estar vazio ou "/"

## 📞 Suporte

- **Railway Docs**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **Railway Status**: https://status.railway.app

## 🎯 Configuração Manual (Last Resort)

Se tudo falhar, configure manualmente no Railway Dashboard:

1. Vá para **Settings**
2. Em **Deploy**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Em **Environment Variables**:
   - Não precisa adicionar PORT (Railway define automaticamente)

## ✅ Verificação Final

Após deploy bem-sucedido, teste:

```bash
# Substitua pela sua URL
export API_URL="https://seu-app.railway.app"

# 1. Health check
curl "$API_URL/health"

# 2. Busca simples
curl -X POST "$API_URL/search" \
  -H "Content-Type: application/json" \
  -d '{"molecule": "aspirin", "page": 1, "page_size": 5}'

# 3. Documentação
open "$API_URL/docs"
```

---

**🎉 Deploy funcionando?** Parabéns! Agora você tem uma API REST completa de scraping de patentes!
