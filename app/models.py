from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class MoleculeSearchRequest(BaseModel):
    """Request para busca por molécula"""
    molecule: str = Field(
        ..., 
        min_length=2, 
        max_length=500,
        description="Fórmula molecular, SMILES, ou nome da molécula"
    )
    search_type: str = Field(
        "exact",
        description="Tipo de busca: 'exact', 'similarity', 'substructure'"
    )
    page: int = Field(1, ge=1, le=1000)
    page_size: int = Field(10, ge=1, le=100)
    
    @validator('molecule')
    def validate_molecule(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Molécula não pode ser vazia")
        # Remover caracteres perigosos
        dangerous = ['<', '>', 'script', 'javascript']
        if any(d in v.lower() for d in dangerous):
            raise ValueError("Molécula contém caracteres inválidos")
        return v.strip()


class PatentResult(BaseModel):
    """Resultado individual de patente"""
    patent_id: str
    publication_number: str
    title: str
    abstract: Optional[str] = None
    applicants: List[str] = []
    inventors: List[str] = []
    publication_date: Optional[str] = None
    ipc_codes: List[str] = []
    url: str
    relevance_score: Optional[float] = None


class PaginationInfo(BaseModel):
    """Informações de paginação"""
    current_page: int
    page_size: int
    total_results: int
    total_pages: int
    has_next: bool
    has_previous: bool
    next_page: Optional[int] = None
    previous_page: Optional[int] = None


class SearchResponse(BaseModel):
    """Resposta completa de busca"""
    status: str = "success"
    query: str
    results: List[PatentResult]
    pagination: PaginationInfo
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Resposta de erro"""
    status: str = "error"
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
