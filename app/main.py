from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.models import (
    MoleculeSearchRequest,
    SearchResponse,
    ErrorResponse,
    HealthResponse,
    PatentResult,
    PaginationInfo
)
from app.scraper import PatentScopeScraper

# Version
VERSION = "1.0.0"

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento de recursos da aplicação"""
    print(f"🚀 Starting Patent Scraper API v{VERSION}")
    print(f"📡 Port: {os.getenv('PORT', '8000')}")
    yield
    print("👋 Shutting down...")

# Inicializar FastAPI
app = FastAPI(
    title="Patent Scraper API - Molecule Search",
    version=VERSION,
    description="""
    # 🧪 API para Busca de Patentes por Molécula
    
    Busque patentes no WIPO PatentScope usando:
    - Fórmula molecular (ex: C6H12O6)
    - SMILES
    - Nome da molécula (ex: "glucose")
    
    ## 📖 Endpoints
    
    - **POST /search** - Buscar patentes por molécula
    - **GET /patent/{patent_id}** - Detalhes de patente específica
    - **GET /health** - Health check
    
    ## 🔍 Paginação
    
    Use os parâmetros `page` e `page_size` para navegar pelos resultados.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler para HTTPException"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=f"HTTP {exc.status_code}",
            message=exc.detail
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler para exceções gerais"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            message=str(exc)
        ).dict()
    )

# ==================== ENDPOINTS ====================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - redirect para docs"""
    return {
        "message": "Patent Scraper API - Molecule Search",
        "version": VERSION,
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version=VERSION
    )

@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_molecule(search_request: MoleculeSearchRequest):
    """
    Busca patentes por molécula
    
    ## Parâmetros
    
    - **molecule**: Fórmula molecular, SMILES ou nome da molécula
    - **search_type**: Tipo de busca (exact, similarity, substructure)
    - **page**: Número da página (padrão: 1)
    - **page_size**: Resultados por página (padrão: 10, máx: 100)
    
    ## Exemplo de Request
    
    ```json
    {
        "molecule": "C6H12O6",
        "search_type": "exact",
        "page": 1,
        "page_size": 10
    }
    ```
    
    ## Exemplo de Uso via cURL
    
    ```bash
    curl -X POST "http://localhost:8000/search" \\
      -H "Content-Type: application/json" \\
      -d '{"molecule": "aspirin", "page": 1, "page_size": 10}'
    ```
    """
    try:
        async with PatentScopeScraper() as scraper:
            result = await scraper.search_by_molecule(
                molecule=search_request.molecule,
                search_type=search_request.search_type,
                page=search_request.page,
                page_size=search_request.page_size
            )
        
        if result.get('status') == 'error':
            raise HTTPException(
                status_code=500, 
                detail=result.get('error', 'Unknown error')
            )
        
        # Formatar resultados
        patent_results = [
            PatentResult(
                patent_id=r.get('patent_id', ''),
                publication_number=r.get('publication_number', ''),
                title=r.get('title', 'No title'),
                abstract=r.get('abstract'),
                applicants=r.get('applicants', []),
                inventors=r.get('inventors', []),
                publication_date=r.get('publication_date'),
                ipc_codes=r.get('ipc_codes', []),
                url=r.get('url', ''),
                relevance_score=None
            )
            for r in result.get('results', [])
        ]
        
        pagination = PaginationInfo(
            current_page=result.get('page', 1),
            page_size=result.get('page_size', 10),
            total_results=result.get('total_results', 0),
            total_pages=result.get('total_pages', 0),
            has_next=result.get('has_next', False),
            has_previous=result.get('has_previous', False),
            next_page=result.get('next_page'),
            previous_page=result.get('previous_page')
        )
        
        return SearchResponse(
            status="success",
            query=search_request.molecule,
            results=patent_results,
            pagination=pagination,
            metadata={
                "search_type": search_request.search_type,
                "duration_ms": result.get('duration_ms', 0),
                "scraped_at": result.get('scraped_at', ''),
                "source": "WIPO PatentScope"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/patent/{patent_id}", tags=["Patents"])
async def get_patent_details(patent_id: str):
    """
    Obtém detalhes completos de uma patente
    
    ## Parâmetros
    
    - **patent_id**: ID da patente (ex: WO2023026103)
    
    ## Exemplo de Uso
    
    ```bash
    curl "http://localhost:8000/patent/WO2023026103"
    ```
    """
    try:
        async with PatentScopeScraper() as scraper:
            patent = await scraper.get_patent_details(patent_id)
        
        if 'error' in patent:
            raise HTTPException(
                status_code=404, 
                detail=f"Patent not found: {patent_id}"
            )
        
        return {
            "status": "success",
            "patent": patent
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch patent details: {str(e)}"
        )

@app.get("/stats", tags=["Statistics"])
async def get_stats():
    """Estatísticas da API (placeholder)"""
    return {
        "status": "operational",
        "version": VERSION,
        "endpoints": {
            "search": "/search",
            "patent_details": "/patent/{patent_id}",
            "health": "/health"
        }
    }

@app.post("/search/mock", response_model=SearchResponse, tags=["Search"])
async def search_mock(search_request: MoleculeSearchRequest):
    """
    Endpoint MOCK para testar sem scraping real
    Retorna dados fake para debug
    """
    import random
    
    # Criar resultados fake
    fake_results = [
        PatentResult(
            patent_id=f"WO2023{random.randint(100000, 999999)}",
            publication_number=f"WO2023{random.randint(100000, 999999)}A1",
            title=f"Patent about {search_request.molecule} - Result {i+1}",
            abstract=f"This invention relates to {search_request.molecule} and its applications...",
            applicants=[f"Company {chr(65+i)}"],
            inventors=[f"Dr. John Doe {i+1}"],
            publication_date="2023-06-29",
            ipc_codes=["A61K31/00"],
            url=f"https://patentscope.wipo.int/search/en/detail.jsf?docId=WO2023{random.randint(100000, 999999)}",
            relevance_score=0.95 - (i * 0.1)
        )
        for i in range(min(search_request.page_size, 5))
    ]
    
    total_fake = 50  # Total fake de resultados
    
    pagination = PaginationInfo(
        current_page=search_request.page,
        page_size=search_request.page_size,
        total_results=total_fake,
        total_pages=(total_fake + search_request.page_size - 1) // search_request.page_size,
        has_next=search_request.page < 10,
        has_previous=search_request.page > 1,
        next_page=search_request.page + 1 if search_request.page < 10 else None,
        previous_page=search_request.page - 1 if search_request.page > 1 else None
    )
    
    return SearchResponse(
        status="success",
        query=search_request.molecule,
        results=fake_results,
        pagination=pagination,
        metadata={
            "search_type": "MOCK - Fake data for testing",
            "duration_ms": 10,
            "scraped_at": datetime.utcnow().isoformat(),
            "source": "MOCK API"
        }
    )

# Para desenvolvimento local
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
