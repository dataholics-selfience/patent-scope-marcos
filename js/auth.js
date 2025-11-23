// Auth.js - Authentication logic

// DOM Elements
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const loginFormElement = document.getElementById('loginFormElement');
const registerFormElement = document.getElementById('registerFormElement');
const showRegisterBtn = document.getElementById('showRegister');
const showLoginBtn = document.getElementById('showLogin');
const messageDiv = document.getElementById('message');

// Switch between login and register forms
showRegisterBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    loginForm.classList.add('hidden');
    registerForm.classList.remove('hidden');
    clearMessage();
});

showLoginBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    registerForm.classList.add('hidden');
    loginForm.classList.remove('hidden');
    clearMessage();
});

// Login
loginFormElement?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        await auth.signInWithEmailAndPassword(email, password);
        showMessage('Login realizado com sucesso!', 'success');
        
        // Redirect to dashboard
        setTimeout(() => {
            window.location.href = 'dashboard.html';
        }, 1000);
    } catch (error) {
        console.error('Login error:', error);
        showMessage(getErrorMessage(error.code), 'error');
    }
});

// Register
registerFormElement?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('registerName').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const inviteCode = document.getElementById('inviteCode').value;
    
    // Validate invite code
    if (!VALID_INVITE_CODES.includes(inviteCode.toUpperCase())) {
        showMessage('Código de convite inválido!', 'error');
        return;
    }
    
    // Validate password length
    if (password.length < 6) {
        showMessage('A senha deve ter pelo menos 6 caracteres!', 'error');
        return;
    }
    
    try {
        // Create user
        const userCredential = await auth.createUserWithEmailAndPassword(email, password);
        const user = userCredential.user;
        
        // Update profile
        await user.updateProfile({
            displayName: name
        });
        
        // Save user data to Firestore (mesma collection de usuários do v1)
        await db.collection(COLLECTIONS.users).doc(user.uid).set({
            name: name,
            email: email,
            createdAt: firebase.firestore.FieldValue.serverTimestamp(),
            inviteCode: inviteCode.toUpperCase(),
            role: 'beta_user',
            version: 'v2'
        });
        
        showMessage('Cadastro realizado com sucesso!', 'success');
        
        // Redirect to dashboard
        setTimeout(() => {
            window.location.href = 'dashboard.html';
        }, 1000);
    } catch (error) {
        console.error('Registration error:', error);
        showMessage(getErrorMessage(error.code), 'error');
    }
});

// Auth state observer
auth.onAuthStateChanged((user) => {
    if (user && window.location.pathname.includes('dashboard.html')) {
        // User is signed in and on dashboard - this is correct
        return;
    } else if (user && window.location.pathname.includes('index.html')) {
        // User is signed in but on login page - redirect to dashboard
        window.location.href = 'dashboard.html';
    } else if (!user && window.location.pathname.includes('dashboard.html')) {
        // User is not signed in but on dashboard - redirect to login
        window.location.href = 'index.html';
    }
});

// Helper functions
function showMessage(message, type) {
    messageDiv.textContent = message;
    messageDiv.className = `message ${type}`;
    messageDiv.classList.remove('hidden');
}

function clearMessage() {
    messageDiv.className = 'message hidden';
    messageDiv.textContent = '';
}

function getErrorMessage(errorCode) {
    const errorMessages = {
        'auth/email-already-in-use': 'Este email já está cadastrado!',
        'auth/invalid-email': 'Email inválido!',
        'auth/user-not-found': 'Usuário não encontrado!',
        'auth/wrong-password': 'Senha incorreta!',
        'auth/weak-password': 'Senha muito fraca!',
        'auth/too-many-requests': 'Muitas tentativas. Tente novamente mais tarde.',
        'auth/network-request-failed': 'Erro de conexão. Verifique sua internet.'
    };
    
    return errorMessages[errorCode] || 'Erro ao processar. Tente novamente.';
}
