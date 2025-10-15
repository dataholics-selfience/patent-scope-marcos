#!/usr/bin/env python3
"""
PatentScope Scraper - Cliente para API do WIPO PatentScope
Busca patentes internacionais usando a API REST do PatentScope
"""

import requests
import time
import json
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config_patentscope import (
    PATENTSCOPE_CONFIG,
    PATENTSCOPE_AUTH_CONFIG,
    PATENTSCOPE_VALIDATION_CONFIG,
    COUNTRY_CODES
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('patentscope_scraper.log'),
        logging.StreamHandler()
    ]
)

class RateLimiter:
    """Gerencia rate limiting inteligente"""

    def __init__(self, min_delay=1.0, max_delay=3.0, adaptive=True):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.adaptive = adaptive
        self.last_request_time = 0
        self.consecutive_errors = 0
        self.success_streak = 0

    def wait(self):
        """Calcula e aplica delay inteligente"""
        current_time = time.time()

        if self.adaptive:
            # Aumenta delay em caso de erros consecutivos
            if self.consecutive_errors > 0:
                delay = min(self.min_delay * (2 ** self.consecutive_errors), self.max_delay)
            else:
                # Reduz delay gradualmente em caso de sucessos
                delay = max(self.min_delay, self.max_delay / (1 + self.success_streak * 0.1))
        else:
            delay = random.uniform(self.min_delay, self.max_delay)

        # Garante que passou tempo suficiente desde última requisição
        elapsed = current_time - self.last_request_time
        if elapsed < delay:
            time.sleep(delay - elapsed)

        self.last_request_time = time.time()

    def record_success(self):
        """Registra sucesso na requisição"""
        self.consecutive_errors = 0
        self.success_streak += 1

    def record_error(self):
        """Registra erro na requisição"""
        self.consecutive_errors += 1
        self.success_streak = 0

class DataValidator:
    """Valida dados extraídos da API PatentScope"""

    @staticmethod
    def validate_patent(data: Dict) -> bool:
        """Valida dados de patente"""
        required_fields = PATENTSCOPE_VALIDATION_CONFIG.REQUIRED_PATENT_FIELDS

        # Verifica campos obrigatórios
        if not all(field in data and data[field] for field in required_fields):
            logging.warning(f"Campos obrigatórios faltando em patente")
            return False

        # Valida tamanho do título
        if 'title' in data and data['title']:
            if len(data['title']) < PATENTSCOPE_VALIDATION_CONFIG.MIN_TITLE_LENGTH:
                logging.warning(f"Título muito curto: {data['title']}")
                return False

        return True

class IncrementalSaver:
    """Salva dados incrementalmente"""

    def __init__(self, base_filename: str, chunk_size: int = 100):
        self.base_filename = base_filename
        self.chunk_size = chunk_size
        self.current_data = []
        self.total_saved = 0

    def add_data(self, data: Dict):
        """Adiciona dados ao buffer"""
        self.current_data.append(data)

        if len(self.current_data) >= self.chunk_size:
            self.save_chunk()

    def save_chunk(self):
        """Salva chunk atual"""
        if not self.current_data:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.base_filename}_chunk_{self.total_saved}_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.current_data, f, ensure_ascii=False, indent=2)

        logging.info(f"Salvos {len(self.current_data)} registros em {filename}")
        self.total_saved += len(self.current_data)
        self.current_data = []

    def finalize(self):
        """Salva dados restantes"""
        if self.current_data:
            self.save_chunk()

