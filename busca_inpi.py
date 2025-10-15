#!/usr/bin/env python3
"""
INPI Scraper - Busca Unificada e Inteligente
Combina busca completa (marcas + patentes) com geração inteligente de termos
Execute: python busca_inpi.py
"""

import sys
import logging
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Configura encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# Logging configurável
log_level = os.getenv('LOG_LEVEL', 'WARNING')
logging.basicConfig(level=getattr(logging, log_level.upper()))

class GerenciadorTermos:
    """Gerencia dicionário de termos e geração inteligente"""

    def __init__(self, arquivo_dicionario='dicionario_termos.json'):
        self.arquivo_dicionario = Path(arquivo_dicionario)
        self.dicionario = self._carregar_dicionario()
        self.claude_disponivel = self._verificar_claude()

    def _carregar_dicionario(self):
        """Carrega dicionário de termos do arquivo JSON"""
        try:
            if self.arquivo_dicionario.exists():
                with open(self.arquivo_dicionario, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"⚠️ Dicionário não encontrado: {self.arquivo_dicionario}")
                return {"termos_farmaceuticos": {}, "configuracoes": {"max_termos_por_busca": 6}}
        except Exception as e:
            print(f"⚠️ Erro ao carregar dicionário: {e}")
            return {"termos_farmaceuticos": {}, "configuracoes": {"max_termos_por_busca": 6}}

    def _verificar_claude(self):
        """Verifica se Claude está disponível"""
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key and len(api_key) > 20:
                import anthropic
                return True
        except ImportError:
            pass
        return False

    def gerar_termos_alternativos(self, termo_original, max_termos=None):
        """Gera termos alternativos usando dicionário + Claude"""

        if max_termos is None:
            max_termos = self.dicionario.get('configuracoes', {}).get('max_termos_por_busca', 6)

        print(f"🔍 Gerando termos alternativos para '{termo_original}'...")

        # 1. Busca no dicionário JSON
        termos_dicionario = self._buscar_no_dicionario(termo_original, max_termos)

        if len(termos_dicionario) > 1:
            print(f"📚 Encontrado no dicionário farmacêutico ({len(termos_dicionario)} termos)")
            return termos_dicionario

        # 2. Tenta Claude se disponível
        if self.claude_disponivel:
            termos_claude = self._gerar_com_claude(termo_original, max_termos)
            if termos_claude and len(termos_claude) > 1:
                print(f"🤖 Gerado pelo Claude ({len(termos_claude)} termos)")
                return termos_claude

        # 3. Fallback: variações básicas
        print(f"📝 Usando variações básicas")
        return self._gerar_variacoes_basicas(termo_original, max_termos)

    def _buscar_no_dicionario(self, termo_original, max_termos):
        """Busca termos no dicionário JSON"""
        termos = [termo_original]
        termo_upper = termo_original.upper()

        # Busca direta nos termos farmacêuticos
        termos_farm = self.dicionario.get('termos_farmaceuticos', {})

        for chave, dados in termos_farm.items():
            if (chave.upper() in termo_upper or
                termo_upper in chave.upper() or
                any(sin.upper() in termo_upper for sin in dados.get('sinonimos', []))):

                # Adiciona termos prioritários primeiro
                for termo in dados.get('prioridade', [])[:3]:
                    if termo not in termos:
                        termos.append(termo)

                # Adiciona nomes comerciais
                for termo in dados.get('nomes_comerciais', [])[:2]:
                    if termo not in termos and len(termos) < max_termos:
                        termos.append(termo)

                # Adiciona mecanismo de ação
                for termo in dados.get('mecanismo_acao', [])[:2]:
                    if termo not in termos and len(termos) < max_termos:
                        termos.append(termo)

                # Adiciona área terapêutica
                for termo in dados.get('area_terapeutica', [])[:1]:
                    if termo not in termos and len(termos) < max_termos:
                        termos.append(termo)

                break

        return termos[:max_termos]

    def _gerar_com_claude(self, termo_original, max_termos):
        """Gera termos usando Claude"""
        try:
            import anthropic

            api_key = os.getenv('ANTHROPIC_API_KEY')
            client = anthropic.Anthropic(api_key=api_key)

            prompt = f"""
            Para o termo farmacêutico/médico "{termo_original}", gere exatamente {max_termos-1} termos alternativos para busca no INPI brasileiro.

            Foque em:
            - Nomes comerciais principais
            - Princípios ativos relacionados
            - Área terapêutica
            - Mecanismo de ação
            - Competidores da mesma classe

            Retorne APENAS um array JSON:
            ["termo1", "termo2", "termo3"]
            """

            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )

            resposta = response.content[0].text.strip()
            resposta_limpa = resposta.replace('```json', '').replace('```', '').strip()

            termos_claude = json.loads(resposta_limpa)

            if isinstance(termos_claude, list):
                return [termo_original] + termos_claude[:max_termos-1]

        except Exception as e:
            print(f"⚠️ Claude indisponível: {str(e)[:30]}...")

        return None

    def _gerar_variacoes_basicas(self, termo_original, max_termos):
        """Gera variações básicas do termo"""
        termos = [termo_original]

        # Variações de case
        if termo_original != termo_original.lower():
            termos.append(termo_original.lower())
        if termo_original != termo_original.upper():
            termos.append(termo_original.upper())
        if termo_original != termo_original.title():
            termos.append(termo_original.title())

        # Remove duplicatas
        termos_unicos = []
        for termo in termos:
            if termo not in termos_unicos:
                termos_unicos.append(termo)

        return termos_unicos[:max_termos]

