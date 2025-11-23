// Patent Cliff Calculator
// Calcula quando as patentes mais importantes irão expirar

/**
 * Calculate patent cliff - the next patent expiration date
 * @param {Array} patents - Array of patent objects
 * @returns {string} - Formatted cliff date or message
 */
function calculatePatentCliff(patents) {
    if (!patents || patents.length === 0) {
        return 'N/A';
    }
    
    const now = new Date();
    const activePatents = patents.filter(p => {
        const expiryDate = p.expiry_date ? new Date(p.expiry_date) : null;
        const isActive = p.legal_status === 'Active' || p.legal_status === 'Granted';
        return expiryDate && isActive && expiryDate > now;
    });
    
    if (activePatents.length === 0) {
        return 'Todas expiradas';
    }
    
    // Find the next expiring patent
    activePatents.sort((a, b) => {
        const dateA = new Date(a.expiry_date);
        const dateB = new Date(b.expiry_date);
        return dateA - dateB;
    });
    
    const nextExpiring = activePatents[0];
    const expiryDate = new Date(nextExpiring.expiry_date);
    
    // Calculate years until expiration
    const yearsUntilExpiry = (expiryDate - now) / (1000 * 60 * 60 * 24 * 365.25);
    
    if (yearsUntilExpiry < 1) {
        const months = Math.floor((expiryDate - now) / (1000 * 60 * 60 * 24 * 30));
        return `${months} ${months === 1 ? 'mês' : 'meses'}`;
    } else {
        const years = Math.floor(yearsUntilExpiry);
        return `${years} ${years === 1 ? 'ano' : 'anos'}`;
    }
}

/**
 * Get detailed patent cliff analysis
 * @param {Array} patents - Array of patent objects
 * @returns {Object} - Detailed cliff analysis
 */
function getPatentCliffAnalysis(patents) {
    if (!patents || patents.length === 0) {
        return {
            nextCliff: null,
            upcomingExpirations: [],
            totalActive: 0,
            criticalPeriod: false
        };
    }
    
    const now = new Date();
    const activePatents = patents.filter(p => {
        const expiryDate = p.expiry_date ? new Date(p.expiry_date) : null;
        const isActive = p.legal_status === 'Active' || p.legal_status === 'Granted';
        return expiryDate && isActive && expiryDate > now;
    });
    
    // Sort by expiry date
    activePatents.sort((a, b) => {
        const dateA = new Date(a.expiry_date);
        const dateB = new Date(b.expiry_date);
        return dateA - dateB;
    });
    
    // Get patents expiring in the next 5 years
    const fiveYearsFromNow = new Date(now.getTime() + (5 * 365.25 * 24 * 60 * 60 * 1000));
    const upcomingExpirations = activePatents.filter(p => {
        const expiryDate = new Date(p.expiry_date);
        return expiryDate <= fiveYearsFromNow;
    });
    
    // Check if we're in a critical period (multiple patents expiring within 2 years)
    const twoYearsFromNow = new Date(now.getTime() + (2 * 365.25 * 24 * 60 * 60 * 1000));
    const criticalExpirations = activePatents.filter(p => {
        const expiryDate = new Date(p.expiry_date);
        return expiryDate <= twoYearsFromNow;
    });
    
    return {
        nextCliff: activePatents.length > 0 ? {
            patent: activePatents[0],
            expiryDate: activePatents[0].expiry_date,
            yearsUntil: (new Date(activePatents[0].expiry_date) - now) / (1000 * 60 * 60 * 24 * 365.25)
        } : null,
        upcomingExpirations: upcomingExpirations.map(p => ({
            publicationNumber: p.publication_number,
            title: p.title,
            expiryDate: p.expiry_date,
            yearsUntil: (new Date(p.expiry_date) - now) / (1000 * 60 * 60 * 24 * 365.25),
            type: p.patent_type,
            jurisdiction: p.jurisdiction
        })),
        totalActive: activePatents.length,
        criticalPeriod: criticalExpirations.length >= 3
    };
}

