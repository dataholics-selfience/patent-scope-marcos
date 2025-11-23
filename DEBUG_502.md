# 🚨 DEBUG: Erro 502 "Application failed to respond"

## O Que Significa

✅ **Build OK** - Dockerfile funcionou!  
✅ **Deploy OK** - Aplicação iniciou!  
❌ **Resposta FAIL** - Aplicação crashou ao processar requisição

---

## 🔍 DIAGNÓSTICO PASSO A PASSO

### 1️⃣ Testar Health Check

Abra no browser:
```
https://web-production-a8f0.up.railway.app/health
```

**Se retornar 502:** App crashou ao iniciar (grave)  
**Se retornar JSON:** App viva, problema é no /search

---

### 2️⃣ Testar Endpoint MOCK (Novo!)

Teste com dados fake (sem scraping):

**Postman:**
```
POST https://web-production-a8f0.up.railway.app/search/mock
Content-Type: application/json

{
  "molecule": "test",
  "page": 1,
  "page_size": 5
}
```

**cURL:**
```bash
curl -X POST "https://web-production-a8f0.up.railway.app/search/mock" \
  -H "Content-Type: application/json" \
  -d '{"molecule": "test", "page": 1, "page_size": 5}'
```

**Se MOCK funcionar:** Problema é no scraping  
**Se MOCK falhar:** Problema é na aplicação base

---

### 3️⃣ Ver Logs do Railway

**CRÍTICO:** Logs mostram o erro exato!

1. Railway Dashboard
2. Seu serviço
3. Aba "Deployments"
4. Deployment ativo
5. **"Deploy Logs"** (depois que iniciou)

**Procure por:**
- ❌ Erros em vermelho
- ❌ Python Traceback
- ❌ "Error", "Exception", "Timeout"
- ❌ "Connection refused", "Network error"

**Me mostre o que aparece!**

---

## 🔧 CAUSAS COMUNS & SOLUÇÕES

### **Causa 1: Timeout ao fazer scraping**

**Sintoma:** Demora e depois 502  
**Logs:** "TimeoutError", "Request timeout"

**Solução:** Scraping demora muito (30s+ timeout)

**Fix rápido:**
```python
# Em scraper.py, reduzir timeout
self.session = httpx.AsyncClient(
    timeout=10.0  # Era 30.0
)
```

---

### **Causa 2: Erro ao acessar PatentScope**

**Sintoma:** 502 imediato  
**Logs:** "Connection refused", "HTTP error 403/401"

**Solução:** PatentScope bloqueou ou está offline

**Fix:** Usar endpoint /search/mock por enquanto

---

### **Causa 3: Erro no Parser**

**Sintoma:** 502 depois de alguns segundos  
**Logs:** "AttributeError", "KeyError", "NoneType"

**Solução:** HTML do PatentScope mudou

**Fix:** Usar Grok API ou mock data

---

### **Causa 4: Memória/CPU insuficiente**

**Sintoma:** 502 aleatório  
**Logs:** "Killed", "Out of memory"

**Solução:** Railway free tier tem limites

**Fix:** Otimizar código ou upgrade plano

---

## 🧪 TESTE LOCAL PRIMEIRO

**IMPORTANTE:** Teste local antes de deploy!

```bash
# No diretório do projeto
pip install -r requirements.txt
uvicorn app.main:app --reload

# Outro terminal - testar health
curl http://localhost:8000/health

# Testar mock
curl -X POST http://localhost:8000/search/mock \
  -H "Content-Type: application/json" \
  -d '{"molecule": "test", "page": 1, "page_size": 5}'

# Testar scraping real (pode demorar!)
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"molecule": "aspirin", "page": 1, "page_size": 3}'
```

**Se funcionar local mas não no Railway:**
- Problema de rede/firewall
- Timeout muito curto no Railway
- Recursos insuficientes

---

## 🚀 SOLUÇÕES IMEDIATAS

### **Solução 1: Usar Endpoint MOCK**

Enquanto debugamos, use:
```
POST /search/mock
```

Retorna dados fake instantaneamente (sem 502!)

---

### **Solução 2: Aumentar Timeout no Railway**

Adicionar variável de ambiente:
```
RAILWAY_TIMEOUT=120
```

---

### **Solução 3: Simplificar Scraping**

Reduzir `page_size` inicial:
```json
{
  "molecule": "aspirin",
  "page": 1,
  "page_size": 3  ← Menor = mais rápido
}
```

---

### **Solução 4: Adicionar Grok API**

Se HTML mudou, Grok pode ajudar:
```
GROK_API_KEY=xai-sua_chave
```

---

## 📊 CHECKLIST DE DEBUG

- [ ] `/health` funciona?
- [ ] `/search/mock` funciona?
- [ ] Vi os logs do Railway?
- [ ] Testei local?
- [ ] Scraping demora quanto tempo local?
- [ ] Qual erro aparece nos logs?

---

## 💬 PRÓXIMOS PASSOS

**Me diga:**

1. **`/health` funciona?** (sim/não)
2. **`/search/mock` funciona?** (sim/não)
3. **O que aparece nos logs?** (copie aqui)

Com essas 3 informações, posso corrigir exatamente! 🎯

---

## 🔗 LINKS ÚTEIS

**Testar agora:**
- Health: https://web-production-a8f0.up.railway.app/health
- Mock: https://web-production-a8f0.up.railway.app/search/mock
- Docs: https://web-production-a8f0.up.railway.app/docs

**Railway:**
- Dashboard: https://railway.app/dashboard
- Logs: Deployments → Ver logs
