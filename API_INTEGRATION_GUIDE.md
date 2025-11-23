# Guia de Integração com API

Este documento descreve como integrar o frontend com a API do backend quando estiver pronta.

## 📡 Endpoints Esperados

### 1. Busca de Patentes
```
POST /api/v2/search
Content-Type: application/json

Body:
{
  "molecule_name": "string",
  "commercial_name": "string",
  "wo_number": "string",
  "iupac_name": "string",
  "cas_number": "string"
}

Response:
{
  "executive_summary": {...},
  "search_result": {
    "molecule": {...},
    "patents": [...],
    "families": [...]
  }
}
```

### 2. Upload de Estrutura Molecular
```
POST /api/v2/ocr/molecule
Content-Type: multipart/form-data

Body:
{
  "image": File
}

Response:
{
  "molecule_detected": true,
  "iupac_name": "string",
  "cas_number": "string",
  "confidence": 0.95
}
```

### 3. Desenho de Molécula
```
POST /api/v2/draw/molecule
Content-Type: application/json

Body:
{
  "smiles": "string",
  "mol_file": "string"
}

Response:
{
  "molecule_id": "string",
  "iupac_name": "string",
  "molecular_formula": "string"
}
```

## 🔧 Modificações Necessárias

### 1. Atualizar `dashboard.js`

Substituir a função `performSearch`:

```javascript
async function performSearch(params) {
    try {
        // Show loading state
        showLoading(true);
        
        // Call API
        const response = await fetch('https://api.pharmyrus.com/v2/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${await getAuthToken()}`
            },
            body: JSON.stringify(params)
        });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Rest of the code remains the same
        currentSearchData = data;
        filteredPatents = data.search_result?.patents || [];
        
        displayResults();
        displaySummaryCards();
        displayPatentsTable();
        
        document.getElementById('resultsSection').classList.remove('hidden');
        
        await saveSearchToHistory(params, data);
        
    } catch (error) {
        console.error('Search error:', error);
        showError('Erro ao realizar busca. Tente novamente.');
    } finally {
        showLoading(false);
    }
}

