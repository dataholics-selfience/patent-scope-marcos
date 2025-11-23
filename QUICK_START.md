# 🚀 Quick Start - Patent Scraper API

## ⚡ Deploy em 3 Minutos

### 1️⃣ Extrair o ZIP
```bash
unzip patent-api.zip
cd patent-api
```

### 2️⃣ Subir no GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/SEU_USERNAME/patent-api.git
git push -u origin main
```

### 3️⃣ Deploy na Railway
1. Acesse [railway.app](https://railway.app)
2. Login com GitHub
3. "New Project" → "Deploy from GitHub repo"
4. Selecione seu repositório
5. ✅ Deploy automático!

**Pronto!** Sua API estará online em ~2 minutos.

---

## 🧪 Testar Localmente (Opcional)

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar servidor
python -m uvicorn app.main:app --reload

# Acessar
open http://localhost:8000/docs
```

---

## 🔍 Primeiro Teste

```bash
# Substitua pela URL da Railway
export API_URL="https://seu-app.railway.app"

# Buscar patentes de aspirin
curl -X POST "$API_URL/search" \
  -H "Content-Type: application/json" \
  -d '{
    "molecule": "aspirin",
    "page": 1,
    "page_size": 5
  }'
```

---

## 📚 Documentação Completa

- **README.md** - Documentação completa
- **DEPLOY.md** - Guia detalhado de deploy
- **EXAMPLES.md** - Exemplos em várias linguagens
- **Swagger UI** - `/docs` na sua URL

---

## 🎯 Endpoints Principais

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/search` | POST | Buscar patentes por molécula |
| `/patent/{id}` | GET | Detalhes de patente |
| `/health` | GET | Health check |
| `/docs` | GET | Documentação interativa |

---

## 💡 Exemplos de Molécula

```json
{"molecule": "C6H12O6"}      // Fórmula molecular
{"molecule": "glucose"}       // Nome
{"molecule": "aspirin"}       // Nome
{"molecule": "caffeine"}      // Nome
```

---

## ⚙️ Estrutura do Projeto

```
patent-api/
├── app/
│   ├── main.py          # FastAPI app
│   ├── scraper.py       # Lógica de scraping
│   ├── parser.py        # Parser HTML (Parsel/Grok)
│   └── models.py        # Modelos Pydantic
├── main.py             # Entry point (raiz)
├── requirements.txt     # Dependências
├── nixpacks.toml       # Config Nixpacks (Railway)
├── railway.toml        # Config Railway
└── Procfile            # Fallback config
```

**📝 Nota:** Projeto inclui 3 arquivos de configuração para garantir que Railway detecta o start command:
- `nixpacks.toml` (recomendado)
- `railway.toml` 
- `Procfile` (fallback)

---

## 🐛 Problemas Comuns

**Erro no deploy?**
```bash
# Ver logs
railway logs
```

**"No start command was found"?**
- ✅ Já corrigido! Este ZIP inclui `nixpacks.toml`, `railway.toml` e `Procfile`
- Veja **RAILWAY_FIX.md** para detalhes completos

**API não responde?**
- Verifique se PORT está correta (Railway define automaticamente)
- Veja logs no dashboard da Railway

**Sem resultados?**
- Tente molécula mais conhecida ("aspirin", "caffeine")
- Verifique paginação

📚 **Troubleshooting completo:** Veja `RAILWAY_FIX.md`

---

## 📞 Suporte

- **Documentação**: Veja README.md
- **Swagger**: `/docs` na sua URL
- **Issues**: GitHub Issues

---

**🎉 Pronto para usar!**

Railway URL: `https://seu-app.railway.app`  
Docs: `https://seu-app.railway.app/docs`
