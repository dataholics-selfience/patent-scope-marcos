// Admin Panel JavaScript - Pharmyrus v2
console.log('Admin.js loaded');

let currentUser = null;
const ADMIN_EMAIL = 'daniel.mendes@dataholics.io';
let currentContractsPage = 1;
const contractsPerPage = 20;
let allContracts = [];

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM ready, initializing admin...');
    initializeAdmin();
});

function initializeAdmin() {
    // Setup event listeners first
    setupEventListeners();
    
    // Then check auth
    auth.onAuthStateChanged(async (user) => {
        console.log('Auth state changed:', user?.email);
        
        if (user) {
            currentUser = user;
            
            // Verify admin status
            if (user.email !== ADMIN_EMAIL) {
                alert('Acesso negado! Apenas administradores podem acessar este painel.');
                window.location.href = 'dashboard.html';
                return;
            }
            
            // Update UI with user info
            const userNameEl = document.getElementById('userName');
            if (userNameEl) {
                userNameEl.textContent = user.displayName || user.email;
            }
            
            // Load overview data
            console.log('Loading overview data...');
            await loadOverviewData();
            
        } else {
            console.log('No user, redirecting...');
            window.location.href = 'index.html';
        }
    });
}

function setupEventListeners() {
    console.log('Setting up event listeners');
    
    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            try {
                await auth.signOut();
                window.location.href = 'index.html';
            } catch (error) {
                console.error('Logout error:', error);
            }
        });
    }
    
    // Back to dashboard button
    const backBtn = document.getElementById('backToDashboard');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            window.location.href = 'dashboard.html';
        });
    }
    
    // Tab navigation
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const tabName = btn.dataset.tab;
            console.log('Tab clicked:', tabName);
            
            // Update active tab
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Show corresponding content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            const tabContent = document.getElementById(`${tabName}Tab`);
            if (tabContent) {
                tabContent.classList.add('active');
            }
            
            // Load tab-specific data
            switch(tabName) {
                case 'overview':
                    await loadOverviewData();
                    break;
                case 'invites':
                    await loadInvites();
                    break;
                case 'users':
                    await loadUsers();
                    break;
                case 'contracts':
                    await loadContracts();
                    break;
                case 'stats':
                    await loadStats();
                    break;
            }
        });
    });
    
    // Create invite form
    const createInviteForm = document.getElementById('createInviteForm');
    if (createInviteForm) {
        createInviteForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await createInvite();
        });
    }
    
    // Contract filters
    const applyFiltersBtn = document.getElementById('applyContractFilters');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', () => {
            displayContracts();
        });
    }
    
    const clearFiltersBtn = document.getElementById('clearContractFilters');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            const filters = ['filterVersion', 'searchContracts', 'filterDateFrom', 'filterDateTo'];
            filters.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            displayContracts();
        });
    }
    
    // Modal close buttons
    const closeModal = document.querySelector('.close');
    if (closeModal) {
        closeModal.addEventListener('click', closeContractModal);
    }
    
    const closeModalBtn = document.getElementById('closeContractModal');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeContractModal);
    }
}

// ========== OVERVIEW TAB ==========

async function loadOverviewData() {
    console.log('Loading overview data...');
    try {
        // Total users
        const usersSnapshot = await db.collection('users').get();
        updateElement('totalUsers', usersSnapshot.size);
        console.log('Total users:', usersSnapshot.size);
        
        // Active users (last 30 days)
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        
        const activeUsersSnapshot = await db.collection('users')
            .where('lastAccess', '>=', thirtyDaysAgo)
            .get();
        updateElement('activeUsers', activeUsersSnapshot.size);
        
        // Total searches (v1 + v2)
        const searchesV1 = await db.collection('searches').get();
        const searchesV2 = await db.collection('searches_v2').get();
        const totalSearches = searchesV1.size + searchesV2.size;
        updateElement('totalSearches', totalSearches);
        console.log('Total searches:', totalSearches);
        
        // Searches today
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        const searchesTodayV1 = await db.collection('searches')
            .where('timestamp', '>=', today)
            .get();
        const searchesTodayV2 = await db.collection('searches_v2')
            .where('timestamp', '>=', today)
            .get();
        updateElement('searchesToday', searchesTodayV1.size + searchesTodayV2.size);
        
        // Active invites
        const invitesSnapshot = await db.collection('invites')
            .where('active', '==', true)
            .get();
        updateElement('activeInvites', invitesSnapshot.size);
        
        // Load recent activity
        await loadRecentActivity();
        
        console.log('Overview loaded successfully');
        
    } catch (error) {
        console.error('Error loading overview:', error);
        alert('Erro ao carregar visão geral: ' + error.message);
    }
}