// Helper function to get auth token
async function getAuthToken() {
    if (!currentUser) return null;
    return await currentUser.getIdToken();
}
```

### 2. Adicionar Upload de Imagem

No `dashboard.js`, adicionar:

```javascript
// Handle image upload
document.getElementById('moleculeImage')?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    try {
        showLoading(true);
        
        const formData = new FormData();
        formData.append('image', file);
        
        const response = await fetch('https://api.pharmyrus.com/v2/ocr/molecule', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${await getAuthToken()}`
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('OCR failed');
        }
        
        const result = await response.json();
        
        // Auto-fill form with detected data
        if (result.iupac_name) {
            document.getElementById('iupacName').value = result.iupac_name;
        }
        
        showSuccess(`Molécula detectada: ${result.iupac_name || 'Desconhecida'}`);
        
    } catch (error) {
        console.error('OCR error:', error);
        showError('Erro ao processar imagem. Tente novamente.');
    } finally {
        showLoading(false);
    }
});
```

### 3. Adicionar Loading States

Adicionar ao `dashboard.js`:

```javascript
function showLoading(show) {
    const loadingEl = document.getElementById('loadingIndicator');
    if (show) {
        if (!loadingEl) {
            const loading = document.createElement('div');
            loading.id = 'loadingIndicator';
            loading.className = 'loading-overlay';
            loading.innerHTML = `
                <div class="loading-spinner">
                    <div class="spinner"></div>
                    <p>Consultando patentes...</p>
                </div>
            `;
            document.body.appendChild(loading);
        }
    } else {
        if (loadingEl) {
            loadingEl.remove();
        }
    }
}

function showError(message) {
    // Show toast or alert with error
    alert(message); // Replace with better UI
}

function showSuccess(message) {
    // Show toast or alert with success
    console.log(message); // Replace with better UI
}
```

### 4. Adicionar CSS para Loading

Adicionar ao `dashboard.css`:

```css
.loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

.loading-spinner {
    background: white;
    padding: 40px;
    border-radius: 12px;
    text-align: center;
}

.spinner {
    width: 50px;
    height: 50px;
    border: 4px solid var(--border-color);
    border-top-color: var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 20px;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
```

## 🔐 Autenticação

A API deve aceitar tokens JWT do Firebase:

```javascript
// No backend, validar token
const admin = require('firebase-admin');

async function validateToken(token) {
    try {
        const decodedToken = await admin.auth().verifyIdToken(token);
        return decodedToken;
    } catch (error) {
        throw new Error('Invalid token');
    }
}
```

## 📊 Rate Limiting

Implementar no frontend:

```javascript
class RateLimiter {
    constructor(maxRequests, timeWindow) {
        this.maxRequests = maxRequests;
        this.timeWindow = timeWindow;
        this.requests = [];
    }
    
    canMakeRequest() {
        const now = Date.now();
        this.requests = this.requests.filter(time => now - time < this.timeWindow);
        
        if (this.requests.length < this.maxRequests) {
            this.requests.push(now);
            return true;
        }
        
        return false;
    }
    
    getTimeUntilNextRequest() {
        if (this.requests.length < this.maxRequests) return 0;
        
        const oldestRequest = Math.min(...this.requests);
        return this.timeWindow - (Date.now() - oldestRequest);
    }
}

// Usage
const limiter = new RateLimiter(10, 60000); // 10 requests per minute

async function performSearch(params) {
    if (!limiter.canMakeRequest()) {
        const waitTime = Math.ceil(limiter.getTimeUntilNextRequest() / 1000);
        showError(`Limite de requisições atingido. Aguarde ${waitTime}s.`);
        return;
    }
    
    // ... rest of search logic
}
```

## 🧪 Testing

### Teste Local com Mock API

Criar arquivo `js/mock-api.js`:

```javascript
class MockAPI {
    static async search(params) {
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Return static data
        const molecule = params.moleculeName?.toLowerCase();
        const response = await fetch(`data/${molecule}.json`);
        return await response.json();
    }
    
    static async ocrMolecule(file) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        return {
            molecule_detected: true,
            iupac_name: "N-(4-hydroxyphenyl)acetamide",
            cas_number: "103-90-2",
            confidence: 0.95
        };
    }
}

// Toggle between mock and real API
const USE_MOCK_API = true;

async function performSearch(params) {
    if (USE_MOCK_API) {
        const data = await MockAPI.search(params);
        // ... process data
    } else {
        // ... real API call
    }
}
```

## 📈 Monitoring

Adicionar tracking de uso:

```javascript
async function trackAPICall(endpoint, duration, success) {
    try {
        await db.collection(COLLECTIONS.usage_stats_v2).add({
            userId: currentUser.uid,
            endpoint: endpoint,
            duration: duration,
            success: success,
            timestamp: firebase.firestore.FieldValue.serverTimestamp()
        });
    } catch (error) {
        console.error('Tracking error:', error);
    }
}

// Usage
async function performSearch(params) {
    const startTime = Date.now();
    let success = false;
    
    try {
        // ... API call
        success = true;
    } catch (error) {
        // ... error handling
    } finally {
        const duration = Date.now() - startTime;
        await trackAPICall('/api/v2/search', duration, success);
    }
}
```

## ✅ Checklist de Integração

- [ ] Endpoints da API definidos e documentados
- [ ] Autenticação Firebase configurada no backend
- [ ] Rate limiting implementado
- [ ] Error handling robusto
- [ ] Loading states adicionados
- [ ] Toast/Alert system implementado
- [ ] Mock API para testes locais
- [ ] Tracking de uso configurado
- [ ] Upload de imagem funcionando
- [ ] Validação de inputs
- [ ] Tratamento de timeouts
- [ ] Retry logic para falhas
- [ ] Cache de resultados (opcional)
- [ ] Testes end-to-end

## 🚀 Deploy

Após integração com API:

1. Atualizar variáveis de ambiente
2. Testar em staging
3. Executar testes E2E
4. Deploy para produção
5. Monitorar logs e métricas

---

**Última atualização**: Janeiro 2025