/**
 * Get patent timeline for visualization
 * @param {Array} patents - Array of patent objects
 * @returns {Array} - Timeline data
 */
function getPatentTimeline(patents) {
    if (!patents || patents.length === 0) {
        return [];
    }
    
    const now = new Date();
    const activePatents = patents.filter(p => {
        const expiryDate = p.expiry_date ? new Date(p.expiry_date) : null;
        const isActive = p.legal_status === 'Active' || p.legal_status === 'Granted';
        return expiryDate && isActive && expiryDate > now;
    });
    
    // Group by year
    const timeline = {};
    activePatents.forEach(patent => {
        const expiryYear = new Date(patent.expiry_date).getFullYear();
        if (!timeline[expiryYear]) {
            timeline[expiryYear] = [];
        }
        timeline[expiryYear].push({
            publicationNumber: patent.publication_number,
            title: patent.title,
            type: patent.patent_type,
            jurisdiction: patent.jurisdiction
        });
    });
    
    // Convert to sorted array
    return Object.keys(timeline).sort().map(year => ({
        year: parseInt(year),
        count: timeline[year].length,
        patents: timeline[year]
    }));
}

/**
 * Calculate protection coverage score
 * Based on number and distribution of active patents
 * @param {Array} patents - Array of patent objects
 * @returns {Object} - Coverage analysis
 */
function calculateProtectionCoverage(patents) {
    if (!patents || patents.length === 0) {
        return {
            score: 0,
            level: 'Nenhuma',
            details: 'Nenhuma patente ativa encontrada'
        };
    }
    
    const now = new Date();
    const activePatents = patents.filter(p => {
        const expiryDate = p.expiry_date ? new Date(p.expiry_date) : null;
        const isActive = p.legal_status === 'Active' || p.legal_status === 'Granted';
        return expiryDate && isActive && expiryDate > now;
    });
    
    // Calculate score based on multiple factors
    let score = 0;
    
    // Factor 1: Number of active patents (max 40 points)
    score += Math.min(activePatents.length * 4, 40);
    
    // Factor 2: Geographic coverage (max 30 points)
    const jurisdictions = [...new Set(activePatents.map(p => p.jurisdiction).filter(Boolean))];
    const keyMarkets = ['BR', 'US', 'EP', 'CN', 'JP'];
    const keyMarketCoverage = keyMarkets.filter(market => jurisdictions.includes(market)).length;
    score += keyMarketCoverage * 6;
    
    // Factor 3: Patent type diversity (max 20 points)
    const types = [...new Set(activePatents.map(p => p.patent_type).filter(Boolean))];
    score += Math.min(types.length * 5, 20);
    
    // Factor 4: Time until next cliff (max 10 points)
    const sortedPatents = activePatents.sort((a, b) => {
        return new Date(a.expiry_date) - new Date(b.expiry_date);
    });
    if (sortedPatents.length > 0) {
        const yearsToCliff = (new Date(sortedPatents[0].expiry_date) - now) / (1000 * 60 * 60 * 24 * 365.25);
        score += Math.min(yearsToCliff, 10);
    }
    
    // Determine protection level
    let level, details;
    if (score >= 80) {
        level = 'Excelente';
        details = 'Proteção robusta com cobertura ampla';
    } else if (score >= 60) {
        level = 'Boa';
        details = 'Proteção sólida mas pode ser melhorada';
    } else if (score >= 40) {
        level = 'Moderada';
        details = 'Proteção básica com lacunas significativas';
    } else if (score >= 20) {
        level = 'Fraca';
        details = 'Proteção limitada, vulnerável';
    } else {
        level = 'Muito Fraca';
        details = 'Proteção inadequada';
    }
    
    return {
        score: Math.round(score),
        level,
        details,
        activePatents: activePatents.length,
        jurisdictions: jurisdictions.length,
        types: types.length
    };
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        calculatePatentCliff,
        getPatentCliffAnalysis,
        getPatentTimeline,
        calculateProtectionCoverage
    };
}