async function loadRecentActivity() {
    console.log('Loading recent activity...');
    try {
        const activityList = document.getElementById('activityList');
        if (!activityList) return;
        
        activityList.innerHTML = '<div class="loading"><div class="loading-spinner"></div></div>';
        
        const activities = [];
        
        // Get recent users
        try {
            const recentUsers = await db.collection('users')
                .orderBy('createdAt', 'desc')
                .limit(5)
                .get();
            
            recentUsers.forEach(doc => {
                const data = doc.data();
                activities.push({
                    type: 'user',
                    title: `Novo usuário: ${data.name || data.email}`,
                    time: data.createdAt?.toDate() || new Date(),
                    icon: '👤'
                });
            });
        } catch (err) {
            console.log('Error loading users:', err);
        }
        
        // Get recent searches
        try {
            const recentSearches = await db.collection('searches_v2')
                .orderBy('timestamp', 'desc')
                .limit(5)
                .get();
            
            recentSearches.forEach(doc => {
                const data = doc.data();
                activities.push({
                    type: 'search',
                    title: `Consulta v2: ${data.moleculeName || 'Molécula'}`,
                    time: data.timestamp?.toDate() || new Date(),
                    icon: '🔍'
                });
            });
        } catch (err) {
            console.log('Error loading searches:', err);
        }
        
        // Sort and display
        activities.sort((a, b) => b.time - a.time);
        
        activityList.innerHTML = '';
        
        if (activities.length === 0) {
            activityList.innerHTML = '<div class="empty-state"><p>Nenhuma atividade recente</p></div>';
            return;
        }
        
        activities.slice(0, 10).forEach(activity => {
            const item = document.createElement('div');
            item.className = 'activity-item';
            item.innerHTML = `
                <div class="activity-icon ${activity.type}">
                    ${activity.icon}
                </div>
                <div class="activity-content">
                    <div class="activity-title">${activity.title}</div>
                    <div class="activity-time">${formatRelativeTime(activity.time)}</div>
                </div>
            `;
            activityList.appendChild(item);
        });
        
    } catch (error) {
        console.error('Error loading activity:', error);
    }
}

// ========== INVITES TAB ==========

async function createInvite() {
    console.log('Creating invite...');
    
    const code = document.getElementById('inviteCode').value.trim().toUpperCase();
    const limit = parseInt(document.getElementById('inviteLimit').value) || 0;
    const expiry = document.getElementById('inviteExpiry').value;
    const description = document.getElementById('inviteDescription').value.trim();
    
    if (!code) {
        alert('Por favor, insira um código!');
        return;
    }
    
    try {
        // Check if exists
        const existing = await db.collection('invites').doc(code).get();
        
        if (existing.exists) {
            alert('Este código já existe!');
            return;
        }
        
        // Create
        await db.collection('invites').doc(code).set({
            code: code,
            limit: limit,
            used: 0,
            expiry: expiry ? firebase.firestore.Timestamp.fromDate(new Date(expiry)) : null,
            description: description || '',
            active: true,
            createdBy: currentUser.email,
            createdAt: firebase.firestore.FieldValue.serverTimestamp()
        });
        
        alert('Código criado com sucesso!');
        document.getElementById('createInviteForm').reset();
        await loadInvites();
        
    } catch (error) {
        console.error('Error creating invite:', error);
        alert('Erro ao criar código: ' + error.message);
    }
}

async function loadInvites() {
    console.log('Loading invites...');
    try {
        const snapshot = await db.collection('invites')
            .orderBy('createdAt', 'desc')
            .get();
        
        const tbody = document.getElementById('invitesTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (snapshot.empty) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Nenhum código criado ainda</td></tr>';
            return;
        }
        
        snapshot.forEach(doc => {
            const invite = doc.data();
            const row = document.createElement('tr');
            
            const isExpired = invite.expiry && new Date(invite.expiry.toDate()) < new Date();
            const isLimitReached = invite.limit > 0 && invite.used >= invite.limit;
            const status = !invite.active ? 'inactive' : 
                          isExpired ? 'expired' : 
                          isLimitReached ? 'expired' : 'active';
            
            row.innerHTML = `
                <td><strong>${invite.code}</strong></td>
                <td>${invite.description || '-'}</td>
                <td>${invite.used || 0}</td>
                <td>${invite.limit === 0 ? 'Ilimitado' : invite.limit}</td>
                <td>${invite.expiry ? formatDate(invite.expiry.toDate()) : 'Nunca'}</td>
                <td><span class="status-badge status-${status}">${
                    status === 'active' ? 'Ativo' : 
                    status === 'expired' ? 'Expirado' : 'Inativo'
                }</span></td>
                <td>
                    ${invite.active ? 
                        `<button class="btn btn-danger btn-small" onclick="deactivateInvite('${doc.id}')">Desativar</button>` :
                        `<button class="btn btn-success btn-small" onclick="activateInvite('${doc.id}')">Ativar</button>`
                    }
                </td>
            `;
            tbody.appendChild(row);
        });
        
        console.log('Invites loaded');
        
    } catch (error) {
        console.error('Error loading invites:', error);
    }
}

