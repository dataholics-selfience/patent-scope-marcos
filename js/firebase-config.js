// Firebase Configuration
// Configuração correta do projeto Pharmyrus
const firebaseConfig = {
    apiKey: "AIzaSyAHq5Tvn3qZvbj1D2GJdUW-BhPWiAURBJI",
    authDomain: "patentes-51d85.firebaseapp.com",
    projectId: "patentes-51d85",
    storageBucket: "patentes-51d85.firebasestorage.app",
    messagingSenderId: "278792677855",
    appId: "1:278792677855:web:a801a4894efe7aa1bbbc6a"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Initialize services
const auth = firebase.auth();
const db = firebase.firestore();

// Códigos de convite válidos para beta
const VALID_INVITE_CODES = [
    'PHARMYRUS2025',
    'BETA2025',
    'WIPO2025'
];

// Email do admin com acesso total
const ADMIN_EMAIL = 'daniel.mendes@dataholics.io';

// Collections names - separadas do projeto v1
const COLLECTIONS = {
    users: 'users', // Mesma collection de usuários
    searches_v2: 'searches_v2', // Nova collection para o v2
    invites: 'invites', // Códigos de convite
    usage_stats_v2: 'usage_stats_v2' // Nova collection para estatísticas do v2
};
