import httpx
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import random
import time

from app.parser import PatentScopeParser


class PatentScopeScraper:
    """Scraper assíncrono para WIPO PatentScope - Busca por molécula"""
    
    BASE_URL = "https://patentscope.wipo.int"
    SEARCH_URL = f"{BASE_URL}/search/en/result.jsf"
    
    def __init__(self):
        self.parser = PatentScopeParser()
        self.session: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Context manager entry"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self.session = httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
            verify=False  # Alguns sites tem problemas com SSL
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.aclose()
    
    async def _fetch_with_retry(
        self, 
        url: str, 
        params: Optional[Dict] = None,
        max_retries: int = 3
    ) -> str:
        """
        Faz requisição HTTP com retry e backoff
        
        Args:
            url: URL para requisição
            params: Parâmetros query
            max_retries: Número máximo de tentativas
            
        Returns:
            HTML da resposta
        """
        for attempt in range(max_retries):
            try:
                # Delay aleatório para parecer humano
                if attempt > 0:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                
                response = await self.session.get(url, params=params)
                
                if response.status_code == 200:
                    return response.text
                
                elif response.status_code == 429:
                    # Rate limited
                    await asyncio.sleep(5)
                    continue
                
                elif response.status_code >= 500:
                    # Erro no servidor, tentar novamente
                    continue
                
                else:
                    response.raise_for_status()
            
            except httpx.TimeoutException:
                if attempt == max_retries - 1:
                    raise Exception("Timeout na requisição")
                continue
            
            except httpx.HTTPError as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Erro HTTP: {str(e)}")
                continue
        
        raise Exception(f"Falha ao buscar {url} após {max_retries} tentativas")
    
    def _build_molecule_query(self, molecule: str, search_type: str = "exact") -> str:
        """
        Constrói query para busca de molécula
        
        Args:
            molecule: Fórmula molecular, SMILES ou nome
            search_type: Tipo de busca
            
        Returns:
            Query formatada
        """
        # Limpar molécula
        molecule = molecule.strip()
        
        # Detectar tipo de entrada
        if all(c in '0123456789CHONPS()[]+-=' for c in molecule.replace(' ', '')):
            # Provavelmente fórmula molecular
            query_field = "EN_AB"  # Abstract
            query = f'"{molecule}"'
        
        elif any(c in molecule for c in ['@', '/', '\\']):
            # Provavelmente SMILES
            query_field = "EN_AB"
            query = f'"{molecule}"'
        
        else:
            # Nome da molécula
            query_field = "EN_ALL"
            query = molecule
        
        # Adicionar termos relacionados a química
        chemistry_terms = [
            "compound",
            "molecule",
            "chemical",
            "synthesis",
            "composition"
        ]
        
        # Query expandida
        expanded_query = f"{query_field}:({query})"
        
        return expanded_query
    
    async def search_by_molecule(
        self,
        molecule: str,
        search_type: str = "exact",
        page: int = 1,
        page_size: int = 10
    ) -> Dict:
        """
        Busca patentes por molécula
        
        Args:
            molecule: Fórmula molecular, SMILES ou nome
            search_type: Tipo de busca (exact, similarity, substructure)
            page: Número da página
            page_size: Resultados por página
            
        Returns:
            Dicionário com resultados e metadados
        """
        start_time = time.time()
        
        # Construir query
        query = self._build_molecule_query(molecule, search_type)
        
        # Calcular offset para paginação
        start_rec = (page - 1) * page_size + 1
        
        # Parâmetros de busca do PatentScope
        # Nota: PatentScope usa JSF com sessão server-side
        # Esta é uma aproximação - pode precisar ajustar
        params = {
            'query': query,
            'office': 'all',
            'sortOption': 'Relevance',
            'maxRec': page_size,
            'startRec': start_rec,
        }
        
        try:
            # Fazer requisição
            html = await self._fetch_with_retry(self.SEARCH_URL, params)
            
            # Parsear resultados
            results = self.parser.parse_search_results(html)
            total_results = self.parser.extract_total_results(html)
            
            # Se não encontrou total, usar tamanho dos resultados
            if total_results == 0 and results:
                total_results = len(results)
            
            # Calcular paginação
            total_pages = max(1, (total_results + page_size - 1) // page_size)
            
            # Adicionar URLs aos resultados
            for result in results:
                if 'patent_id' in result:
                    result['url'] = f"{self.BASE_URL}/search/en/detail.jsf?docId={result['patent_id']}"
                else:
                    result['url'] = self.BASE_URL
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'success',
                'results': results,
                'total_results': total_results,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_previous': page > 1,
                'next_page': page + 1 if page < total_pages else None,
                'previous_page': page - 1 if page > 1 else None,
                'query': molecule,
                'search_type': search_type,
                'duration_ms': duration_ms,
                'scraped_at': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'results': [],
                'total_results': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0,
                'has_next': False,
                'has_previous': False,
                'query': molecule,
                'search_type': search_type
            }
    
    async def get_patent_details(self, patent_id: str) -> Dict:
        """
        Obtém detalhes de uma patente específica
        
        Args:
            patent_id: ID da patente
            
        Returns:
            Dicionário com detalhes da patente
        """
        detail_url = f"{self.BASE_URL}/search/en/detail.jsf"
        params = {'docId': patent_id}
        
        try:
            html = await self._fetch_with_retry(detail_url, params)
            patent = self.parser.parse_patent_detail(html)
            patent['patent_id'] = patent_id
            patent['url'] = f"{detail_url}?docId={patent_id}"
            return patent
        
        except Exception as e:
            return {
                'error': str(e),
                'patent_id': patent_id
            }