window.deactivateInvite = async function(inviteId) {
    if (!confirm('Desativar este código?')) return;
    
    try {
        await db.collection('invites').doc(inviteId).update({ active: false });
        await loadInvites();
    } catch (error) {
        console.error('Error:', error);
        alert('Erro ao desativar código!');
    }
};

window.activateInvite = async function(inviteId) {
    try {
        await db.collection('invites').doc(inviteId).update({ active: true });
        await loadInvites();
    } catch (error) {
        console.error('Error:', error);
        alert('Erro ao ativar código!');
    }
};

// ========== USERS TAB ==========

async function loadUsers() {
    console.log('Loading users...');
    try {
        const snapshot = await db.collection('users')
            .orderBy('createdAt', 'desc')
            .get();
        
        const tbody = document.getElementById('usersTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '<tr><td colspan="9" class="loading"><div class="loading-spinner"></div></td></tr>';
        
        if (snapshot.empty) {
            tbody.innerHTML = '<tr><td colspan="9" class="empty-state">Nenhum usuário cadastrado</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        
        for (const doc of snapshot.docs) {
            const user = doc.data();
            
            // Count searches
            let totalSearches = 0;
            try {
                const searches = await db.collection('searches_v2')
                    .where('userId', '==', doc.id)
                    .get();
                totalSearches = searches.size;
            } catch (err) {
                console.log('Error counting searches:', err);
            }
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${user.name || '-'}</td>
                <td>${user.email || '-'}</td>
                <td>${user.inviteCode || '-'}</td>
                <td>${formatDate(user.createdAt?.toDate())}</td>
                <td>${user.lastAccess ? formatDate(user.lastAccess.toDate()) : 'Nunca'}</td>
                <td>${totalSearches}</td>
                <td><span class="status-badge status-active">v2</span></td>
                <td><span class="status-badge ${user.email === ADMIN_EMAIL ? 'status-expired' : 'status-active'}">
                    ${user.email === ADMIN_EMAIL ? 'admin' : 'beta_user'}
                </span></td>
                <td>
                    <button class="btn btn-primary btn-small" onclick="viewUserDetails('${doc.id}')">Detalhes</button>
                </td>
            `;
            tbody.appendChild(row);
        }
        
        console.log('Users loaded');
        
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

window.viewUserDetails = function(userId) {
    alert(`Detalhes do usuário ${userId} - Em desenvolvimento`);
};

// ========== CONTRACTS TAB ==========

async function loadContracts() {
    console.log('Loading contracts...');
    try {
        const tbody = document.getElementById('contractsTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '<tr><td colspan="7" class="loading"><div class="loading-spinner"></div></td></tr>';
        
        allContracts = [];
        
        // Load v2 searches
        try {
            const searchesV2 = await db.collection('searches_v2')
                .orderBy('timestamp', 'desc')
                .limit(50)
                .get();
            
            console.log('V2 searches found:', searchesV2.size);
            
            for (const doc of searchesV2.docs) {
                const data = doc.data();
                let userName = 'Usuário desconhecido';
                let userEmail = '-';
                
                try {
                    const user = await db.collection('users').doc(data.userId).get();
                    if (user.exists) {
                        userName = user.data().name || 'Sem nome';
                        userEmail = user.data().email || '-';
                    }
                } catch (err) {
                    console.log('Error fetching user:', err);
                }
                
                allContracts.push({
                    id: doc.id,
                    version: 'v2',
                    timestamp: data.timestamp?.toDate() || new Date(),
                    userName: userName,
                    userEmail: userEmail,
                    moleculeName: data.moleculeName || data.searchParams?.moleculeName || '-',
                    totalPatents: data.totalPatents || 0,
                    totalFamilies: data.totalFamilies || 0,
                    data: data
                });
            }
        } catch (err) {
            console.error('Error loading v2:', err);
        }
        
        // Load v1 searches
        try {
            const searchesV1 = await db.collection('searches')
                .orderBy('timestamp', 'desc')
                .limit(50)
                .get();
            
            console.log('V1 searches found:', searchesV1.size);
            
            for (const doc of searchesV1.docs) {
                const data = doc.data();
                let userName = 'Usuário desconhecido';
                let userEmail = '-';
                
                try {
                    const user = await db.collection('users').doc(data.userId).get();
                    if (user.exists) {
                        userName = user.data().name || 'Sem nome';
                        userEmail = user.data().email || '-';
                    }
                } catch (err) {
                    console.log('Error fetching user:', err);
                }
                
                allContracts.push({
                    id: doc.id,
                    version: 'v1',
                    timestamp: data.timestamp?.toDate() || new Date(),
                    userName: userName,
                    userEmail: userEmail,
                    moleculeName: data.moleculeName || data.searchParams?.moleculeName || '-',
                    totalPatents: data.totalPatents || 0,
                    totalFamilies: data.totalFamilies || 0,
                    data: data
                });
            }
        } catch (err) {
            console.error('Error loading v1:', err);
        }
        
        // Sort by timestamp
        allContracts.sort((a, b) => b.timestamp - a.timestamp);
        
        console.log('Total contracts:', allContracts.length);
        
        // Update stats
        const v1Count = allContracts.filter(c => c.version === 'v1').length;
        const v2Count = allContracts.filter(c => c.version === 'v2').length;
        
        updateElement('contractsV1', v1Count);
        updateElement('contractsV2', v2Count);
        updateElement('contractsTotal', allContracts.length);
        
        // Display
        displayContracts();
        
    } catch (error) {
        console.error('Error loading contracts:', error);
    }
}

function displayContracts() {
    const tbody = document.getElementById('contractsTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (allContracts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Nenhum contrato encontrado</td></tr>';
        return;
    }
    
    const startIndex = (currentContractsPage - 1) * contractsPerPage;
    const endIndex = startIndex + contractsPerPage;
    const pageContracts = allContracts.slice(startIndex, endIndex);
    
    pageContracts.forEach(contract => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formatDateTime(contract.timestamp)}</td>
            <td>
                <div>${contract.userName}</div>
                <small style="color: var(--text-secondary)">${contract.userEmail}</small>
            </td>
            <td><strong>${contract.moleculeName}</strong></td>
            <td>${contract.totalPatents}</td>
            <td>${contract.totalFamilies}</td>
            <td><span class="status-badge status-active">${contract.version}</span></td>
            <td>
                <button class="btn btn-primary btn-small" onclick="viewContract('${contract.id}', '${contract.version}')">Ver</button>
                <button class="btn btn-success btn-small" onclick="downloadContractPdf('${contract.id}', '${contract.version}')">PDF</button>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    updatePagination();
}

function updatePagination() {
    const totalPages = Math.ceil(allContracts.length / contractsPerPage);
    const paginationDiv = document.getElementById('contractsPagination');
    if (!paginationDiv) return;
    
    paginationDiv.innerHTML = '';
    
    if (totalPages <= 1) return;
    
    // Previous
    const prevBtn = document.createElement('button');
    prevBtn.textContent = '← Anterior';
    prevBtn.disabled = currentContractsPage === 1;
    prevBtn.addEventListener('click', () => {
        currentContractsPage--;
        displayContracts();
    });
    paginationDiv.appendChild(prevBtn);
    
    // Pages
    const startPage = Math.max(1, currentContractsPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    
    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = i === currentContractsPage ? 'active' : '';
        pageBtn.addEventListener('click', () => {
            currentContractsPage = i;
            displayContracts();
        });
        paginationDiv.appendChild(pageBtn);
    }
    
    // Next
    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'Próximo →';
    nextBtn.disabled = currentContractsPage === totalPages;
    nextBtn.addEventListener('click', () => {
        currentContractsPage++;
        displayContracts();
    });
    paginationDiv.appendChild(nextBtn);
}

window.viewContract = async function(contractId, version) {
    try {
        const collection = version === 'v1' ? 'searches' : 'searches_v2';
        const doc = await db.collection(collection).doc(contractId).get();
        
        if (!doc.exists) {
            alert('Contrato não encontrado!');
            return;
        }
        
        const data = doc.data();
        const userDoc = await db.collection('users').doc(data.userId).get();
        const user = userDoc.data() || {};
        
        const modal = document.getElementById('contractModal');
        const modalTitle = document.getElementById('contractModalTitle');
        const modalBody = document.getElementById('contractModalBody');
        
        if (modalTitle) modalTitle.textContent = `Contrato - ${data.moleculeName || 'Consulta'}`;
        
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="contract-details">
                    <h3>Informações do Usuário</h3>
                    <p><strong>Nome:</strong> ${user.name || '-'}</p>
                    <p><strong>Email:</strong> ${user.email || '-'}</p>
                    
                    <h3>Informações da Consulta</h3>
                    <p><strong>Data/Hora:</strong> ${formatDateTime(data.timestamp?.toDate())}</p>
                    <p><strong>Molécula:</strong> ${data.moleculeName || '-'}</p>
                    <p><strong>Total de Patentes:</strong> ${data.totalPatents || 0}</p>
                    <p><strong>Total de Famílias:</strong> ${data.totalFamilies || 0}</p>
                    <p><strong>Versão:</strong> ${version}</p>
                    
                    <h3>Parâmetros de Busca</h3>
                    <pre>${JSON.stringify(data.searchParams || {}, null, 2)}</pre>
                </div>
            `;
        }
        
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('active');
            modal.dataset.contractId = contractId;
            modal.dataset.contractVersion = version;
        }
        
    } catch (error) {
        console.error('Error viewing contract:', error);
        alert('Erro ao carregar contrato!');
    }
};

window.downloadContractPdf = async function(contractId, version) {
    try {
        const collection = version === 'v1' ? 'searches' : 'searches_v2';
        const doc = await db.collection(collection).doc(contractId).get();
        
        if (!doc.exists) {
            alert('Contrato não encontrado!');
            return;
        }
        
        const data = doc.data();
        const userDoc = await db.collection('users').doc(data.userId).get();
        const user = userDoc.data() || {};
        
        await generateContractPdf(data, user, version);
        
    } catch (error) {
        console.error('Error downloading PDF:', error);
        alert('Erro ao gerar PDF!');
    }
};

async function generateContractPdf(searchData, userData, version) {
    try {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        
        // Title
        doc.setFontSize(20);
        doc.text('Pharmyrus - Contrato de Consulta', 20, 20);
        
        doc.setFontSize(12);
        doc.text(`Versão: ${version}`, 170, 20);
        
        doc.setLineWidth(0.5);
        doc.line(20, 25, 190, 25);
        
        // User info
        doc.setFontSize(14);
        doc.text('Informações do Usuário', 20, 35);
        doc.setFontSize(10);
        doc.text(`Nome: ${userData.name || '-'}`, 20, 42);
        doc.text(`Email: ${userData.email || '-'}`, 20, 48);
        
        // Search info
        doc.setFontSize(14);
        doc.text('Informações da Consulta', 20, 60);
        doc.setFontSize(10);
        doc.text(`Data/Hora: ${formatDateTime(searchData.timestamp?.toDate())}`, 20, 67);
        doc.text(`Molécula: ${searchData.moleculeName || '-'}`, 20, 73);
        doc.text(`Total de Patentes: ${searchData.totalPatents || 0}`, 20, 79);
        doc.text(`Total de Famílias: ${searchData.totalFamilies || 0}`, 20, 85);
        
        // Footer
        doc.setFontSize(8);
        doc.text(`Gerado em ${formatDateTime(new Date())}`, 20, 285);
        
        // Save
        const fileName = `Pharmyrus_${version}_${searchData.moleculeName || 'Consulta'}_${Date.now()}.pdf`;
        doc.save(fileName);
        
    } catch (error) {
        console.error('Error generating PDF:', error);
        alert('Erro ao gerar PDF: ' + error.message);
    }
}

function closeContractModal() {
    const modal = document.getElementById('contractModal');
    if (modal) {
        modal.classList.remove('active');
        modal.classList.add('hidden');
    }
}

// ========== STATS TAB ==========

async function loadStats() {
    console.log('Loading stats...');
    alert('Estatísticas em desenvolvimento!');
}

// ========== HELPER FUNCTIONS ==========

function updateElement(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function formatDate(date) {
    if (!date) return '-';
    try {
        return date.toLocaleDateString('pt-BR');
    } catch {
        return '-';
    }
}

function formatDateTime(date) {
    if (!date) return '-';
    try {
        return date.toLocaleString('pt-BR');
    } catch {
        return '-';
    }
}

function formatRelativeTime(date) {
    if (!date) return '-';
    
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'Agora';
    if (minutes < 60) return `${minutes}m atrás`;
    if (hours < 24) return `${hours}h atrás`;
    return `${days}d atrás`;
}

console.log('Admin.js fully loaded');