class PatentScopeScraper:
    """Cliente PatentScope com Selenium para dados reais"""

    def __init__(self,
                 min_delay=None,
                 max_delay=None,
                 headless=True,
                 use_demo_mode=False,
                 use_login=False):
        """
        Scraper PatentScope com Selenium (PRODUCTION READY)

        Args:
            min_delay: Delay mínimo entre requisições (padrão: config)
            max_delay: Delay máximo entre requisições (padrão: config)
            headless: Executar Chrome em modo headless (padrão: True)
            use_demo_mode: Usar dados de demonstração ao invés de Selenium (padrão: False)
            use_login: Usar autenticação com login WIPO (padrão: False)
        """
        self.config = PATENTSCOPE_CONFIG
        self.auth_config = PATENTSCOPE_AUTH_CONFIG
        self.use_demo_mode = use_demo_mode
        self.use_login = use_login

        # Rate limiter
        min_delay = min_delay or self.config.MIN_DELAY
        max_delay = max_delay or self.config.MAX_DELAY
        self.rate_limiter = RateLimiter(min_delay, max_delay)

        # Validador
        self.validator = DataValidator()

        # Configuração da sessão HTTP (para fallback)
        self.session = self._create_session()

        # Inicializa Selenium para modo produção
        if not use_demo_mode:
            self.chrome_options = self._setup_chrome_options(headless)
            self.driver = None
            self.logged_in = False
            self.login_time = None
            self._init_driver()

            # Login opcional - PatentScope funciona com ou sem autenticação
            if self.use_login:
                if self.auth_config.USERNAME and self.auth_config.PASSWORD:
                    logging.info("Modo de login habilitado - tentando autenticação WIPO...")
                    try:
                        self._login()
                    except Exception as e:
                        logging.warning(f"Login falhou, continuando sem autenticação: {e}")
                else:
                    logging.warning("Login solicitado mas credenciais não configuradas (.env)")
            else:
                logging.info("Modo anônimo - sem autenticação (melhor performance)")
        else:
            logging.warning("PatentScope em MODO DEMO - dados fictícios")

        logging.info("PatentScopeScraper inicializado com sucesso")

    def _create_session(self) -> requests.Session:
        """Cria sessão HTTP com configurações robustas"""
        session = requests.Session()

        # Headers realistas
        session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': self.config.BASE_URL,
        })

        # PatentScope usa autenticação por login (username/password), não API key
        # A autenticação será feita via Selenium no método _login()

        return session

    def _get_random_user_agent(self) -> str:
        """Retorna User-Agent aleatório"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        return random.choice(user_agents)

    def _setup_chrome_options(self, headless: bool) -> Options:
        """Configura opções do Chrome para Selenium"""
        options = Options()

        if headless:
            options.add_argument('--headless')

        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument(f'--user-agent={self._get_random_user_agent()}')
        options.add_argument('--lang=en-US')

        return options

    def _init_driver(self):
        """Inicializa driver Selenium"""
        try:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            logging.info("Selenium WebDriver inicializado")
        except Exception as e:
            logging.error(f"Erro ao inicializar Selenium: {e}")
            logging.warning("Mudando para modo demo")
            self.use_demo_mode = True
            self.driver = None

    def _login(self):
        """Realiza login no WIPO PatentScope"""
        try:
            logging.info("Realizando login no WIPO PatentScope...")

            # Navega para página de login
            login_url = self.auth_config.LOGIN_URL
            logging.info(f"Acessando: {login_url}")
            self.driver.get(login_url)

            # Aguarda página carregar
            time.sleep(3)

            # Procura pelo link/botão "IP Portal" ou "Login"
            login_selectors = [
                (By.LINK_TEXT, "IP Portal"),
                (By.PARTIAL_LINK_TEXT, "IP Portal"),
                (By.LINK_TEXT, "Login"),
                (By.PARTIAL_LINK_TEXT, "Login"),
                (By.CSS_SELECTOR, "a[href*='ipportal']"),
                (By.CSS_SELECTOR, "a[href*='login']"),
                (By.XPATH, "//a[contains(text(), 'IP Portal')]"),
                (By.XPATH, "//a[contains(text(), 'Login')]")
            ]

            login_link = None
            for selector_type, selector_value in login_selectors:
                try:
                    login_link = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    logging.info(f"Link de login encontrado: {selector_type}")
                    break
                except:
                    continue

            if login_link:
                login_link.click()
                time.sleep(3)
                logging.info("Clicked no link de login")
            else:
                logging.warning("Link de login não encontrado, tentando direto no formulário")

            # Aguarda formulário de login aparecer
            time.sleep(2)

            # Procura campos de usuário e senha
            username_selectors = [
                (By.ID, "username"),
                (By.ID, "user"),
                (By.ID, "login"),
                (By.NAME, "username"),
                (By.NAME, "user"),
                (By.CSS_SELECTOR, "input[type='text'][name*='user']"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.XPATH, "//input[@type='text' or @type='email']")
            ]

            password_selectors = [
                (By.ID, "password"),
                (By.ID, "pass"),
                (By.ID, "pwd"),
                (By.NAME, "password"),
                (By.NAME, "pass"),
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.XPATH, "//input[@type='password']")
            ]

            # Localiza campo de usuário
            username_field = None
            for selector_type, selector_value in username_selectors:
                try:
                    username_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    logging.info(f"Campo usuário encontrado: {selector_type}")
                    break
                except:
                    continue

            # Localiza campo de senha
            password_field = None
            for selector_type, selector_value in password_selectors:
                try:
                    password_field = self.driver.find_element(selector_type, selector_value)
                    logging.info(f"Campo senha encontrado: {selector_type}")
                    break
                except:
                    continue

            if not username_field or not password_field:
                logging.error("Campos de login não encontrados")
                self.driver.save_screenshot("wipo_login_debug.png")
                logging.info("Screenshot salvo: wipo_login_debug.png")
                return

            # Preenche credenciais
            logging.info("Preenchendo credenciais...")
            username_field.clear()
            username_field.send_keys(self.auth_config.USERNAME)
            time.sleep(0.5)

            password_field.clear()
            password_field.send_keys(self.auth_config.PASSWORD)
            time.sleep(0.5)

            # Procura botão de submit
            submit_selectors = [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.ID, "submit"),
                (By.NAME, "submit"),
                (By.XPATH, "//button[contains(text(), 'Login')]"),
                (By.XPATH, "//button[contains(text(), 'Sign in')]"),
                (By.XPATH, "//input[@type='submit']")
            ]

            submit_button = None
            for selector_type, selector_value in submit_selectors:
                try:
                    submit_button = self.driver.find_element(selector_type, selector_value)
                    logging.info(f"Botão submit encontrado: {selector_type}")
                    break
                except:
                    continue

            if submit_button:
                submit_button.click()
                logging.info("Submitted formulário de login")
            else:
                # Fallback: pressiona Enter
                logging.warning("Botão submit não encontrado, pressionando Enter")
                from selenium.webdriver.common.keys import Keys
                password_field.send_keys(Keys.RETURN)

            # Aguarda login completar
            time.sleep(5)

            # Verifica se login foi bem sucedido
            # Pode verificar pela presença de elementos que aparecem após login
            # ou pela URL mudando
            current_url = self.driver.current_url
            logging.info(f"URL após login: {current_url}")

            # Considera login bem sucedido se não está mais na página de login
            if 'login' not in current_url.lower() or 'portal' in current_url.lower():
                self.logged_in = True
                self.login_time = datetime.now()
                logging.info("✅ Login realizado com sucesso!")
            else:
                logging.warning("⚠️ Login pode não ter sido bem sucedido")
                self.driver.save_screenshot("wipo_after_login.png")
                logging.info("Screenshot pós-login salvo: wipo_after_login.png")

        except Exception as e:
            logging.error(f"Erro ao fazer login no WIPO: {e}")
            import traceback
            traceback.print_exc()
            self.driver.save_screenshot("wipo_login_error.png")
            logging.info("Screenshot de erro salvo: wipo_login_error.png")

    def __del__(self):
        """Fecha driver Selenium ao destruir objeto"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except:
                pass

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type(requests.RequestException))
    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> requests.Response:
        """Faz requisição com retry automático"""
        self.rate_limiter.wait()

        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=self.config.REQUEST_TIMEOUT, **kwargs)
            else:
                response = self.session.post(url, timeout=self.config.REQUEST_TIMEOUT, **kwargs)

            response.raise_for_status()

            self.rate_limiter.record_success()
            return response

        except requests.RequestException as e:
            self.rate_limiter.record_error()
            logging.error(f"Erro na requisição para {url}: {e}")
            raise

    def construir_query(self,
                       termo_busca: str,
                       campo: str = 'all',
                       pais: Optional[str] = None,
                       data_inicio: Optional[str] = None,
                       data_fim: Optional[str] = None) -> str:
        """
        Constrói query para PatentScope API

        Args:
            termo_busca: Termo para buscar
            campo: Campo de busca ('all', 'title', 'abstract', 'inventor', 'applicant')
            pais: Código do país (ex: 'BR', 'US', 'EP')
            data_inicio: Data início (formato: YYYY-MM-DD)
            data_fim: Data fim (formato: YYYY-MM-DD)

        Returns:
            Query string formatada
        """
        # Obtém código do campo
        field_code = self.config.SEARCH_FIELDS.get(campo, 'FP')

        # Query básica - PatentScope usa sintaxe: campo:(termo)
        # Para campo 'all', usa apenas o termo sem prefixo
        if campo == 'all' or field_code == 'FP':
            query = termo_busca
        else:
            query = f"{field_code}:({termo_busca})"

        # Adiciona filtro de país se especificado
        if pais:
            query += f" AND PC:{pais}"

        # Adiciona filtro de data se especificado
        if data_inicio:
            query += f" AND PD:[{data_inicio} TO "
            if data_fim:
                query += f"{data_fim}]"
            else:
                query += "*]"

        return query

    def buscar_patentes(self,
                       termo_busca: str,
                       campo: str = 'all',
                       pais: Optional[str] = None,
                       data_inicio: Optional[str] = None,
                       data_fim: Optional[str] = None,
                       limite: int = 100,
                       salvar_incremental: bool = False) -> List[Dict]:
        """
        Busca patentes no PatentScope

        Args:
            termo_busca: Termo para buscar
            campo: Campo de busca ('all', 'title', 'abstract', 'inventor', 'applicant')
            pais: Código do país (ex: 'BR', 'US', 'WO')
            data_inicio: Data início (formato: YYYY-MM-DD)
            data_fim: Data fim (formato: YYYY-MM-DD)
            limite: Limite de resultados
            salvar_incremental: Se deve salvar incrementalmente

        Returns:
            Lista de patentes encontradas
        """
        logging.info(f"Iniciando busca PatentScope: '{termo_busca}' no campo '{campo}'")
        if pais:
            logging.info(f"  Filtro de país: {pais} ({COUNTRY_CODES.get(pais, 'Desconhecido')})")

        # Constrói query
        query = self.construir_query(termo_busca, campo, pais, data_inicio, data_fim)
        logging.info(f"  Query: {query}")

        saver = IncrementalSaver(f"patentscope_{termo_busca.replace(' ', '_')}", 50) if salvar_incremental else None

        resultados = []

        try:
            # Modo produção com Selenium
            if not self.use_demo_mode and self.driver:
                patentes = self._buscar_com_selenium(termo_busca, campo, pais, data_inicio, data_fim, limite)
            else:
                # Fallback para modo demo
                logging.warning("Usando modo DEMO - dados fictícios")
                patentes = self._gerar_dados_demonstracao(termo_busca, limite, campo, pais)

            for patente in patentes:
                if self.validator.validate_patent(patente):
                    resultados.append(patente)
                    if saver:
                        saver.add_data(patente)

                    if len(resultados) >= limite:
                        break
                else:
                    logging.warning(f"Patente inválida ignorada: {patente.get('publicationNumber', 'N/A')}")

        except Exception as e:
            logging.error(f"Erro na busca de patentes: {e}")

        finally:
            if saver:
                saver.finalize()

        logging.info(f"Busca concluída. {len(resultados)} patentes encontradas")
        return resultados

    def buscar_patentes_simples(self,
                                termo_busca: str,
                                limite: int = 100) -> List[Dict]:
        """
        Busca simples de patentes (todos os campos)

        Args:
            termo_busca: Termo para buscar
            limite: Limite de resultados

        Returns:
            Lista de patentes encontradas
        """
        return self.buscar_patentes(termo_busca, campo='all', limite=limite)

    def buscar_por_titulo(self,
                         titulo: str,
                         limite: int = 100) -> List[Dict]:
        """Busca patentes por título"""
        return self.buscar_patentes(titulo, campo='title', limite=limite)

    def buscar_por_inventor(self,
                           inventor: str,
                           limite: int = 100) -> List[Dict]:
        """Busca patentes por inventor"""
        return self.buscar_patentes(inventor, campo='inventor', limite=limite)

    def buscar_por_depositante(self,
                               depositante: str,
                               limite: int = 100) -> List[Dict]:
        """Busca patentes por depositante/requerente"""
        return self.buscar_patentes(depositante, campo='applicant', limite=limite)

    def buscar_por_resumo(self,
                         resumo: str,
                         limite: int = 100) -> List[Dict]:
        """Busca patentes por resumo/abstract"""
        return self.buscar_patentes(resumo, campo='abstract', limite=limite)

    def _buscar_com_selenium(self, termo_busca: str, campo: str, pais: Optional[str],
                             data_inicio: Optional[str], data_fim: Optional[str], limite: int) -> List[Dict]:
        """
        Busca patentes usando Selenium (PRODUCTION)

        Args:
            termo_busca: Termo para buscar
            campo: Campo de busca
            pais: Filtro de país
            data_inicio: Data início
            data_fim: Data fim
            limite: Limite de resultados

        Returns:
            Lista de patentes extraídas
        """
        patentes = []

        try:
            # Verifica se o driver ainda está funcionando
            if self.driver:
                try:
                    # Testa se o driver está vivo
                    _ = self.driver.current_url
                except:
                    # Driver morreu, reinicializa
                    logging.warning("Driver inativo, reinicializando...")
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                    self._init_driver()

            # Se ainda não tem driver, inicializa
            if not self.driver:
                logging.info("Inicializando novo driver...")
                self._init_driver()

            # URL da busca PatentScope (usa URL em português ou inglês)
            if self.logged_in and self.auth_config.SEARCH_URL:
                search_url = self.auth_config.SEARCH_URL
            else:
                # Usa versão em inglês por padrão (melhor compatibilidade)
                search_url = f"{self.config.BASE_URL}/search/en/search.jsf"

            logging.info(f"Acessando PatentScope: {search_url}")
            self.driver.get(search_url)

            # Aguarda página carregar completamente
            logging.info("Aguardando carregamento da página...")
            time.sleep(6)  # Aguarda JavaScript e elementos dinâmicos

            # Screenshot da página inicial
            try:
                self.driver.save_screenshot("patentscope_01_search_page.png")
                logging.info("Screenshot salvo: patentscope_01_search_page.png")
            except:
                pass

            # Constrói query
            query = self.construir_query(termo_busca, campo, pais, data_inicio, data_fim)
            logging.info(f"Query de busca: {query}")

            # Tenta localizar campo de busca com múltiplos seletores
            # Usa element_to_be_clickable em vez de apenas presence
            search_input = None
            search_selectors = [
                # Seletores corretos identificados pela análise da página
                (By.ID, "simpleSearchForm:fpSearch:input"),
                (By.NAME, "simpleSearchForm:fpSearch:input"),
                (By.CSS_SELECTOR, "#simpleSearchForm\\:fpSearch\\:input"),  # Escaped :
                # Fallbacks para outras versões da página
                (By.ID, "simpleSearchSearchTerm"),
                (By.NAME, "simpleSearchSearchTerm"),
                (By.CSS_SELECTOR, "input[type='text'][name*='Search']"),
                (By.CSS_SELECTOR, "input[type='text'][name*='search']"),
                (By.XPATH, "//input[@type='text' and contains(@name, 'Search')]"),
                (By.XPATH, "//input[@type='text']")  # Último recurso: qualquer input text visível
            ]

            for selector_type, selector_value in search_selectors:
                try:
                    logging.info(f"Tentando seletor: {selector_type} = {selector_value}")
                    # Aguarda elemento ser CLICÁVEL, não apenas presente
                    search_input = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    logging.info(f"✅ Campo de busca CLICÁVEL encontrado: {selector_type}")
                    break
                except TimeoutException:
                    logging.debug(f"Timeout para seletor: {selector_type}")
                    continue
                except Exception as e:
                    logging.debug(f"Erro com seletor {selector_type}: {e}")
                    continue

            if not search_input:
                logging.error("❌ Campo de busca não encontrado com nenhum seletor")
                # Salva screenshot para debug
                self.driver.save_screenshot("patentscope_debug.png")
                logging.info("Screenshot salvo: patentscope_debug.png")

                # Tenta listar inputs disponíveis para debug
                logging.info("Listando inputs disponíveis...")
                try:
                    inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    visible_inputs = [inp for inp in inputs if inp.is_displayed()]
                    logging.info(f"Inputs visíveis: {len(visible_inputs)}")
                    for i, inp in enumerate(visible_inputs[:5], 1):
                        try:
                            inp_id = inp.get_attribute('id') or 'N/A'
                            inp_name = inp.get_attribute('name') or 'N/A'
                            inp_type = inp.get_attribute('type') or 'N/A'
                            logging.info(f"  {i}. type={inp_type}, id={inp_id}, name={inp_name}")
                        except:
                            pass
                except:
                    pass

                return []

            # Preenche campo de busca
            logging.info("Preenchendo campo de busca...")
            try:
                # Scroll até o elemento
                self.driver.execute_script("arguments[0].scrollIntoView(true);", search_input)
                time.sleep(0.5)

                # Clica no elemento primeiro (garante foco)
                search_input.click()
                time.sleep(0.3)

                # Limpa e preenche
                search_input.clear()
                search_input.send_keys(query)
                time.sleep(1)
                logging.info("✅ Campo preenchido")

                # Screenshot após preencher
                try:
                    self.driver.save_screenshot("patentscope_02_search_filled.png")
                    logging.info("Screenshot salvo: patentscope_02_search_filled.png")
                except:
                    pass

            except Exception as e:
                logging.error(f"Erro ao preencher campo: {e}")
                return []

            # Click no botão de busca - tenta múltiplos seletores
            search_button = None
            button_selectors = [
                (By.ID, "simpleSearchSubmitButton"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Search')]"),
                (By.CSS_SELECTOR, ".search-button"),
                (By.NAME, "submit")
            ]

            for selector_type, selector_value in button_selectors:
                try:
                    search_button = self.driver.find_element(selector_type, selector_value)
                    logging.info(f"Botão de busca encontrado com: {selector_type}")
                    break
                except:
                    continue

            if search_button:
                try:
                    # Scroll até o botão
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", search_button)
                    time.sleep(0.3)
                    search_button.click()
                    logging.info("✅ Botão clicado")
                except Exception as e:
                    # Se falhar ao clicar, usa Enter
                    logging.warning(f"Erro ao clicar no botão ({e}), usando Enter")
                    from selenium.webdriver.common.keys import Keys
                    search_input.send_keys(Keys.RETURN)
            else:
                # Fallback: pressiona Enter no campo de busca
                logging.info("Botão não encontrado, pressionando Enter")
                from selenium.webdriver.common.keys import Keys
                search_input.send_keys(Keys.RETURN)

            # Aguarda resultados carregarem
            logging.info("Aguardando resultados...")
            time.sleep(5)  # Aguarda inicial para página processar

            # Screenshot após submeter busca
            try:
                self.driver.save_screenshot("patentscope_loading.png")
                logging.info("Screenshot salvo: patentscope_loading.png")
            except:
                pass

            # Verifica se chegamos na página de resultados
            current_url = self.driver.current_url
            logging.info(f"URL atual após busca: {current_url}")

            if 'result.jsf' not in current_url:
                logging.warning(f"Não está na página de resultados (URL: {current_url})")
                self.driver.save_screenshot("patentscope_wrong_page.png")
                return []

            # Procura tabela de resultados com múltiplas estratégias
            results_table_found = False

            # Estratégia 1: Por classe
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "resultListTable"))
                )
                results_table_found = True
                logging.info("✅ Tabela encontrada por classe 'resultListTable'")
            except TimeoutException:
                logging.debug("Tabela não encontrada por classe 'resultListTable'")

            # Estratégia 2: Por ID ou atributos comuns
            if not results_table_found:
                try:
                    # Procura tabela com ID que contenha 'result'
                    self.driver.find_element(By.XPATH, "//table[contains(@id, 'result') or contains(@class, 'result')]")
                    results_table_found = True
                    logging.info("✅ Tabela encontrada por atributo result")
                except:
                    pass

            # Estratégia 3: Procura tabela com muitas linhas (provavelmente resultados)
            if not results_table_found:
                try:
                    all_tables = self.driver.find_elements(By.TAG_NAME, "table")
                    logging.info(f"📊 Total de tabelas na página: {len(all_tables)}")

                    # Procura tabela com mais de 3 linhas (cabeçalho + resultados)
                    for table in all_tables:
                        try:
                            rows = table.find_elements(By.TAG_NAME, "tr")
                            if len(rows) > 3:
                                # Verifica se tem links para detalhes de patentes
                                links = table.find_elements(By.TAG_NAME, "a")
                                if len(links) > 0:
                                    results_table_found = True
                                    logging.info(f"✅ Tabela de resultados identificada: {len(rows)} linhas, {len(links)} links")
                                    break
                        except:
                            continue
                except Exception as e:
                    logging.debug(f"Erro procurando tabelas: {e}")

            if not results_table_found:
                logging.warning("⚠️ Nenhuma tabela de resultados identificada")
                self.driver.save_screenshot("patentscope_no_table.png")
                logging.info("Screenshot salvo: patentscope_no_table.png")

                # Verifica mensagem de "sem resultados"
                try:
                    no_results = self.driver.find_element(By.XPATH, "//*[contains(text(), 'No results') or contains(text(), 'No se encontraron') or contains(text(), 'Nenhum resultado')]")
                    logging.info("Página indica: Nenhum resultado encontrado")
                    return []
                except:
                    pass

                # Continua mesmo sem confirmar tabela - pode ter resultados
                logging.info("Tentando extrair dados mesmo assim...")

            time.sleep(2)  # Aguarda renderização completa

            # Screenshot final com resultados
            try:
                self.driver.save_screenshot("patentscope_03_results.png")
                logging.info("Screenshot salvo: patentscope_03_results.png")
            except:
                pass

            # Extrai resultados da página atual
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            patentes = self._extrair_dados_patentes_selenium(soup, termo_busca, campo)

            logging.info(f"Página 1: {len(patentes)} patentes extraídas")

            # Se precisamos de mais resultados, tenta próximas páginas
            pagina_atual = 1
            max_paginas = 10  # Limite de segurança

            while len(patentes) < limite and pagina_atual < max_paginas:
                # Procura botão "próxima página" ou link de paginação
                try:
                    # Tenta múltiplos seletores para próxima página
                    next_button = None
                    next_selectors = [
                        (By.LINK_TEXT, "Next"),
                        (By.LINK_TEXT, "›"),
                        (By.LINK_TEXT, "»"),
                        (By.CSS_SELECTOR, "a.next"),
                        (By.CSS_SELECTOR, "a[title*='Next']"),
                        (By.XPATH, "//a[contains(text(), 'Next') or contains(text(), 'next')]"),
                        (By.XPATH, "//a[contains(@class, 'next') or contains(@class, 'Next')]"),
                        (By.XPATH, "//a[@title='Next page']")
                    ]

                    for selector_type, selector_value in next_selectors:
                        try:
                            next_button = self.driver.find_element(selector_type, selector_value)
                            if next_button.is_displayed() and next_button.is_enabled():
                                logging.info(f"Botão 'próxima página' encontrado: {selector_type}")
                                break
                            else:
                                next_button = None
                        except:
                            continue

                    if not next_button:
                        logging.info("Não há mais páginas disponíveis")
                        break

                    # Clica no botão próxima página
                    logging.info(f"Navegando para página {pagina_atual + 1}...")
                    next_button.click()
                    time.sleep(5)  # Aguarda carregar

                    # Screenshot da nova página
                    try:
                        self.driver.save_screenshot(f"patentscope_03_results_page{pagina_atual + 1}.png")
                    except:
                        pass

                    # Extrai dados da nova página
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    patentes_pagina = self._extrair_dados_patentes_selenium(soup, termo_busca, campo)

                    if len(patentes_pagina) == 0:
                        logging.info("Página sem resultados, parando paginação")
                        break

                    patentes.extend(patentes_pagina)
                    pagina_atual += 1

                    logging.info(f"Página {pagina_atual}: +{len(patentes_pagina)} patentes (total: {len(patentes)})")

                    # Verifica se já temos o suficiente
                    if len(patentes) >= limite:
                        break

                except Exception as e:
                    logging.warning(f"Erro na paginação: {e}")
                    break

            # Limita ao número solicitado
            patentes = patentes[:limite]

            logging.info(f"✅ Total extraído: {len(patentes)} patentes de {pagina_atual} página(s)")

        except TimeoutException as e:
            logging.error(f"Timeout ao acessar PatentScope: {e}")
        except WebDriverException as e:
            logging.error(f"Erro no WebDriver: {e}")
        except Exception as e:
            logging.error(f"Erro na busca com Selenium: {e}")
            import traceback
            traceback.print_exc()

        return patentes

    def _extrair_dados_patentes_selenium(self, soup: BeautifulSoup, termo_busca: str, campo: str) -> List[Dict]:
        """
        Extrai dados de patentes do HTML do PatentScope

        Args:
            soup: BeautifulSoup object da página de resultados
            termo_busca: Termo de busca usado
            campo: Campo de busca usado

        Returns:
            Lista de patentes extraídas
        """
        patentes = []

        try:
            # Procura pela tabela de resultados com múltiplas estratégias
            result_table = None

            # Estratégia 1: Por classe específica
            result_table = soup.find('table', class_='resultListTable')

            # Estratégia 2: Por ID ou atributos
            if not result_table:
                result_table = soup.find('table', id=lambda x: x and 'result' in x.lower())

            # Estratégia 3: Procura tabela com links para detail.jsf (patentes)
            if not result_table:
                all_tables = soup.find_all('table')
                logging.info(f"Procurando em {len(all_tables)} tabelas...")

                for table in all_tables:
                    # Procura links que apontam para detalhes de patentes
                    links = table.find_all('a', href=lambda x: x and 'detail.jsf' in x)
                    if len(links) > 0:
                        result_table = table
                        logging.info(f"✅ Tabela identificada com {len(links)} links de patentes")
                        break

            if not result_table:
                logging.warning("⚠️ Tabela de resultados não encontrada em nenhuma estratégia")
                return []

            # Procura pelas linhas de resultados
            result_rows = result_table.find_all('tr', class_=['resultListEvenRow', 'resultListOddRow'])

            if not result_rows:
                # Tenta formato alternativo
                result_rows = result_table.find_all('tr')[1:]  # Pula cabeçalho

            logging.info(f"Encontradas {len(result_rows)} linhas de resultados")

            for idx, row in enumerate(result_rows, 1):
                try:
                    patente = {}

                    # Extrai células da linha
                    cells = row.find_all('td')

                    logging.debug(f"Linha {idx}: {len(cells)} células")

                    if len(cells) < 1:
                        logging.debug(f"  Pulando linha {idx}: sem células")
                        continue

                    # Número de publicação (geralmente primeira coluna ou em link)
                    pub_link = row.find('a', href=lambda x: x and 'detail.jsf' in x)
                    detail_url = ''
                    if pub_link:
                        pub_number_elem = pub_link.find('span') or pub_link
                        patente['publicationNumber'] = pub_number_elem.get_text(strip=True)

                        # Extrai link de detalhes
                        href = pub_link.get('href', '')
                        if href:
                            # Se for URL relativa, constrói URL completa
                            if href.startswith('/'):
                                detail_url = f"{self.config.BASE_URL}{href}"
                            elif href.startswith('http'):
                                detail_url = href
                            else:
                                detail_url = f"{self.config.BASE_URL}/search/en/{href}"
                    else:
                        # Tenta primeira célula
                        patente['publicationNumber'] = cells[0].get_text(strip=True)

                    patente['detailUrl'] = detail_url

                    # Título - tenta múltiplas estratégias
                    title = ''

                    # Estratégia 1: Span com classe 'title'
                    title_elem = row.find('span', class_='title')
                    if title_elem:
                        title = title_elem.get_text(strip=True)

                    # Estratégia 2: Link próximo ao publication number (geralmente é o título)
                    if not title and pub_link:
                        title = pub_link.get_text(strip=True)

                    # Estratégia 3: Segunda célula (se houver mais de 1 célula)
                    if not title and len(cells) > 1:
                        # Pega todo o texto da segunda célula, exceto o pub number
                        cell_text = cells[1].get_text(strip=True)
                        # Remove o publication number do texto se estiver lá
                        if pub_num and pub_num in cell_text:
                            cell_text = cell_text.replace(pub_num, '').strip()
                        if len(cell_text) > 10:  # Título deve ter mais de 10 caracteres
                            title = cell_text

                    # Estratégia 4: Procura em todas as células
                    if not title:
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            # Ignora células pequenas e números
                            if len(cell_text) > 20 and not cell_text.isdigit():
                                title = cell_text
                                break

                    patente['title'] = title

                    # Data de publicação
                    date_elem = row.find('span', class_='date')
                    if date_elem:
                        patente['publicationDate'] = date_elem.get_text(strip=True)
                    elif len(cells) > 2:
                        # Tenta terceira célula
                        date_text = cells[2].get_text(strip=True)
                        if len(date_text) <= 15:  # Parece uma data
                            patente['publicationDate'] = date_text

                    # Depositante/Applicant
                    applicant_elem = row.find('span', class_='applicant')
                    if applicant_elem:
                        applicants_text = applicant_elem.get_text(strip=True)
                        patente['applicants'] = [app.strip() for app in applicants_text.split(';')]
                    else:
                        patente['applicants'] = []

                    # Inventores
                    inventor_elem = row.find('span', class_='inventor')
                    if inventor_elem:
                        inventors_text = inventor_elem.get_text(strip=True)
                        patente['inventors'] = [inv.strip() for inv in inventors_text.split(';')]
                    else:
                        patente['inventors'] = []

                    # Abstract (se disponível na listagem)
                    abstract_elem = row.find('div', class_='abstract') or row.find('p', class_='abstract')
                    if abstract_elem:
                        patente['abstract'] = abstract_elem.get_text(strip=True)[:500]  # Limita tamanho
                    else:
                        patente['abstract'] = ''

                    # Classificação IPC
                    ipc_elem = row.find('span', class_=['ipc', 'classification'])
                    if ipc_elem:
                        patente['ipcClassifications'] = [ipc_elem.get_text(strip=True)]
                    else:
                        patente['ipcClassifications'] = []

                    # Metadados
                    patente['applicationNumber'] = ''  # Não disponível na listagem
                    patente['applicationDate'] = ''
                    patente['cpcClassifications'] = []
                    patente['priorityNumber'] = ''
                    patente['priorityDate'] = ''
                    patente['pctNumber'] = ''
                    patente['termo_busca'] = termo_busca
                    patente['campo_busca'] = campo
                    patente['fonte'] = 'PatentScope (REAL)'
                    patente['timestamp_coleta'] = datetime.now().isoformat()

                    # Valida campos mínimos
                    pub_num = patente.get('publicationNumber', '')
                    title = patente.get('title', '')

                    logging.debug(f"  Linha {idx}: pub_num='{pub_num[:30] if pub_num else 'N/A'}', title='{title[:40] if title else 'N/A'}'")

                    if pub_num and title:
                        patentes.append(patente)
                        logging.info(f"✅ Patente {len(patentes)} extraída: {pub_num}")
                    else:
                        logging.warning(f"⚠️ Linha {idx} ignorada: pub_num={'OK' if pub_num else 'FALTA'}, title={'OK' if title else 'FALTA'}")

                except Exception as e:
                    logging.warning(f"❌ Erro na linha {idx}: {e}")
                    continue

        except Exception as e:
            logging.error(f"Erro ao processar HTML de resultados: {e}")
            import traceback
            traceback.print_exc()

        return patentes

    def _gerar_dados_demonstracao(self, termo_busca: str, limite: int, campo: str, pais: Optional[str]) -> List[Dict]:
        """
        Gera dados de demonstração realistas para testes

        NOTA: Este método retorna dados fictícios para demonstração.
        Para uso em produção, substitua por implementação real com:
        - Selenium para web scraping
        - EPO OPS API
        - Google Patents API
        """
        import random
        from datetime import datetime, timedelta

        patentes_demo = []

        # Empresas farmacêuticas realistas
        empresas = [
            "Novo Nordisk A/S", "Eli Lilly and Company", "Sanofi",
            "Pfizer Inc", "Merck & Co", "AstraZeneca", "GlaxoSmithKline",
            "Johnson & Johnson", "Roche", "Bristol-Myers Squibb"
        ]

        # Países para patentes
        paises_disponiveis = ['US', 'EP', 'WO', 'BR', 'CN', 'JP']
        pais_filtro = pais if pais else random.choice(paises_disponiveis)

        # Classificações IPC comuns para farmacêuticos
        ipc_classes = [
            "A61K 31/00", "A61K 38/00", "A61K 39/00",
            "A61P 3/00", "A61P 3/10", "C07K 14/00"
        ]

        # Gera patentes de demonstração
        for i in range(min(limite, 10)):  # Máximo 10 para demo
            ano = random.randint(2018, 2024)
            mes = random.randint(1, 12)
            dia = random.randint(1, 28)

            pub_date = f"{ano:04d}-{mes:02d}-{dia:02d}"
            app_date = f"{ano-1:04d}-{mes:02d}-{dia:02d}"

            numero = f"{pais_filtro}{ano}{random.randint(100000, 999999)}A1"
            empresa = random.choice(empresas)

            patente = {
                'publicationNumber': numero,
                'applicationNumber': f"PCT/{pais_filtro}{ano-1}/{random.randint(10000, 99999)}",
                'title': f"{termo_busca} pharmaceutical composition and methods of use",
                'abstract': f"The present invention relates to pharmaceutical compositions comprising {termo_busca} or pharmaceutically acceptable salts thereof, and methods of using such compositions for treating metabolic disorders, diabetes, and obesity.",
                'inventors': [
                    f"John {'ABCDEFGH'[i]} Smith",
                    f"Jane {'ABCDEFGH'[i]} Doe"
                ],
                'applicants': [empresa],
                'publicationDate': pub_date,
                'applicationDate': app_date,
                'ipcClassifications': [random.choice(ipc_classes)],
                'cpcClassifications': ["A61K 31/00"],
                'priorityNumber': f"{pais_filtro}{ano-2}{random.randint(100000, 999999)}",
                'priorityDate': f"{ano-2:04d}-{mes:02d}-{dia:02d}",
                'pctNumber': f"PCT/{pais_filtro}{ano-1}/{random.randint(10000, 99999)}",
                'termo_busca': termo_busca,
                'campo_busca': campo,
                'pais': pais_filtro,
                'fonte': 'PatentScope (DEMO)',
                'timestamp_coleta': datetime.now().isoformat(),
                '_demo': True,  # Marca como dados de demonstração
                '_nota': 'Dados fictícios para demonstração. Implemente Selenium ou EPO API para dados reais.'
            }

            patentes_demo.append(patente)

        logging.info(f"Geradas {len(patentes_demo)} patentes de demonstração para '{termo_busca}'")
        return patentes_demo

    def _extrair_dados_patentes(self, html_content: str, termo_busca: str) -> List[Dict]:
        """
        Extrai dados de patentes do HTML ou JSON retornado

        Args:
            html_content: Conteúdo HTML ou JSON da resposta
            termo_busca: Termo de busca usado

        Returns:
            Lista de patentes extraídas
        """
        patentes = []

        try:
            # Tenta parsear como JSON primeiro
            try:
                data = json.loads(html_content)
                if 'patents' in data:
                    for patent_data in data['patents']:
                        patente = self._processar_patente_json(patent_data, termo_busca)
                        if patente:
                            patentes.append(patente)
                return patentes
            except json.JSONDecodeError:
                pass

            # Se não for JSON, faz parsing HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Procura por resultados de patentes no HTML
            # A estrutura exata depende da página do PatentScope
            result_items = soup.find_all('div', class_=['result-item', 'patent-result'])

            for item in result_items:
                try:
                    patente = {
                        'publicationNumber': '',
                        'title': '',
                        'abstract': '',
                        'inventors': [],
                        'applicants': [],
                        'publicationDate': '',
                        'applicationDate': '',
                        'ipcClassifications': [],
                        'termo_busca': termo_busca,
                        'fonte': 'PatentScope',
                        'timestamp_coleta': datetime.now().isoformat()
                    }

                    # Extrai número de publicação
                    pub_num = item.find(['span', 'div'], class_=['pub-number', 'publication-number'])
                    if pub_num:
                        patente['publicationNumber'] = pub_num.get_text(strip=True)

                    # Extrai título
                    title_elem = item.find(['h3', 'h4', 'span'], class_=['title', 'patent-title'])
                    if title_elem:
                        patente['title'] = title_elem.get_text(strip=True)

                    # Extrai resumo se disponível
                    abstract_elem = item.find(['div', 'p'], class_=['abstract', 'summary'])
                    if abstract_elem:
                        patente['abstract'] = abstract_elem.get_text(strip=True)

                    # Extrai data
                    date_elem = item.find(['span', 'div'], class_=['date', 'pub-date'])
                    if date_elem:
                        patente['publicationDate'] = date_elem.get_text(strip=True)

                    # Extrai inventores
                    inventors_elem = item.find(['div', 'span'], class_=['inventors', 'inventor'])
                    if inventors_elem:
                        patente['inventors'] = [inv.strip() for inv in inventors_elem.get_text().split(';')]

                    # Extrai depositantes
                    applicants_elem = item.find(['div', 'span'], class_=['applicants', 'applicant'])
                    if applicants_elem:
                        patente['applicants'] = [app.strip() for app in applicants_elem.get_text().split(';')]

                    if patente['publicationNumber'] or patente['title']:
                        patentes.append(patente)

                except Exception as e:
                    logging.debug(f"Erro ao extrair patente individual: {e}")
                    continue

        except Exception as e:
            logging.error(f"Erro ao processar dados de patentes: {e}")

        return patentes

    def _processar_patente_json(self, data: Dict, termo_busca: str) -> Optional[Dict]:
        """Processa dados de patente em formato JSON"""
        try:
            patente = {
                'publicationNumber': data.get('publicationNumber', ''),
                'applicationNumber': data.get('applicationNumber', ''),
                'title': data.get('title', {}).get('en', '') or data.get('title', ''),
                'abstract': data.get('abstract', {}).get('en', '') or data.get('abstract', ''),
                'inventors': data.get('inventors', []),
                'applicants': data.get('applicants', []),
                'publicationDate': data.get('publicationDate', ''),
                'applicationDate': data.get('applicationDate', ''),
                'ipcClassifications': data.get('ipcClassifications', []),
                'cpcClassifications': data.get('cpcClassifications', []),
                'priorityNumber': data.get('priorityNumber', ''),
                'priorityDate': data.get('priorityDate', ''),
                'pctNumber': data.get('pctNumber', ''),
                'termo_busca': termo_busca,
                'fonte': 'PatentScope',
                'timestamp_coleta': datetime.now().isoformat()
            }

            return patente if patente['publicationNumber'] or patente['title'] else None

        except Exception as e:
            logging.error(f"Erro ao processar patente JSON: {e}")
            return None

    def obter_detalhes_patente(self, numero_publicacao: str) -> Dict:
        """
        Obtém detalhes completos de uma patente específica

        Args:
            numero_publicacao: Número de publicação da patente

        Returns:
            Dicionário com detalhes completos
        """
        logging.info(f"Buscando detalhes da patente: {numero_publicacao}")

        try:
            url = f"{self.config.BASE_URL}/search/en/detail.jsf"
            params = {'docId': numero_publicacao}

            response = self._make_request(url, 'GET', params=params)

            # Processa resposta
            detalhes = self._processar_detalhes_patente(response.text, numero_publicacao)

            return detalhes

        except Exception as e:
            logging.error(f"Erro ao obter detalhes da patente {numero_publicacao}: {e}")
            return {'publicationNumber': numero_publicacao, 'erro': str(e)}

    def _processar_detalhes_patente(self, html_content: str, numero_publicacao: str) -> Dict:
        """Processa detalhes completos da patente"""
        from bs4 import BeautifulSoup

        detalhes = {
            'publicationNumber': numero_publicacao,
            'timestamp_detalhes': datetime.now().isoformat()
        }

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extrai campos detalhados
            # A estrutura específica depende da página de detalhes do PatentScope

            # Título
            title = soup.find(['h1', 'h2'], class_=['title', 'patent-title'])
            if title:
                detalhes['title'] = title.get_text(strip=True)

            # Abstract/Resumo
            abstract = soup.find('div', class_=['abstract', 'summary'])
            if abstract:
                detalhes['abstract'] = abstract.get_text(strip=True)

            # Claims/Reivindicações
            claims = soup.find('div', class_=['claims'])
            if claims:
                detalhes['claims'] = claims.get_text(strip=True)

            # Description/Descrição
            description = soup.find('div', class_=['description'])
            if description:
                detalhes['description'] = description.get_text(strip=True)[:5000]  # Limita tamanho

        except Exception as e:
            logging.error(f"Erro ao processar detalhes: {e}")
            detalhes['erro_processamento'] = str(e)

        return detalhes

    def salvar_dados_final(self, dados: List[Dict], nome_arquivo: str, formato: str = 'json'):
        """
        Salva dados finais com timestamp

        Args:
            dados: Lista de dados para salvar
            nome_arquivo: Nome base do arquivo
            formato: Formato de saída ('json', 'csv', 'excel')
        """
        if not dados:
            logging.warning("Nenhum dado para salvar")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_completo = f"{nome_arquivo}_{timestamp}"

        try:
            # Cria diretório se não existir
            Path("resultados").mkdir(exist_ok=True)

            df = pd.DataFrame(dados)

            if formato.lower() == 'csv':
                filepath = f"resultados/{nome_completo}.csv"
                df.to_csv(filepath, index=False, encoding='utf-8')
            elif formato.lower() == 'json':
                filepath = f"resultados/{nome_completo}.json"
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(dados, f, ensure_ascii=False, indent=2)
            elif formato.lower() == 'excel':
                filepath = f"resultados/{nome_completo}.xlsx"
                df.to_excel(filepath, index=False)

            logging.info(f"Dados salvos: {filepath} ({len(dados)} registros)")

        except Exception as e:
            logging.error(f"Erro ao salvar dados: {e}")
