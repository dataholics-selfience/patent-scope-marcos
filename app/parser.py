from parsel import Selector
from typing import List, Dict, Optional
import re
from datetime import datetime


class PatentScopeParser:
    """Parser robusto para WIPO PatentScope usando Parsel/Grok"""
    
    @staticmethod
    def parse_search_results(html: str) -> List[Dict]:
        """
        Extrai resultados de busca usando múltiplos seletores (tags mudam)
        
        Args:
            html: HTML da página de resultados
            
        Returns:
            Lista de dicionários com dados das patentes
        """
        selector = Selector(text=html)
        results = []
        
        # PatentScope pode usar várias estruturas - testar todas
        result_selectors = [
            '.result-item',
            '.patent-result', 
            'tr.data-row',
            'div[class*="result"]',
            'tr[class*="row"]',
            'div[id*="result"]',
            '.resultSet > div',
            'table.resultTable tr',
        ]
        
        items = []
        for sel in result_selectors:
            items = selector.css(sel)
            if items:
                break
        
        for item in items:
            try:
                result = {}
                
                # Número de publicação - múltiplos seletores
                pub_selectors = [
                    '.publication-number::text',
                    '.pub-number::text',
                    'a[href*="docId"]::text',
                    '.docId::text',
                    'td.number::text',
                    'span[class*="number"]::text',
                ]
                
                pub_number = None
                for sel in pub_selectors:
                    pub_number = item.css(sel).get()
                    if pub_number:
                        break
                
                if not pub_number:
                    # Tentar XPath
                    pub_number = item.xpath('.//text()[contains(., "WO") or contains(., "US") or contains(., "EP")]').get()
                
                if pub_number:
                    result['publication_number'] = pub_number.strip()
                
                # Extrair docId da URL
                href = item.css('a[href*="docId"]::attr(href)').get()
                if href:
                    doc_id_match = re.search(r'docId=([^&\s]+)', href)
                    if doc_id_match:
                        result['patent_id'] = doc_id_match.group(1)
                
                # Se não tiver patent_id, usar publication_number
                if 'patent_id' not in result and 'publication_number' in result:
                    result['patent_id'] = result['publication_number']
                
                # Título - múltiplos seletores
                title_selectors = [
                    '.title::text',
                    'h3::text',
                    '.patent-title::text',
                    'a[href*="docId"]::text',
                    'td.title::text',
                    'div[class*="title"]::text',
                ]
                
                title = None
                for sel in title_selectors:
                    title = item.css(sel).get()
                    if title:
                        break
                
                if title:
                    result['title'] = title.strip()
                
                # Abstract/Resumo
                abstract_selectors = [
                    '.abstract::text',
                    '.summary::text',
                    'div[class*="abstract"]::text',
                    'td.abstract::text',
                ]
                
                abstract_parts = []
                for sel in abstract_selectors:
                    parts = item.css(sel).getall()
                    if parts:
                        abstract_parts.extend(parts)
                
                if abstract_parts:
                    result['abstract'] = ' '.join(abstract_parts).strip()
                
                # Requerentes/Applicants
                applicant_selectors = [
                    '.applicant::text',
                    '.applicant-name::text',
                    'div[class*="applicant"]::text',
                    'td.applicant::text',
                ]
                
                applicants = []
                for sel in applicant_selectors:
                    apps = item.css(sel).getall()
                    if apps:
                        applicants.extend(apps)
                
                result['applicants'] = [a.strip() for a in applicants if a.strip()]
                
                # Inventores
                inventor_selectors = [
                    '.inventor::text',
                    '.inventor-name::text',
                    'div[class*="inventor"]::text',
                ]
                
                inventors = []
                for sel in inventor_selectors:
                    invs = item.css(sel).getall()
                    if invs:
                        inventors.extend(invs)
                
                result['inventors'] = [i.strip() for i in inventors if i.strip()]
                
                # Data de publicação
                date_selectors = [
                    '.publication-date::text',
                    '.pub-date::text',
                    'td.date::text',
                    'span[class*="date"]::text',
                ]
                
                pub_date = None
                for sel in date_selectors:
                    pub_date = item.css(sel).get()
                    if pub_date:
                        break
                
                if pub_date:
                    result['publication_date'] = pub_date.strip()
                
                # Códigos IPC
                ipc_selectors = [
                    '.ipc-code::text',
                    '.ipc::text',
                    'span[class*="ipc"]::text',
                ]
                
                ipc_codes = []
                for sel in ipc_selectors:
                    codes = item.css(sel).getall()
                    if codes:
                        ipc_codes.extend(codes)
                
                result['ipc_codes'] = [c.strip() for c in ipc_codes if c.strip()]
                
                # Adicionar apenas se tiver dados mínimos
                if result.get('patent_id') or result.get('publication_number'):
                    results.append(result)
                    
            except Exception as e:
                # Continuar com próximo item se houver erro
                print(f"Erro ao parsear item: {e}")
                continue
        
        return results
    
    @staticmethod
    def extract_total_results(html: str) -> int:
        """
        Extrai número total de resultados
        
        Args:
            html: HTML da página
            
        Returns:
            Número total de resultados
        """
        selector = Selector(text=html)
        
        # Múltiplos seletores para total de resultados
        total_selectors = [
            '.total-results::text',
            '.result-count::text',
            '#totalResults::text',
            '.results-info::text',
            'span[class*="total"]::text',
            'div[class*="count"]::text',
        ]
        
        for sel in total_selectors:
            text = selector.css(sel).get()
            if text:
                # Extrair números do texto
                numbers = re.findall(r'\d[\d,]*', text)
                if numbers:
                    # Pegar o maior número encontrado
                    return max(int(n.replace(',', '')) for n in numbers)
        
        # Tentar XPath genérico
        texts = selector.xpath('//text()').getall()
        for text in texts:
            if any(keyword in text.lower() for keyword in ['total', 'results', 'found', 'resultados']):
                numbers = re.findall(r'\d[\d,]*', text)
                if numbers:
                    return max(int(n.replace(',', '')) for n in numbers)
        
        return 0
    
    @staticmethod
    def parse_patent_detail(html: str) -> Dict:
        """
        Extrai detalhes completos de uma patente
        
        Args:
            html: HTML da página de detalhes
            
        Returns:
            Dicionário com dados da patente
        """
        selector = Selector(text=html)
        patent = {}
        
        # Título
        title_selectors = [
            'h1.patent-title::text',
            '.title::text',
            'h1::text',
            'div[class*="title"]::text',
        ]
        
        for sel in title_selectors:
            title = selector.css(sel).get()
            if title:
                patent['title'] = title.strip()
                break
        
        # Abstract
        abstract_selectors = [
            '#abstract::text',
            '.abstract::text',
            'div[name="abstract"]::text',
            'p[class*="abstract"]::text',
        ]
        
        abstract_parts = []
        for sel in abstract_selectors:
            parts = selector.css(sel).getall()
            if parts:
                abstract_parts.extend(parts)
        
        if abstract_parts:
            patent['abstract'] = ' '.join(abstract_parts).strip()
        
        # Números
        pub_number = selector.css('.publication-number::text, #publicationNumber::text').get()
        if pub_number:
            patent['publication_number'] = pub_number.strip()
        
        # Datas
        pub_date = selector.css('.publication-date::text, #publicationDate::text').get()
        if pub_date:
            patent['publication_date'] = pub_date.strip()
        
        app_date = selector.css('.application-date::text, #applicationDate::text').get()
        if app_date:
            patent['application_date'] = app_date.strip()
        
        # Inventores
        inventors = []
        inventor_elements = selector.css('.inventor, [itemprop="inventor"]')
        for inv in inventor_elements:
            name = inv.css('.name::text, .inventor-name::text').get()
            if name:
                inventors.append(name.strip())
        
        if not inventors:
            # Fallback
            inventors = selector.css('span[class*="inventor"]::text').getall()
            inventors = [i.strip() for i in inventors if i.strip()]
        
        patent['inventors'] = inventors
        
        # Requerentes
        applicants = []
        applicant_elements = selector.css('.applicant, [itemprop="applicant"]')
        for app in applicant_elements:
            name = app.css('.name::text, .applicant-name::text').get()
            if name:
                applicants.append(name.strip())
        
        if not applicants:
            # Fallback
            applicants = selector.css('span[class*="applicant"]::text').getall()
            applicants = [a.strip() for a in applicants if a.strip()]
        
        patent['applicants'] = applicants
        
        # Classificações IPC
        ipc_codes = selector.css('.ipc-code::text, [itemprop="ipcCode"]::text').getall()
        patent['ipc_codes'] = [c.strip() for c in ipc_codes if c.strip()]
        
        # CPC codes
        cpc_codes = selector.css('.cpc-code::text, [itemprop="cpcCode"]::text').getall()
        patent['cpc_codes'] = [c.strip() for c in cpc_codes if c.strip()]
        
        return patent
