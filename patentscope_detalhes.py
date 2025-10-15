#!/usr/bin/env python3
"""
Módulo para extrair detalhes completos de patentes do PatentScope
Usa o detailUrl para buscar informações adicionais
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import time
import logging
from typing import Dict, List
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatentScopeDetailExtractor:
    """Extrai detalhes completos de patentes do PatentScope"""

    def __init__(self, driver):
        """
        Inicializa o extrator

        Args:
            driver: Instância do Selenium WebDriver
        """
        self.driver = driver

    def obter_detalhes_completos(self, patente: Dict) -> Dict:
        """
        Obtém detalhes completos de uma patente usando o detailUrl

        Args:
            patente: Dicionário com dados básicos da patente (deve conter detailUrl)

        Returns:
            Dicionário com todos os detalhes da patente
        """
        detail_url = patente.get('detailUrl', '')
        pub_number = patente.get('publicationNumber', 'N/A')

        if not detail_url:
            logger.warning(f"Patente {pub_number} não tem detailUrl")
            return patente

        logger.info(f"Buscando detalhes completos de {pub_number}...")
        logger.info(f"URL: {detail_url}")

        try:
            # Navega para página de detalhes
            self.driver.get(detail_url)
            time.sleep(3)  # Aguarda inicial

            # Aguarda o elemento "Loading..." desaparecer (página carrega dinamicamente)
            try:
                WebDriverWait(self.driver, 20).until_not(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Loading')]"))
                )
                logger.debug(f"Página de detalhes carregada (Loading desapareceu)")
            except TimeoutException:
                logger.warning(f"Timeout aguardando 'Loading' desaparecer para {pub_number}")

            # Aguarda elementos específicos aparecerem
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
                logger.debug(f"Elementos da página encontrados")
            except TimeoutException:
                logger.warning(f"Timeout aguardando elementos para {pub_number}")

            # Aguarda adicional para JavaScript processar
            time.sleep(5)

            # Extrai HTML
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # Cria cópia dos dados básicos
            detalhes = patente.copy()

            # Extrai campos adicionais
            detalhes['detalhes_completos'] = self._extrair_campos_detalhados(soup)

            # Screenshot para debug (opcional)
            try:
                screenshot_name = f"patent_detail_{pub_number.replace('/', '_')}.png"
                self.driver.save_screenshot(screenshot_name)
                detalhes['screenshot'] = screenshot_name
            except:
                pass

            logger.info(f"✅ Detalhes extraídos de {pub_number}")
            return detalhes

        except Exception as e:
            logger.error(f"❌ Erro ao buscar detalhes de {pub_number}: {e}")
            return patente

    def _extrair_campos_detalhados(self, soup: BeautifulSoup) -> Dict:
        """
        Extrai campos detalhados da página de detalhes

        Args:
            soup: BeautifulSoup da página de detalhes

        Returns:
            Dicionário com campos detalhados
        """
        detalhes = {}

        # CAMPOS BIBLIOGRÁFICOS ESPECÍFICOS (15 campos)
        biblio_fields = self._extrair_campos_bibliograficos_estruturados(soup)
        detalhes.update(biblio_fields)

        # 1. Abstract/Resumo Completo
        abstract = self._extrair_abstract(soup)
        if abstract:
            detalhes['abstract_completo'] = abstract

        # 2. Claims/Reivindicações
        claims = self._extrair_claims(soup)
        if claims:
            detalhes['claims'] = claims

        # 3. Description/Descrição
        description = self._extrair_description(soup)
        if description:
            detalhes['description'] = description

        # 4. Dados bibliográficos adicionais (genérico)
        biblio = self._extrair_dados_bibliograficos(soup)
        if biblio:
            detalhes['bibliografia_adicional'] = biblio

        # 5. Classificações completas
        classifications = self._extrair_classificacoes(soup)
        if classifications:
            detalhes['classificacoes_detalhadas'] = classifications

        # 6. Citações
        citations = self._extrair_citacoes(soup)
        if citations:
            detalhes['citacoes'] = citations

        # 7. Documentos relacionados
        related = self._extrair_documentos_relacionados(soup)
        if related:
            detalhes['documentos_relacionados'] = related

        return detalhes

    def _extrair_campos_bibliograficos_estruturados(self, soup: BeautifulSoup) -> Dict:
        """
        Extrai campos bibliográficos estruturados (15 campos específicos)

        Campos extraídos:
        - Office, Application Number, Application Date
        - Publication Number, Publication Date
        - Grant Number, Grant Date, Publication Kind
        - IPC, CPC
        - Applicants, Inventors, Agents
        - Title, Abstract
        """
        campos = {}

        try:
            # Office - procura pelo padrão específico
            office_labels = soup.find_all('span', class_='trans-nc-detail-label')
            for label in office_labels:
                if 'Office' in label.get_text():
                    next_div = label.find_next('div')
                    if next_div:
                        office_value = next_div.get_text(strip=True)
                        if office_value and len(office_value) < 50:
                            campos['Office'] = office_value
                            break

            # Applicants - usa ID específica
            applicants_elem = soup.find('span', id=lambda x: x and 'NPapplicants' in x)
            if applicants_elem:
                applicants_html = applicants_elem.decode_contents()
                applicants_list = [a.strip() for a in applicants_html.replace('<br>', '\n').replace('<br/>', '\n').split('\n') if a.strip()]
                if applicants_list:
                    campos['Applicants'] = applicants_list

            # Inventors - usa ID específica
            inventors_elem = soup.find('span', id=lambda x: x and 'NPinventors' in x)
            if inventors_elem:
                inventors_html = inventors_elem.decode_contents()
                inventors_list = [i.strip() for i in inventors_html.replace('<br>', '\n').replace('<br/>', '\n').split('\n') if i.strip()]
                if inventors_list:
                    campos['Inventors'] = inventors_list

            # CPC - procura por links com href contendo 'cpc'
            cpc_links = soup.find_all('a', href=lambda x: x and 'cpc' in x.lower())
            cpc_codes = []
            for link in cpc_links:
                code = link.get_text(strip=True)
                if code and len(code) < 30 and '/' in code:
                    cpc_codes.append(code)
            if cpc_codes:
                campos['CPC'] = list(dict.fromkeys(cpc_codes))  # Remove duplicatas

            # Agents - usa ID específica
            agents_elem = soup.find('span', id=lambda x: x and 'NPagents' in x)
            if agents_elem:
                agents_html = agents_elem.decode_contents()
                agents_text = agents_html.replace('<br>', '').replace('<br/>', '').strip()
                if agents_text:
                    campos['Agents'] = agents_text

            # Publication Kind - procura dentro do div que contém label e value
            all_divs = soup.find_all('div')
            for div in all_divs:
                label_span = div.find('span', class_='ps-biblio-field--label')
                if label_span and 'Publication Kind' in label_span.get_text():
                    value_span = div.find('span', class_='ps-biblio-field--value')
                    if value_span:
                        kind = value_span.get_text(strip=True)
                        if kind:
                            campos['Publication Kind'] = kind
                            break

            # Abstract - procura div com classe específica
            abstract_div = soup.find('div', class_='patent-abstract')
            if abstract_div:
                spans = abstract_div.find_all('span')
                abstract_parts = []
                for span in spans:
                    span_text = span.get_text(strip=True)
                    if span_text and len(span_text) > 50:
                        abstract_parts.append(span_text)
                if abstract_parts:
                    campos['Abstract'] = abstract_parts[0]

            # Extração por regex de campos com padrões conhecidos
            import re
            page_text = soup.get_text()

            # Application Number
            if 'Application Number' not in campos:
                app_match = re.search(r'Application Number[:\s]+(\d+\.?\d*)', page_text)
                if app_match:
                    campos['Application Number'] = app_match.group(1)

            # Publication Number
            if 'Publication Number' not in campos:
                pub_match = re.search(r'Publication Number[:\s]+(\d+)', page_text)
                if pub_match:
                    campos['Publication Number'] = pub_match.group(1)

            # Grant Number
            grant_match = re.search(r'Grant Number[:\s]+(\d+)', page_text)
            if grant_match:
                campos['Grant Number'] = grant_match.group(1)

            # Dates (formato: DD.MM.YYYY)
            app_date_match = re.search(r'Application Date[:\s]+(\d{2}\.\d{2}\.\d{4})', page_text)
            if app_date_match:
                campos['Application Date'] = app_date_match.group(1)

            pub_date_match = re.search(r'Publication Date[:\s]+(\d{2}\.\d{2}\.\d{4})', page_text)
            if pub_date_match:
                campos['Publication Date'] = pub_date_match.group(1)

            grant_date_match = re.search(r'Grant Date[:\s]+(\d{2}\.\d{2}\.\d{4})', page_text)
            if grant_date_match:
                campos['Grant Date'] = grant_date_match.group(1)

            # IPC - procura por códigos IPC (formato: A61K 14/605)
            ipc_codes = re.findall(r'[A-H]\d{2}[A-Z]\s+\d+/\d+', page_text)
            if ipc_codes:
                campos['IPC'] = list(set(ipc_codes))

            # Title
            title_elem = soup.find('h1')
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if ' - ' in title_text:
                    title_text = title_text.split(' - ', 1)[1]
                campos['Title'] = title_text

        except Exception as e:
            logger.error(f"Erro ao extrair campos bibliográficos estruturados: {e}")

        return campos

    def _extrair_abstract(self, soup: BeautifulSoup) -> str:
        """Extrai resumo completo"""
        try:
            # Tenta múltiplos seletores
            selectors = [
                {'name': 'div', 'attrs': {'id': 'abstract'}},
                {'name': 'div', 'attrs': {'class': 'abstract'}},
                {'name': 'section', 'attrs': {'id': 'abstract'}},
                {'name': 'p', 'attrs': {'class': 'abstract'}},
            ]

            for selector in selectors:
                elem = soup.find(selector['name'], selector['attrs'])
                if elem:
                    text = elem.get_text(strip=True, separator=' ')
                    if len(text) > 50:  # Mínimo de caracteres
                        return text

            return ""
        except Exception as e:
            logger.debug(f"Erro ao extrair abstract: {e}")
            return ""

    def _extrair_claims(self, soup: BeautifulSoup) -> List[str]:
        """Extrai reivindicações"""
        try:
            claims = []

            # Tenta múltiplos seletores
            selectors = [
                {'name': 'div', 'attrs': {'id': 'claims'}},
                {'name': 'div', 'attrs': {'class': 'claims'}},
                {'name': 'section', 'attrs': {'id': 'claims'}},
            ]

            for selector in selectors:
                claims_div = soup.find(selector['name'], selector['attrs'])
                if claims_div:
                    # Procura claims individuais
                    claim_elements = claims_div.find_all(['p', 'div'], class_=lambda x: x and 'claim' in x.lower())

                    if claim_elements:
                        for i, claim_elem in enumerate(claim_elements, 1):
                            claim_text = claim_elem.get_text(strip=True, separator=' ')
                            if claim_text:
                                claims.append(f"{i}. {claim_text}")
                    else:
                        # Se não encontrar claims individuais, pega todo o texto
                        text = claims_div.get_text(strip=True, separator='\n')
                        if text:
                            claims.append(text)

                    if claims:
                        break

            return claims
        except Exception as e:
            logger.debug(f"Erro ao extrair claims: {e}")
            return []

    def _extrair_description(self, soup: BeautifulSoup) -> str:
        """Extrai descrição (limitada a 10000 caracteres)"""
        try:
            selectors = [
                {'name': 'div', 'attrs': {'id': 'description'}},
                {'name': 'div', 'attrs': {'class': 'description'}},
                {'name': 'section', 'attrs': {'id': 'description'}},
            ]

            for selector in selectors:
                elem = soup.find(selector['name'], selector['attrs'])
                if elem:
                    text = elem.get_text(strip=True, separator=' ')
                    if len(text) > 100:
                        return text[:10000]  # Limita tamanho

            return ""
        except Exception as e:
            logger.debug(f"Erro ao extrair description: {e}")
            return ""

    def _extrair_dados_bibliograficos(self, soup: BeautifulSoup) -> Dict:
        """Extrai dados bibliográficos adicionais"""
        try:
            biblio = {}

            # Procura por tabela de dados bibliográficos
            biblio_table = soup.find('table', class_=lambda x: x and 'biblio' in x.lower())

            if not biblio_table:
                biblio_table = soup.find('dl', class_=lambda x: x and 'biblio' in x.lower())

            if biblio_table:
                # Extrai pares chave-valor
                if biblio_table.name == 'table':
                    rows = biblio_table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            key = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            if key and value:
                                biblio[key] = value

                elif biblio_table.name == 'dl':
                    dts = biblio_table.find_all('dt')
                    dds = biblio_table.find_all('dd')
                    for dt, dd in zip(dts, dds):
                        key = dt.get_text(strip=True)
                        value = dd.get_text(strip=True)
                        if key and value:
                            biblio[key] = value

            return biblio
        except Exception as e:
            logger.debug(f"Erro ao extrair bibliografia: {e}")
            return {}

    def _extrair_classificacoes(self, soup: BeautifulSoup) -> Dict:
        """Extrai classificações IPC/CPC completas"""
        try:
            classifications = {
                'ipc': [],
                'cpc': [],
                'outras': []
            }

            # Procura seções de classificação
            class_sections = soup.find_all(['div', 'section'], class_=lambda x: x and 'classification' in x.lower())

            for section in class_sections:
                text = section.get_text(strip=True)

                # Identifica tipo de classificação
                if 'IPC' in text or 'ipc' in section.get('class', []):
                    classifications['ipc'].append(text)
                elif 'CPC' in text or 'cpc' in section.get('class', []):
                    classifications['cpc'].append(text)
                else:
                    classifications['outras'].append(text)

            return classifications
        except Exception as e:
            logger.debug(f"Erro ao extrair classificações: {e}")
            return {}

    def _extrair_citacoes(self, soup: BeautifulSoup) -> Dict:
        """Extrai citações de patentes"""
        try:
            citations = {
                'cited_by': [],  # Patentes que citam esta
                'cites': []      # Patentes citadas por esta
            }

            # Procura seções de citações
            citation_sections = soup.find_all(['div', 'section'], class_=lambda x: x and 'citation' in x.lower())

            for section in citation_sections:
                links = section.find_all('a', href=True)
                for link in links:
                    patent_num = link.get_text(strip=True)
                    if patent_num:
                        # Tenta identificar se é "cited by" ou "cites"
                        section_text = section.get_text().lower()
                        if 'cited by' in section_text:
                            citations['cited_by'].append(patent_num)
                        elif 'cites' in section_text or 'references' in section_text:
                            citations['cites'].append(patent_num)

            return citations
        except Exception as e:
            logger.debug(f"Erro ao extrair citações: {e}")
            return {}

    def _extrair_documentos_relacionados(self, soup: BeautifulSoup) -> List[str]:
        """Extrai documentos relacionados (família de patentes)"""
        try:
            related = []

            # Procura seção de família de patentes
            family_section = soup.find(['div', 'section'], class_=lambda x: x and 'family' in x.lower())

            if family_section:
                links = family_section.find_all('a', href=True)
                for link in links:
                    patent_num = link.get_text(strip=True)
                    if patent_num:
                        related.append(patent_num)

            return related
        except Exception as e:
            logger.debug(f"Erro ao extrair documentos relacionados: {e}")
            return []


def enriquecer_patentes_com_detalhes(patentes: List[Dict], driver, max_detalhes: int = None) -> List[Dict]:
    """
    Enriquece lista de patentes com detalhes completos

    Args:
        patentes: Lista de patentes com detailUrl
        driver: Instância do Selenium WebDriver
        max_detalhes: Número máximo de patentes para buscar detalhes (None = todas)

    Returns:
        Lista de patentes enriquecidas com detalhes
    """
    extractor = PatentScopeDetailExtractor(driver)
    patentes_enriquecidas = []

    # Limita número de detalhes se especificado
    patentes_para_processar = patentes[:max_detalhes] if max_detalhes else patentes

    total = len(patentes_para_processar)
    logger.info(f"Buscando detalhes completos de {total} patentes...")

    for i, patente in enumerate(patentes_para_processar, 1):
        logger.info(f"Progresso: {i}/{total}")

        patente_enriquecida = extractor.obter_detalhes_completos(patente)
        patentes_enriquecidas.append(patente_enriquecida)

        # Delay entre requisições para respeitar rate limit
        if i < total:
            time.sleep(2)  # 2 segundos entre cada requisição

    logger.info(f"✅ Detalhes completos extraídos de {len(patentes_enriquecidas)} patentes")

    return patentes_enriquecidas


def agrupar_por_publication_number(patentes: List[Dict]) -> Dict[str, Dict]:
    """
    Agrupa patentes por publicationNumber

    Args:
        patentes: Lista de patentes

    Returns:
        Dicionário com publicationNumber como chave
    """
    agrupadas = {}

    for patente in patentes:
        pub_num = patente.get('publicationNumber', '')
        if pub_num:
            agrupadas[pub_num] = patente
        else:
            logger.warning(f"Patente sem publicationNumber encontrada")

    logger.info(f"Patentes agrupadas por publicationNumber: {len(agrupadas)} únicas")

    return agrupadas
