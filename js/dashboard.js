// Dashboard.js - Main dashboard logic

let currentUser = null;
let currentSearchData = null;
let filteredPatents = [];
let currentPage = 1;
const itemsPerPage = 10;

// Static data (will be replaced with API calls later)
const staticData = {}; // Will hold loaded JSON data

// Initialize dashboard
auth.onAuthStateChanged(async (user) => {
    if (user) {
        currentUser = user;
        document.getElementById('userName').textContent = user.displayName || user.email;
        
        // Show admin button if user is admin
        if (user.email === ADMIN_EMAIL) {
            const adminBtn = document.getElementById('adminBtn');
            if (adminBtn) {
                adminBtn.classList.remove('hidden');
                adminBtn.addEventListener('click', () => {
                    window.location.href = 'admin.html';
                });
            }
        }
        
        await loadUserHistory();
    } else {
        window.location.href = 'index.html';
    }
});

// Logout
document.getElementById('logoutBtn')?.addEventListener('click', async () => {
    try {
        await auth.signOut();
        window.location.href = 'index.html';
    } catch (error) {
        console.error('Logout error:', error);
    }
});

// Tab navigation
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.dataset.tab;
        
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}Tab`).classList.add('active');
        
        // Load tab-specific data
        if (tabName === 'history') {
            loadUserHistory();
        }
    });
});

// Search form submission
document.getElementById('searchForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const searchParams = {
        moleculeName: document.getElementById('moleculeName').value,
        commercialName: document.getElementById('commercialName').value,
        woNumber: document.getElementById('woNumber').value,
        iupacName: document.getElementById('iupacName').value
    };
    
    // Check if at least one field is filled
    const hasSearchTerm = Object.values(searchParams).some(val => val.trim() !== '');
    
    if (!hasSearchTerm) {
        alert('Por favor, preencha pelo menos um campo de busca.');
        return;
    }
    
    await performSearch(searchParams);
});

// Perform search (static data for now)
async function performSearch(params) {
    try {
        // For now, load static data based on molecule name
        const moleculeName = params.moleculeName.toLowerCase();
        
        // Try to load corresponding JSON file
        let data = null;
        try {
            const response = await fetch(`data/${moleculeName}.json`);
            if (response.ok) {
                data = await response.json();
            }
        } catch (error) {
            console.log('Could not load molecule data:', error);
        }
        
        if (!data) {
            alert('Molécula não encontrada. Por enquanto, tente: paracetamol, darolutamide ou axitinib');
            return;
        }
        
        currentSearchData = data;
        filteredPatents = data.search_result?.patents || [];
        
        // Display results
        displayResults();
        displaySummaryCards();
        displayPatentsTable();
        
        // Show results section
        document.getElementById('resultsSection').classList.remove('hidden');
        
        // Save search to history
        await saveSearchToHistory(params, data);
        
    } catch (error) {
        console.error('Search error:', error);
        alert('Erro ao realizar busca. Tente novamente.');
    }
}

// Display summary cards
function displaySummaryCards() {
    if (!currentSearchData) return;
    
    const summary = currentSearchData.executive_summary;
    
    document.getElementById('totalPatents').textContent = summary.total_patents || 0;
    document.getElementById('totalFamilies').textContent = summary.total_families || 0;
    
    // Count active patents
    const activeCount = filteredPatents.filter(p => 
        p.legal_status === 'Active' || p.legal_status === 'Granted'
    ).length;
    document.getElementById('activePatents').textContent = activeCount;
    
    // Calculate patent cliff (next expiring patent)
    const patentCliff = calculatePatentCliff(filteredPatents);
    document.getElementById('patentCliff').textContent = patentCliff;
}

// Display patents table
function displayPatentsTable() {
    const tbody = document.getElementById('patentsTableBody');
    tbody.innerHTML = '';
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pagePatents = filteredPatents.slice(startIndex, endIndex);
    
    pagePatents.forEach(patent => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${patent.publication_number || '-'}</td>
            <td>${truncateText(patent.title || '-', 50)}</td>
            <td>${truncateText((patent.assignees || []).join(', '), 40)}</td>
            <td>${formatDate(patent.priority_date)}</td>
            <td>${formatDate(patent.expiry_date)}</td>
            <td>${patent.jurisdiction || '-'}</td>
            <td><span class="status-badge status-${patent.legal_status?.toLowerCase()}">${patent.legal_status || '-'}</span></td>
            <td>${patent.patent_type || '-'}</td>
            <td>${patent.wo_related || '-'}</td>
            <td>
                <button class="btn btn-primary" onclick="viewPatentDetails('${patent.publication_number}')">Detalhes</button>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    // Update pagination
    updatePagination();
}

// Update pagination
function updatePagination() {
    const totalPages = Math.ceil(filteredPatents.length / itemsPerPage);
    const paginationDiv = document.getElementById('pagination');
    paginationDiv.innerHTML = '';
    
    if (totalPages <= 1) return;
    
    // Previous button
    const prevBtn = document.createElement('button');
    prevBtn.textContent = '← Anterior';
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener('click', () => {
        currentPage--;
        displayPatentsTable();
    });
    paginationDiv.appendChild(prevBtn);
    
    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = i === currentPage ? 'active' : '';
        pageBtn.addEventListener('click', () => {
            currentPage = i;
            displayPatentsTable();
        });
        paginationDiv.appendChild(pageBtn);
    }
    
    // Next button
    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'Próximo →';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.addEventListener('click', () => {
        currentPage++;
        displayPatentsTable();
    });
    paginationDiv.appendChild(nextBtn);
}

// Filter patents
document.getElementById('applyFilters')?.addEventListener('click', () => {
    const jurisdiction = document.getElementById('filterJurisdiction').value;
    const status = document.getElementById('filterStatus').value;
    const type = document.getElementById('filterType').value;
    
    filteredPatents = currentSearchData.search_result?.patents || [];
    
    if (jurisdiction) {
        filteredPatents = filteredPatents.filter(p => p.jurisdiction === jurisdiction);
    }
    
    if (status) {
        filteredPatents = filteredPatents.filter(p => p.legal_status === status);
    }
    
    if (type) {
        filteredPatents = filteredPatents.filter(p => p.patent_type === type);
    }
    
    currentPage = 1;
    displayPatentsTable();
    displaySummaryCards();
});

// Clear filters
document.getElementById('clearFilters')?.addEventListener('click', () => {
    document.getElementById('filterJurisdiction').value = '';
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterType').value = '';
    
    filteredPatents = currentSearchData.search_result?.patents || [];
    currentPage = 1;
    displayPatentsTable();
    displaySummaryCards();
});

// View patent details
window.viewPatentDetails = function(publicationNumber) {
    const patent = filteredPatents.find(p => p.publication_number === publicationNumber);
    if (!patent) return;
    
    const modal = document.getElementById('patentModal');
    const modalBody = document.getElementById('modalBody');
    const modalTitle = document.getElementById('modalTitle');
    
    modalTitle.textContent = patent.title || 'Detalhes da Patente';
    
    modalBody.innerHTML = `
        <div class="modal-section">
            <h3>Informações Básicas</h3>
            <div class="info-grid">
                <div class="info-item">
                    <label>Número de Publicação:</label>
                    <span>${patent.publication_number || '-'}</span>
                </div>
                <div class="info-item">
                    <label>Jurisdição:</label>
                    <span>${patent.jurisdiction || '-'}</span>
                </div>
                <div class="info-item">
                    <label>Status Legal:</label>
                    <span>${patent.legal_status || '-'}</span>
                </div>
                <div class="info-item">
                    <label>Tipo:</label>
                    <span>${patent.patent_type || '-'}</span>
                </div>
            </div>
        </div>
        
        <div class="modal-section">
            <h3>Datas</h3>
            <div class="info-grid">
                <div class="info-item">
                    <label>Data de Prioridade:</label>
                    <span>${formatDate(patent.priority_date)}</span>
                </div>
                <div class="info-item">
                    <label>Data de Depósito:</label>
                    <span>${formatDate(patent.filing_date)}</span>
                </div>
                <div class="info-item">
                    <label>Data de Publicação:</label>
                    <span>${formatDate(patent.publication_date)}</span>
                </div>
                <div class="info-item">
                    <label>Data de Expiração:</label>
                    <span>${formatDate(patent.expiry_date)}</span>
                </div>
            </div>
        </div>
        
        <div class="modal-section">
            <h3>Titulares</h3>
            <p>${(patent.assignees || []).join(', ') || 'Não informado'}</p>
        </div>
        
        <div class="modal-section">
            <h3>Resumo</h3>
            <p>${patent.abstract || 'Não disponível'}</p>
        </div>
        
        <div class="modal-section">
            <h3>Links</h3>
            <p>
                ${patent.source_url ? `<a href="${patent.source_url}" target="_blank">Ver patente original →</a>` : 'Link não disponível'}
            </p>
            ${patent.wo_related ? `<p>WO Relacionado: ${patent.wo_related}</p>` : ''}
        </div>
    `;
    
    modal.classList.remove('hidden');
    modal.classList.add('active');
};

// Close modal
document.querySelector('.close')?.addEventListener('click', () => {
    document.getElementById('patentModal').classList.remove('active');
    document.getElementById('patentModal').classList.add('hidden');
});

// Close modal on outside click
window.addEventListener('click', (e) => {
    const modal = document.getElementById('patentModal');
    if (e.target === modal) {
        modal.classList.remove('active');
        modal.classList.add('hidden');
    }
});

// Save search to history
async function saveSearchToHistory(params, data) {
    if (!currentUser) return;
    
    try {
        await db.collection(COLLECTIONS.searches_v2).add({
            userId: currentUser.uid,
            searchParams: params,
            moleculeName: data.executive_summary?.molecule_name,
            totalPatents: data.executive_summary?.total_patents || 0,
            totalFamilies: data.executive_summary?.total_families || 0,
            timestamp: firebase.firestore.FieldValue.serverTimestamp(),
            resultData: {
                executive_summary: data.executive_summary,
                patents: data.search_result?.patents || []
            }
        });
    } catch (error) {
        console.error('Error saving search:', error);
    }
}

// Load user history
async function loadUserHistory() {
    if (!currentUser) return;
    
    try {
        const snapshot = await db.collection(COLLECTIONS.searches_v2)
            .where('userId', '==', currentUser.uid)
            .orderBy('timestamp', 'desc')
            .limit(20)
            .get();
        
        const historyList = document.getElementById('historyList');
        historyList.innerHTML = '';
        
        if (snapshot.empty) {
            historyList.innerHTML = '<p class="info-text">Nenhuma consulta realizada ainda.</p>';
            return;
        }
        
        snapshot.forEach(doc => {
            const data = doc.data();
            const historyItem = createHistoryItem(data, doc.id);
            historyList.appendChild(historyItem);
        });
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

// Create history item element
function createHistoryItem(data, docId) {
    const div = document.createElement('div');
    div.className = 'history-item';
    
    const timestamp = data.timestamp?.toDate();
    const dateStr = timestamp ? timestamp.toLocaleString('pt-BR') : 'Data não disponível';
    
    div.innerHTML = `
        <div class="history-item-header">
            <div class="history-item-title">${data.moleculeName || 'Consulta sem nome'}</div>
            <div class="history-item-date">${dateStr}</div>
        </div>
        <div class="history-item-details">
            <span>📊 ${data.totalPatents} patentes</span>
            <span>👥 ${data.totalFamilies} famílias</span>
            ${data.searchParams?.woNumber ? `<span>🔖 WO: ${data.searchParams.woNumber}</span>` : ''}
        </div>
    `;
    
    div.addEventListener('click', () => {
        loadHistoricalSearch(data);
    });
    
    return div;
}

// Load historical search
function loadHistoricalSearch(data) {
    currentSearchData = {
        executive_summary: data.resultData?.executive_summary,
        search_result: {
            patents: data.resultData?.patents || []
        }
    };
    
    filteredPatents = currentSearchData.search_result?.patents || [];
    currentPage = 1;
    
    // Switch to search tab
    document.querySelector('[data-tab="search"]').click();
    
    // Display results
    displayResults();
    displaySummaryCards();
    displayPatentsTable();
    
    document.getElementById('resultsSection').classList.remove('hidden');
    
    // Load R&D data
    loadRandDData();
}

// Display results (populate R&D tab)
function displayResults() {
    if (!currentSearchData) return;
    
    loadRandDData();
}

// Load R&D data
function loadRandDData() {
    if (!currentSearchData) return;
    
    const randdContent = document.getElementById('randdContent');
    randdContent.classList.remove('hidden');
    
    const moleculeData = currentSearchData.search_result?.molecule || {};
    const fdaData = currentSearchData.executive_summary?.fda_data || {};
    const clinicalData = currentSearchData.executive_summary?.clinical_trials_data || {};
    
    // Molecule information
    document.getElementById('randd-generic-name').textContent = moleculeData.generic_name || '-';
    document.getElementById('randd-iupac-name').textContent = moleculeData.iupac_name || '-';
    document.getElementById('randd-cas-numbers').textContent = (moleculeData.cas_numbers || []).join(', ') || '-';
    document.getElementById('randd-synonyms').textContent = (moleculeData.synonyms || []).slice(0, 10).join(', ') || '-';
    
    // FDA data
    document.getElementById('fda-approval-status').textContent = fdaData.fda_approval_status || 'Não informado';
    document.getElementById('fda-approval-date').textContent = formatDate(fdaData.approval_date) || '-';
    document.getElementById('fda-sponsor').textContent = fdaData.sponsor || '-';
    document.getElementById('fda-indications').textContent = (fdaData.indications || []).join(', ') || '-';
    document.getElementById('fda-dosage-forms').textContent = (fdaData.dosage_forms || []).join(', ') || '-';
    
    // Clinical trials summary
    document.getElementById('total-trials').textContent = clinicalData.total_trials || 0;
    document.getElementById('phase-1-trials').textContent = clinicalData.trials_by_phase?.['Phase 1'] || 0;
    document.getElementById('phase-2-trials').textContent = clinicalData.trials_by_phase?.['Phase 2'] || 0;
    document.getElementById('phase-3-trials').textContent = clinicalData.trials_by_phase?.['Phase 3'] || 0;
    document.getElementById('phase-4-trials').textContent = clinicalData.trials_by_phase?.['Phase 4'] || 0;
    
    // Clinical trials table
    const trialsBody = document.getElementById('trialsTableBody');
    trialsBody.innerHTML = '';
    
    const trials = clinicalData.trials || [];
    trials.slice(0, 10).forEach(trial => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${trial.nct_id || '-'}</td>
            <td>${truncateText(trial.title || '-', 60)}</td>
            <td>${trial.phase || '-'}</td>
            <td>${trial.overall_status || '-'}</td>
            <td>${trial.primary_sponsor || '-'}</td>
            <td>${trial.start_date || '-'}</td>
        `;
        trialsBody.appendChild(row);
    });
    
    // Patent families
    const familiesContainer = document.getElementById('familiesContainer');
    familiesContainer.innerHTML = '';
    
    const families = currentSearchData.search_result?.families || [];
    if (families.length === 0) {
        familiesContainer.innerHTML = '<p class="info-text">Nenhuma família de patente encontrada.</p>';
    } else {
        families.forEach(family => {
            const familyDiv = document.createElement('div');
            familyDiv.className = 'family-item';
            familyDiv.innerHTML = `
                <h4>Família: ${family.family_id || 'Não identificado'}</h4>
                <p>Data de Prioridade: ${formatDate(family.priority_date)}</p>
                <p>Membros: ${family.total_members || 0}</p>
                <p>Jurisdições: ${(family.jurisdictions_covered || []).join(', ')}</p>
            `;
            familiesContainer.appendChild(familyDiv);
        });
    }
}

// Export PDF
document.getElementById('exportPdf')?.addEventListener('click', () => {
    alert('Funcionalidade de exportação PDF em desenvolvimento.');
});

// Save search button
document.getElementById('saveSearch')?.addEventListener('click', () => {
    alert('Consulta salva no histórico!');
});

// Helper functions
function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('pt-BR');
    } catch {
        return dateString;
    }
}

function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Add CSS for status badges dynamically
const style = document.createElement('style');
style.textContent = `
    .status-badge {
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .status-active {
        background: #d1fae5;
        color: #065f46;
    }
    .status-granted {
        background: #dbeafe;
        color: #1e40af;
    }
    .status-abandoned {
        background: #fee2e2;
        color: #991b1b;
    }
    .family-item {
        background: var(--light-bg);
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
    }
    .family-item h4 {
        color: var(--primary-color);
        margin-bottom: 8px;
    }
    .family-item p {
        font-size: 13px;
        color: var(--text-secondary);
        margin-bottom: 4px;
    }
`;
document.head.appendChild(style);