class BuscadorINPI:
    """Executor de buscas no INPI"""

    def __init__(self):
        self.gerenciador_termos = GerenciadorTermos()

    def executar_busca_completa(self, termo_principal, limite_por_termo=8, buscar_marcas=True, buscar_patentes=True, coletar_detalhes=True):
        """Executa busca completa com múltiplos termos

        Args:
            termo_principal: Termo principal para busca
            limite_por_termo: Quantidade de resultados por termo
            buscar_marcas: Se deve buscar marcas (padrão: True)
            buscar_patentes: Se deve buscar patentes (padrão: True)
            coletar_detalhes: Se deve coletar detalhes completos (padrão: True)
        """

        print("🚀 INPI SCRAPER - BUSCA UNIFICADA E INTELIGENTE")
        print("=" * 60)

        # Gera termos alternativos
        termos_busca = self.gerenciador_termos.gerar_termos_alternativos(termo_principal)

        print(f"\n📋 Termos que serão buscados ({len(termos_busca)}):")
        for i, termo in enumerate(termos_busca, 1):
            print(f"   {i}. {termo}")

        # Confirma busca
        if len(termos_busca) > 1:
            confirmacao = input(f"\n🤔 Continuar busca com {len(termos_busca)} termos? (S/n): ").strip().lower()
            if confirmacao == 'n':
                return None, None, {}

        # Inicializa scraper
        print(f"\n🚀 Inicializando scraper INPI...")

        try:
            from inpi_scraper import INPIScraper

            scraper = INPIScraper(
                min_delay=1.0,
                max_delay=3.0,
                check_robots=False,
                headless=True
            )
            scraper.session.timeout = 12

            if not scraper.logged_in:
                print("❌ Falha no login INPI")
                return None, None, {}

            print("✅ Login INPI realizado com sucesso")

        except Exception as e:
            print(f"❌ Erro ao inicializar scraper: {e}")
            return None, None, {}

        # Executa buscas
        todas_marcas = []
        todas_patentes = []
        estatisticas = {}

        for i, termo in enumerate(termos_busca, 1):
            print(f"\n{'='*50}")
            print(f"🔍 [{i}/{len(termos_busca)}] Buscando: '{termo}'")
            print(f"{'='*50}")

            marcas_termo = []
            patentes_termo = []

            # Busca MARCAS
            if buscar_marcas:
                print(f"📋 Buscando marcas{' (COM detalhes)' if coletar_detalhes else ''}...")
                try:
                    marcas_termo = scraper.buscar_marcas(
                        termo_busca=termo,
                        limite=limite_por_termo,
                        salvar_incremental=False,
                        coletar_detalhes=coletar_detalhes
                    )
                    print(f"   ✅ {len(marcas_termo)} marcas encontradas")

                    # Adiciona marcas únicas
                    for marca in marcas_termo:
                        numero = marca.get('numero_processo')
                        if not any(m.get('numero_processo') == numero for m in todas_marcas):
                            marca['encontrado_por_termo'] = termo
                            todas_marcas.append(marca)

                except Exception as e:
                    print(f"   ⚠️ Erro nas marcas: {str(e)[:40]}...")

            # Busca PATENTES
            if buscar_patentes:
                print(f"📋 Buscando patentes...")
                try:
                    scraper.session.timeout = 10  # Timeout menor para patentes

                    patentes_termo = scraper.buscar_patentes(
                        termo_busca=termo,
                        limite=min(limite_por_termo, 5),  # Limite menor
                        salvar_incremental=False
                    )
                    print(f"   ✅ {len(patentes_termo)} patentes encontradas")

                    # Adiciona patentes únicas
                    for patente in patentes_termo:
                        numero = patente.get('numero_processo')
                        if not any(p.get('numero_processo') == numero for p in todas_patentes):
                            patente['encontrado_por_termo'] = termo
                            todas_patentes.append(patente)

                except Exception as e:
                    print(f"   ⚠️ Patentes timeout (normal): {str(e)[:30]}...")

            # Estatísticas por termo
            estatisticas[termo] = {
                'marcas': len(marcas_termo),
                'patentes': len(patentes_termo),
                'total': len(marcas_termo) + len(patentes_termo)
            }

            # Mostra melhor termo até agora
            if marcas_termo or patentes_termo:
                print(f"   🎯 '{termo}' foi produtivo!")

        return todas_marcas, todas_patentes, estatisticas

    def salvar_e_exibir_resultados(self, termo_principal, todas_marcas, todas_patentes, estatisticas):
        """Salva e exibe os resultados da busca"""

        total_marcas = len(todas_marcas)
        total_patentes = len(todas_patentes)
        total_geral = total_marcas + total_patentes

        print(f"\n{'='*70}")
        print("📊 RESUMO FINAL DA BUSCA UNIFICADA")
        print(f"{'='*70}")
        print(f"   🎯 Termo principal: {termo_principal}")
        print(f"   📋 Total de marcas únicas: {total_marcas}")
        print(f"   🔬 Total de patentes únicas: {total_patentes}")
        print(f"   🏆 Total geral: {total_geral}")
        print(f"   ⏰ Concluído em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        # Estatísticas por termo
        print(f"\n📈 DESEMPENHO POR TERMO:")
        for termo, stats in estatisticas.items():
            emoji = "🎯" if stats['total'] > 0 else "❌"
            print(f"   {emoji} {termo:<15} | M:{stats['marcas']:>2} P:{stats['patentes']:>2} = {stats['total']:>2}")

        # Salva resultados
        if total_geral > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            Path("resultados").mkdir(exist_ok=True)

            from inpi_scraper import INPIScraper
            scraper = INPIScraper(headless=True)  # Só para usar salvar_dados_final

            if todas_marcas:
                arquivo_marcas = f"resultados/marcas_unificado_{termo_principal}_{timestamp}"
                scraper.salvar_dados_final(todas_marcas, arquivo_marcas, "json")
                scraper.salvar_dados_final(todas_marcas, arquivo_marcas, "csv")
                print(f"\n💾 Marcas salvas:")
                print(f"   📄 {arquivo_marcas}.json")
                print(f"   📊 {arquivo_marcas}.csv")

            if todas_patentes:
                arquivo_patentes = f"resultados/patentes_unificado_{termo_principal}_{timestamp}"
                scraper.salvar_dados_final(todas_patentes, arquivo_patentes, "json")
                scraper.salvar_dados_final(todas_patentes, arquivo_patentes, "csv")
                print(f"\n💾 Patentes salvas:")
                print(f"   📄 {arquivo_patentes}.json")
                print(f"   📊 {arquivo_patentes}.csv")

            # Salva relatório completo
            relatorio = {
                'termo_principal': termo_principal,
                'estatisticas_por_termo': estatisticas,
                'total_marcas': total_marcas,
                'total_patentes': total_patentes,
                'marcas': todas_marcas,
                'patentes': todas_patentes,
                'timestamp': datetime.now().isoformat(),
                'configuracao': {
                    'dicionario_usado': self.gerenciador_termos.arquivo_dicionario.name,
                    'claude_disponivel': self.gerenciador_termos.claude_disponivel
                }
            }

            arquivo_completo = f"resultados/relatorio_unificado_{termo_principal}_{timestamp}.json"
            with open(arquivo_completo, 'w', encoding='utf-8') as f:
                json.dump(relatorio, f, ensure_ascii=False, indent=2, default=str)

            print(f"\n📋 Relatório completo: {arquivo_completo}")

        # Preview dos melhores resultados
        if todas_marcas:
            print(f"\n🏆 MELHORES MARCAS (top 3):")
            for i, marca in enumerate(todas_marcas[:3], 1):
                nome = marca.get('classe_ncl', 'N/A')
                termo = marca.get('encontrado_por_termo', 'N/A')
                processo = marca.get('numero_processo', 'N/A')

                print(f"   {i}. {nome}")
                print(f"      📋 Processo: {processo}")
                print(f"      🔍 Encontrado por: '{termo}'")

        if todas_patentes:
            print(f"\n🔬 MELHORES PATENTES (top 3):")
            for i, patente in enumerate(todas_patentes[:3], 1):
                titulo = patente.get('titulo', 'N/A')
                termo = patente.get('encontrado_por_termo', 'N/A')

                print(f"   {i}. {titulo[:50]}...")
                print(f"      🔍 Encontrado por: '{termo}'")

        if total_geral == 0:
            print(f"\n❌ Nenhum resultado encontrado")
            print("💡 Sugestões:")
            print("   - Termos podem não existir no INPI brasileiro")
            print("   - Tente termos mais genéricos (ex: DIABETES, CANCER)")
            print("   - Verifique se existem registros internacionais")
            print("   - Atualize o dicionário com novos termos")

        return total_geral > 0

def main():
    """Função principal"""

    try:
        buscador = BuscadorINPI()

        # Input do usuário
        print("📝 Configure sua busca:")
        termo_principal = input("Digite o termo principal: ").strip()

        if not termo_principal:
            termo_principal = "ABEMACICLIB"
            print(f"Usando termo padrão: {termo_principal}")

        try:
            limite = int(input("Limite por termo (padrão: 5): ").strip() or "5")
        except ValueError:
            limite = 5

        # Opções de busca (SEMPRE busca marcas E patentes, SEMPRE com detalhes)
        print("\n⚙️ Configuração:")
        print("   ✅ Buscar marcas: SIM")
        print("   ✅ Buscar patentes: SIM")
        print("   ✅ Coletar detalhes completos: SIM")

        confirmacao = input("\nContinuar? (S/n): ").strip().lower()
        if confirmacao == 'n':
            print("❌ Cancelado pelo usuário")
            return

        # Executa busca SEMPRE com marcas E patentes E detalhes
        marcas, patentes, stats = buscador.executar_busca_completa(
            termo_principal=termo_principal,
            limite_por_termo=limite,
            buscar_marcas=True,
            buscar_patentes=True,
            coletar_detalhes=True
        )

        if marcas is not None or patentes is not None:
            sucesso = buscador.salvar_e_exibir_resultados(termo_principal, marcas, patentes, stats)

            if sucesso:
                print(f"\n🎉 BUSCA CONCLUÍDA COM SUCESSO!")
            else:
                print(f"\n⚠️ Busca concluída sem resultados")

    except KeyboardInterrupt:
        print(f"\n⚠️ Cancelado pelo usuário")

    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print(f"\n🏁 EXECUÇÃO FINALIZADA")
        input("Enter para sair...")

if __name__ == "__main__":
    main()