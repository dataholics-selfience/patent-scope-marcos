# config_patentscope.py
"""
Configurações para o PatentScope Scraper (WIPO - World Intellectual Property Organization)
"""

import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PatentScopeConfig:
    """Configurações principais do PatentScope"""

    # Base URLs
    BASE_URL: str = "https://patentscope.wipo.int"
    API_BASE_URL: str = "https://patentscope.wipo.int/search/en"
    REST_API_URL: str = "https://patentscope.wipo.int/search/rest/search"

    # API Endpoints
    SEARCH_ENDPOINT: str = "/search/rest/search"
    DETAIL_ENDPOINT: str = "/search/rest/detail"

    # Rate Limiting
    MIN_DELAY: float = 1.0
    MAX_DELAY: float = 3.0
    ADAPTIVE_DELAY: bool = True

    # Retry Logic
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_MULTIPLIER: float = 2.0
    RETRY_MIN_WAIT: int = 2
    RETRY_MAX_WAIT: int = 10

    # Timeouts
    REQUEST_TIMEOUT: int = 30

    # Pagination
    DEFAULT_PAGE_SIZE: int = 100
    MAX_PAGE_SIZE: int = 500

    # Query Parameters
    DEFAULT_QUERY_FORMAT: str = "ADVANCED"  # SIMPLE or ADVANCED
    DEFAULT_SORT: str = "DP"  # DP = Data de Publicação (Publication Date)
    DEFAULT_LANGUAGE: str = "en"  # en, fr, es, de, pt, etc.

    # Search Fields (campos de busca)
    SEARCH_FIELDS = {
        'all': 'FP',           # Full Patent (todos os campos)
        'title': 'TI',         # Title (Título)
        'abstract': 'AB',      # Abstract (Resumo)
        'claims': 'CL',        # Claims (Reivindicações)
        'description': 'DE',   # Description (Descrição)
        'inventor': 'IN',      # Inventor (Inventor)
        'applicant': 'PA',     # Applicant (Depositante)
        'ipc': 'IC',           # IPC Classification (Classificação IPC)
        'cpc': 'CP',           # CPC Classification (Classificação CPC)
        'priority': 'PR',      # Priority Number (Número de Prioridade)
        'publication': 'PN',   # Publication Number (Número de Publicação)
        'application': 'AN',   # Application Number (Número de Aplicação)
    }

    # Data Fields to Extract (campos para extrair)
    EXTRACT_FIELDS = [
        'applicationNumber',
        'publicationNumber',
        'publicationDate',
        'applicationDate',
        'title',
        'abstract',
        'inventors',
        'applicants',
        'ipcClassifications',
        'cpcClassifications',
        'priorityNumber',
        'priorityDate',
        'nationalPhase',
        'pctNumber',
        'filingLanguage',
    ]

    # Configurações de salvamento
    CHUNK_SIZE: int = 100
    BACKUP_ENABLED: bool = True

    # Compliance
    RESPECT_RATE_LIMITS: bool = True
    CHECK_RATE_LIMITS: bool = True

@dataclass
class PatentScopeAuthConfig:
    """Configurações de autenticação para PatentScope"""

    # WIPO PatentScope Credentials
    USERNAME: Optional[str] = os.getenv('WIPO_USERNAME', None)
    PASSWORD: Optional[str] = os.getenv('WIPO_PASSWORD', None)
    LOGIN_URL: str = os.getenv('WIPO_LOGIN_URL', 'https://www.wipo.int/portal/en/')
    SEARCH_URL: str = os.getenv('WIPO_SEARCH_URL', 'https://patentscope.wipo.int/search/pt/search.jsf')

    # Login required for full access
    LOGIN_REQUIRED: bool = True
    SESSION_TIMEOUT: int = 3600  # 1 hora em segundos

    # Rate limits
    ANONYMOUS_RATE_LIMIT: int = 100  # Requisições por minuto para usuários anônimos
    AUTHENTICATED_RATE_LIMIT: int = 300  # Requisições por minuto para usuários autenticados

@dataclass
class PatentScopeLoggingConfig:
    """Configurações de logging"""

    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = "patentscope_scraper.log"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5

@dataclass
class PatentScopeValidationConfig:
    """Configurações de validação"""

    # Campos obrigatórios
    REQUIRED_PATENT_FIELDS: List[str] = None

    # Tamanhos mínimos
    MIN_TITLE_LENGTH: int = 5
    MIN_ABSTRACT_LENGTH: int = 10

    def __post_init__(self):
        if self.REQUIRED_PATENT_FIELDS is None:
            self.REQUIRED_PATENT_FIELDS = ['publicationNumber', 'title']

# Códigos de países e regiões suportados pelo PatentScope
COUNTRY_CODES = {
    'BR': 'Brazil',
    'US': 'United States',
    'EP': 'European Patent Office',
    'WO': 'PCT International',
    'CN': 'China',
    'JP': 'Japan',
    'KR': 'Korea',
    'GB': 'United Kingdom',
    'DE': 'Germany',
    'FR': 'France',
    'CA': 'Canada',
    'AU': 'Australia',
    'IN': 'India',
    'RU': 'Russia',
}

# Instâncias globais das configurações
PATENTSCOPE_CONFIG = PatentScopeConfig()
PATENTSCOPE_AUTH_CONFIG = PatentScopeAuthConfig()
PATENTSCOPE_LOGGING_CONFIG = PatentScopeLoggingConfig()
PATENTSCOPE_VALIDATION_CONFIG = PatentScopeValidationConfig()

# Configurações específicas por ambiente
ENVIRONMENT = os.getenv('SCRAPER_ENV', 'production')

if ENVIRONMENT == 'development':
    PATENTSCOPE_CONFIG.MIN_DELAY = 0.5
    PATENTSCOPE_CONFIG.MAX_DELAY = 1.0
    PATENTSCOPE_LOGGING_CONFIG.LOG_LEVEL = "DEBUG"

elif ENVIRONMENT == 'testing':
    PATENTSCOPE_CONFIG.MIN_DELAY = 0.1
    PATENTSCOPE_CONFIG.MAX_DELAY = 0.5
    PATENTSCOPE_CONFIG.CHUNK_SIZE = 10
    PATENTSCOPE_CONFIG.RESPECT_RATE_LIMITS = False

elif ENVIRONMENT == 'production':
    PATENTSCOPE_CONFIG.MIN_DELAY = 1.0
    PATENTSCOPE_CONFIG.MAX_DELAY = 3.0
    PATENTSCOPE_CONFIG.BACKUP_ENABLED = True
