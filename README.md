# 🧪 Patent Scraper API - Molecule Search

API REST para busca de patentes no WIPO PatentScope usando fórmulas moleculares, SMILES ou nomes de moléculas.

## 🚀 Deploy Rápido na Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)

### Passos para Deploy:

1. **Fork ou clone este repositório**
   ```bash
   git clone <seu-repo>
   cd patent-api
   ```

2. **Crie novo projeto na Railway**
   - Acesse [railway.app](https://railway.app)
   - Clique em "New Project"
   - Selecione "Deploy from GitHub repo"
   - Escolha este repositório

3. **Deploy automático!**
   - Railway detecta automaticamente `railway.json` e `Procfile`
   - Build e deploy acontecem automaticamente
   - URL pública será gerada (ex: `https://seu-app.railway.app`)

## 📋 Funcionalidades

✅ **Busca por molécula** - Fórmula molecular, SMILES ou nome  
✅ **Paginação completa** - Navigate por milhares de resultados  
✅ **Parser robusto** - Usa Parsel (Grok-like) para lidar com tags que mudam  
✅ **Grok API Integration** - Parser adaptativo com IA quando tags mudam (opcional)  
✅ **API REST JSON** - Envie molécula, receba resultados em JSON  
✅ **Retry automático** - Handling de erros e timeouts  
✅ **Documentação interativa** - Swagger UI em `/docs`  

## 🔧 Uso Local

### Instalação

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar servidor
python -m uvicorn app.main:app --reload --port 8000
```

Acesse: **http://localhost:8000/docs**

### 🤖 Grok API (Opcional - Parser Adaptativo)

A API inclui integração com Grok para parsing adaptativo quando as tags HTML do PatentScope mudarem.

**Como ativar:**
1. Obtenha uma chave API Grok em [x.ai](https://x.ai)
2. Configure a variável de ambiente:
   ```bash
   export GROK_API_KEY="seu_grok_api_key"
   ```
3. No Railway: Settings → Variables → Add `GROK_API_KEY`

**Como funciona:**
- Parser tradicional (Parsel) tenta primeiro
- Se falhar, Grok API analisa o HTML e extrai dados
- Completamente opcional - funciona sem Grok também

## 📖 Endpoints

### 1. Buscar Patentes por Molécula

**POST /search**

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "molecule": "C6H12O6",
    "search_type": "exact",
    "page": 1,
    "page_size": 10
  }'
```

**Parâmetros:**
- `molecule` (obrigatório): Fórmula molecular, SMILES ou nome
- `search_type`: "exact", "similarity", "substructure" (padrão: "exact")
- `page`: Número da página (padrão: 1)
- `page_size`: Resultados por página (padrão: 10, máx: 100)

**Resposta:**
```json
{
  "status": "success",
  "query": "C6H12O6",
  "results": [
    {
      "patent_id": "WO2023123456",
      "publication_number": "WO2023123456A1",
      "title": "Novel glucose-based compound...",
      "abstract": "The present invention relates to...",
      "applicants": ["Company XYZ"],
      "inventors": ["John Doe", "Jane Smith"],
      "publication_date": "2023-06-29",
      "ipc_codes": ["A61K31/00"],
      "url": "https://patentscope.wipo.int/..."
    }
  ],
  "pagination": {
    "current_page": 1,
    "page_size": 10,
    "total_results": 156,
    "total_pages": 16,
    "has_next": true,
    "has_previous": false,
    "next_page": 2
  },
  "metadata": {
    "search_type": "exact",
    "duration_ms": 1234,
    "scraped_at": "2024-01-15T10:30:00",
    "source": "WIPO PatentScope"
  }
}
```

### 2. Detalhes de Patente

**GET /patent/{patent_id}**

```bash
curl "http://localhost:8000/patent/WO2023123456"
```

### 3. Health Check

**GET /health**

```bash
curl "http://localhost:8000/health"
```

## 🐍 Exemplo em Python

```python
import requests

# Buscar patentes
response = requests.post(
    "http://localhost:8000/search",
    json={
        "molecule": "aspirin",
        "page": 1,
        "page_size": 20
    }
)

data = response.json()

print(f"Total: {data['pagination']['total_results']} patentes")
print(f"Página: {data['pagination']['current_page']}/{data['pagination']['total_pages']}")

for patent in data['results']:
    print(f"\n{patent['publication_number']}")
    print(f"Título: {patent['title']}")
    print(f"Aplicantes: {', '.join(patent['applicants'])}")
    print(f"URL: {patent['url']}")

# Navegar para próxima página
if data['pagination']['has_next']:
    next_page = data['pagination']['next_page']
    response = requests.post(
        "http://localhost:8000/search",
        json={
            "molecule": "aspirin",
            "page": next_page,
            "page_size": 20
        }
    )
```

## 📊 Exemplos de Busca

### Por Fórmula Molecular
```json
{"molecule": "C6H12O6"}
{"molecule": "C9H8O4"}
{"molecule": "CH4"}
```

### Por Nome da Molécula
```json
{"molecule": "glucose"}
{"molecule": "aspirin"}
{"molecule": "caffeine"}
{"molecule": "penicillin"}
```

### Por SMILES
```json
{"molecule": "CC(=O)Oc1ccccc1C(=O)O"}
{"molecule": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"}
```

## 🔍 Como Funciona

1. **Input**: Você envia uma molécula (fórmula, SMILES ou nome)
2. **Query Building**: API constrói query otimizada para PatentScope
3. **Scraping**: Usa `httpx` (async) para fazer requisições
4. **Parsing**: `Parsel` (Grok-like) extrai dados com múltiplos seletores
5. **Paginação**: Calcula e retorna metadados de paginação
6. **Output**: JSON estruturado com resultados

### Parser Robusto com Parsel

O parser usa **múltiplos seletores CSS/XPath** para cada campo, lidando com mudanças na estrutura HTML:

```python
# Exemplo: Buscar título com fallbacks
title_selectors = [
    '.title::text',
    'h3::text',
    '.patent-title::text',
    'a[href*="docId"]::text',
]

for selector in title_selectors:
    title = item.css(selector).get()
    if title:
        break
```

## 🛠️ Estrutura do Projeto

```
patent-api/
├── app/
│   ├── __init__.py        # Package init
│   ├── main.py            # FastAPI app
│   ├── models.py          # Pydantic models
│   ├── parser.py          # HTML parser com Parsel
│   └── scraper.py         # Scraping logic
├── requirements.txt       # Dependências Python
├── Procfile              # Railway/Heroku config
├── railway.json          # Railway config
├── runtime.txt           # Python version
├── .env.example          # Environment vars
├── .gitignore            # Git ignore
└── README.md             # Esta documentação
```

## 📦 Dependências Principais

- **FastAPI** - Framework web moderno e rápido
- **httpx** - Cliente HTTP assíncrono
- **Parsel** - Parser HTML robusto (usado no Scrapy)
- **Pydantic** - Validação de dados
- **uvicorn** - ASGI server

## 🚨 Notas Importantes

1. **Rate Limiting**: Implemente delays entre requisições para não sobrecarregar o servidor
2. **Scraping Ético**: Use apenas para fins educacionais/pesquisa
3. **Mudanças no Site**: O PatentScope pode mudar estrutura HTML - o parser usa múltiplos seletores para resiliência
4. **Timeout**: Requisições têm timeout de 30s por padrão

## 🐛 Troubleshooting

### Erro: "No results found"
- Tente uma molécula mais conhecida (ex: "aspirin")
- Verifique se a fórmula está correta
- Tente search_type diferente

### Erro: "Timeout"
- Aumente o timeout no scraper
- Verifique sua conexão
- PatentScope pode estar lento

### Erro na Railway
- Verifique logs no dashboard da Railway
- Certifique-se que PORT está correta
- Verifique requirements.txt está completo

## 📝 TODO

- [ ] Adicionar cache com Redis
- [ ] Implementar rate limiting
- [ ] Adicionar mais fontes de patentes (USPTO, EPO)
- [ ] Suporte a estruturas químicas visuais
- [ ] Export para CSV/Excel
- [ ] Filtros avançados (data, país, etc.)

## 📄 Licença

MIT License - Use livremente!

## 🤝 Contribuindo

Pull requests são bem-vindos! Para mudanças grandes, abra uma issue primeiro.

## 📞 Suporte

- Documentação: `/docs` ou `/redoc`
- Issues: GitHub Issues
- Email: seu@email.com

---

**Feito com ❤️ e FastAPI**
