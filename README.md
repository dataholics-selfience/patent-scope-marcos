# PatentScope Scraper

Ferramenta para busca e extração de patentes do WIPO PatentScope com geração inteligente de termos alternativos.

## Arquivos Essenciais

### Scripts Python
- `busca_completa_patentscope.py` - Script principal de busca
- `patentscope_scraper.py` - Cliente Selenium para PatentScope
- `patentscope_detalhes.py` - Extração de detalhes completos
- `config_patentscope.py` - Configurações do scraper
- `busca_inpi.py` - Gerador de termos alternativos

### Configuração
- `requirements.txt` - Dependências Python
- `dicionario_termos.json` - Dicionário de termos farmacêuticos
- `.env` - Credenciais (criar a partir do .env.example)

## Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd xlon_scraper
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as credenciais (opcional):
```bash
cp .env.example .env
# Edite .env e adicione suas credenciais WIPO (opcional)
```

4. Instale o ChromeDriver:
- Baixe o ChromeDriver compatível com seu Chrome: https://chromedriver.chromium.org/
- Adicione ao PATH do sistema

## Uso

Execute o script principal:
```bash
python busca_completa_patentscope.py
```

O script irá solicitar:
1. Termo de busca (ex: "semaglutide")
2. Quantidade de patentes por termo (padrão: 50)
3. Filtro por país (opcional)
4. Login WIPO (opcional - funciona sem autenticação)
5. Buscar detalhes completos (s/N)

## Funcionalidades

- Busca de patentes no PatentScope (WIPO)
- Geração inteligente de termos alternativos usando:
  - Dicionário farmacêutico local
  - Claude AI (se configurado)
  - Variações automáticas
- Extração de detalhes completos:
  - Dados bibliográficos (15+ campos)
  - Abstract/Resumo completo
  - Claims/Reivindicações
  - Descrição
  - Classificações IPC/CPC
  - Citações e documentos relacionados
- Exportação para:
  - JSON completo
  - CSV para Excel
  - Relatório com estatísticas

## Estrutura dos Resultados

Os resultados são salvos em `resultados/patentscope_<termo>_<timestamp>/`:
- `patents_complete.json` - Todas as patentes com detalhes
- `summary_with_stats.json` - Resumo com estatísticas
- `patents.csv` - Planilha Excel
- Screenshots da busca (opcional)

## Configuração Avançada

### Variáveis de Ambiente (.env)

```env
# Modo de execução
SCRAPER_ENV=production

# Rate Limiting
MIN_DELAY=1.0
MAX_DELAY=3.0

# Logging
LOG_LEVEL=INFO

# API Claude (opcional - para geração de termos)
ANTHROPIC_API_KEY=

# WIPO PatentScope (opcional - funciona sem)
WIPO_USERNAME=
WIPO_PASSWORD=
```

### Dicionário de Termos

Edite `dicionario_termos.json` para adicionar novos termos farmacêuticos:

```json
{
  "termos_farmaceuticos": {
    "NOVO_TERMO": {
      "categoria": "Oncologia",
      "nomes_comerciais": ["MARCA1", "MARCA2"],
      "mecanismo_acao": ["MECANISMO"],
      "area_terapeutica": ["AREA"],
      "prioridade": ["TERMO1", "TERMO2"]
    }
  }
}
```

## Notas Importantes

- O PatentScope funciona **sem autenticação** (modo anônimo)
- Respeita rate limits do WIPO (delays configuráveis)
- Usa Selenium para contornar limitações de API
- Salva screenshots para debug (modo headless=False)
- Agrupa patentes por publicationNumber (remove duplicatas)

## Troubleshooting

### ChromeDriver não encontrado
```bash
# Windows: Baixe e adicione ao PATH
# Linux/Mac:
sudo apt-get install chromium-chromedriver  # Ubuntu
brew install chromedriver  # Mac
```

### Timeout nas buscas
Aumente os delays em `.env`:
```env
MIN_DELAY=2.0
MAX_DELAY=5.0
```

### Erro ao carregar página
Execute com modo headless desativado para debug:
Edite `busca_completa_patentscope.py` linha 80:
```python
scraper = PatentScopeScraper(headless=False)
```

## Licença

Uso interno - XLON

## Contato

Para suporte, entre em contato com a equipe de desenvolvimento.
