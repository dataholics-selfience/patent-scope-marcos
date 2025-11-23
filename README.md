# Pharmyrus v2 - Dashboard de Inteligência em Patentes Farmacêuticas

Sistema avançado para consulta e análise de patentes farmacêuticas com dados integrados de FDA, ensaios clínicos, e análise de patent cliff.

## 🚀 Funcionalidades

### ✅ Versão Atual (Estática)
- ✅ Autenticação com Firebase (cadastro com código de convite)
- ✅ Consulta de patentes por múltiplos campos (nome, WO, IUPAC)
- ✅ Visualização em tabela com filtros avançados
- ✅ Cálculo de Patent Cliff
- ✅ Dashboard executivo com métricas
- ✅ Tab P&D com dados FDA e ensaios clínicos
- ✅ Histórico de consultas salvo no Firebase
- ✅ Detalhes completos de patentes
- ✅ Sistema de paginação
- ✅ Interface responsiva

### 🔄 Próximas Versões (Com API)
- 🔄 Integração com API WIPO
- 🔄 Upload e análise de estruturas moleculares
- 🔄 Desenho manual de moléculas
- 🔄 Exportação para PDF
- 🔄 Relatórios executivos personalizados

## 📁 Estrutura do Projeto

```
pharmyrus-v2/
├── index.html              # Página de login/registro
├── dashboard.html          # Dashboard principal
├── css/
│   ├── auth.css           # Estilos de autenticação
│   └── dashboard.css      # Estilos do dashboard
├── js/
│   ├── firebase-config.js # Configuração Firebase
│   ├── auth.js            # Lógica de autenticação
│   ├── dashboard.js       # Lógica principal do dashboard
│   └── patent-cliff.js    # Cálculo de patent cliff
├── data/
│   ├── paracetamol.json   # Dados estáticos (exemplo)
│   ├── darolutamide.json  # Dados estáticos (exemplo)
│   └── axitinib.json      # Dados estáticos (exemplo)
├── _redirects             # Configuração Netlify
└── README.md
```

## 🔐 Firebase Setup

### Projeto Firebase
O projeto usa o **mesmo Firebase** do Pharmyrus v1:
- **Project ID**: `pharmyrus-dashboard`
- **Collections**:
  - `users` - Usuários (compartilhada com v1)
  - `searches_v2` - Histórico de consultas do v2 (exclusiva)
  - `usage_stats_v2` - Estatísticas de uso do v2 (exclusiva)

### Códigos de Convite Beta
Códigos válidos para registro:
- `PHARMYRUS2025`
- `BETA2025`
- `WIPO2025`

## 🌐 Deploy no Netlify

### Opção 1: Netlify Drop (Mais Fácil)
1. Acesse [Netlify Drop](https://app.netlify.com/drop)
2. Arraste a pasta `pharmyrus-v2`
3. Pronto! Seu site está no ar

### Opção 2: Netlify CLI
```bash
# Instalar Netlify CLI
npm install -g netlify-cli

# Deploy
cd pharmyrus-v2
netlify deploy --prod
```

### Opção 3: GitHub + Netlify (Deploy Automático)
1. Faça push para GitHub
2. Conecte o repositório no Netlify
3. Deploy automático a cada commit

## 📊 Dados Estáticos

Por enquanto, o sistema usa dados estáticos em JSON para demonstração:

### Moléculas Disponíveis
- **Paracetamol** - 0 patentes
- **Darolutamide** - 166 patentes
- **Axitinib** - Dados completos

### Estrutura dos JSONs
```json
{
  "executive_summary": {
    "molecule_name": "...",
    "total_patents": 0,
    "total_families": 0,
    "fda_data": {...},
    "clinical_trials_data": {...}
  },
  "search_result": {
    "molecule": {...},
    "patents": [...],
    "families": [...]
  }
}
```

## 🔧 Migração para API

Quando a API estiver pronta, será necessário:

1. **Atualizar `dashboard.js`**:
```javascript
// Substituir a função performSearch
async function performSearch(params) {
    const response = await fetch('https://api.pharmyrus.com/v2/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
    });
    
    const data = await response.json();
    // ... resto do código permanece igual
}
```

2. **Adicionar suporte para upload de imagens**:
```javascript
async function uploadMoleculeImage(file) {
    const formData = new FormData();
    formData.append('image', file);
    
    const response = await fetch('https://api.pharmyrus.com/v2/ocr', {
        method: 'POST',
        body: formData
    });
    
    return await response.json();
}
```

## 👥 Uso

### 1. Registro
1. Acesse a página inicial
2. Clique em "Registre-se"
3. Preencha os dados e use um código de convite válido
4. Clique em "Registrar"

### 2. Login
1. Use email e senha cadastrados
2. Será redirecionado para o dashboard

### 3. Consulta de Patentes
1. Preencha pelo menos um campo de busca
2. Clique em "Buscar"
3. Visualize os resultados na tabela
4. Use os filtros para refinar

### 4. Patent Cliff
- Calculado automaticamente
- Mostra tempo até próxima expiração
- Considera apenas patentes ativas

### 5. Tab P&D
- Dados FDA completos
- Ensaios clínicos
- Informações moleculares
- Famílias de patentes

### 6. Histórico
- Todas as consultas são salvas
- Clique em uma consulta para recarregá-la

## 🎨 Personalização

### Cores
Edite as variáveis CSS em `css/dashboard.css`:
```css
:root {
    --primary-color: #2563eb;
    --primary-dark: #1e40af;
    --success-color: #10b981;
    /* ... */
}
```

### Logo
Adicione seu logo na pasta `images/` e atualize os HTMLs.

## 🔒 Segurança

- ✅ Autenticação Firebase
- ✅ Validação de código de convite
- ✅ Regras de segurança no Firestore
- ✅ Collections separadas por versão
- ✅ Dados do usuário protegidos

### Regras do Firestore (Sugeridas)
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users collection (compartilhada)
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Searches v2 (exclusiva)
    match /searches_v2/{searchId} {
      allow read, write: if request.auth != null && 
                           resource.data.userId == request.auth.uid;
    }
    
    // Usage stats v2 (admin only)
    match /usage_stats_v2/{statId} {
      allow read: if request.auth != null;
      allow write: if false; // Only via Cloud Functions
    }
  }
}
```

## 📱 Responsividade

O dashboard é totalmente responsivo:
- ✅ Desktop (1920px+)
- ✅ Laptop (1024px - 1919px)
- ✅ Tablet (768px - 1023px)
- ✅ Mobile (320px - 767px)

## 🐛 Troubleshooting

### Erro de autenticação
- Verifique as credenciais do Firebase
- Confirme que as regras do Firestore estão corretas

### Dados não carregam
- Verifique o console do navegador
- Confirme que os arquivos JSON estão na pasta `data/`
- Teste com: `paracetamol`, `darolutamide` ou `axitinib`

### Deploy no Netlify não funciona
- Verifique se o arquivo `_redirects` está presente
- Confirme que todos os arquivos CSS/JS estão no repositório

## 📧 Suporte

Para dúvidas ou problemas:
- Email: suporte@pharmyrus.com
- GitHub Issues: [pharmyrus-v2/issues]

## 📄 Licença

© 2025 Pharmyrus. Todos os direitos reservados.

---

**Desenvolvido com ❤️ pela equipe Pharmyrus**
