#!/usr/bin/env python3
"""
Busca Completa PatentScope - JSON + PNG
Extrai TODOS os dados disponíveis e salva JSON + screenshots
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

from patentscope_scraper import PatentScopeScraper
from patentscope_detalhes import enriquecer_patentes_com_detalhes, agrupar_por_publication_number

def main():
    print("="*70)
    print("  🌍 PATENTSCOPE - BUSCA COMPLETA")
    print("  📄 JSON + 📸 PNG Screenshots")
    print("="*70)

    # Parâmetros de busca
    termo = input("\n🔍 Digite o termo de busca (ex: semaglutide): ").strip()
    if not termo:
        termo = "semaglutide"
        print(f"   Usando termo padrão: {termo}")

    try:
        limite_input = input(f"📊 Quantas patentes? (padrão: 50): ").strip()
        limite = int(limite_input) if limite_input else 50
    except:
        limite = 50

    filtrar_pais = input("🌍 Filtrar por país? (S/n): ").strip().lower()
    paises = None
    if filtrar_pais != 'n':
        paises_input = input("   Países (ex: US,EP,WO,CN): ").strip().upper()
        if paises_input:
            paises = [p.strip() for p in paises_input.split(',')]

    usar_login = input("🔐 Usar login WIPO? (s/N): ").strip().lower()
    use_login = usar_login == 's'

    buscar_detalhes = input("📄 Buscar detalhes completos de cada patente? (s/N): ").strip().lower()
    extrair_detalhes = buscar_detalhes == 's'

    if extrair_detalhes:
        try:
            max_detalhes_input = input(f"   Quantas patentes detalhar? (padrão: todas): ").strip()
            max_detalhes = int(max_detalhes_input) if max_detalhes_input else None
        except:
            max_detalhes = None
    else:
        max_detalhes = None

    print(f"\n{'='*70}")
    print(f"  🚀 INICIANDO BUSCA")
    print(f"{'='*70}")
    print(f"   Termo: {termo}")
    print(f"   Limite: {limite}")
    print(f"   Países: {paises if paises else 'Todos'}")
    print(f"   Login: {'Sim (autenticado)' if use_login else 'Não (anônimo)'}")
    print(f"   Buscar detalhes: {'Sim' if extrair_detalhes else 'Não'}")
    if extrair_detalhes and max_detalhes:
        print(f"   Máx. detalhes: {max_detalhes}")
    print(f"{'='*70}\n")

    # Inicializa scraper
    print("🔧 Inicializando scraper...")
    scraper = PatentScopeScraper(
        headless=True,  # True = sem janela do navegador
        use_demo_mode=False,  # False = dados reais
        use_login=use_login  # True = tenta fazer login WIPO
    )

    # Cria diretório para resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta_resultados = Path("resultados") / f"patentscope_{termo}_{timestamp}"
    pasta_resultados.mkdir(parents=True, exist_ok=True)

    print(f"✅ Pasta criada: {pasta_resultados}\n")

    # Executa busca
    all_patents = []

    if paises:
        # Busca por país
        for pais in paises:
            print(f"\n🌍 Buscando em {pais}...")
            patents = scraper.buscar_patentes(
                termo_busca=termo,
                campo='all',
                pais=pais,
                limite=limite
            )

            # Adiciona país aos dados
            for p in patents:
                p['pais_filtro'] = pais

            all_patents.extend(patents)
            print(f"   ✅ {len(patents)} patentes encontradas em {pais}")
    else:
        # Busca geral
        print(f"\n🔍 Buscando patentes...")
        all_patents = scraper.buscar_patentes_simples(termo, limite=limite)

    # Remove duplicatas
    unique_patents = {}
    for p in all_patents:
        pub_num = p.get('publicationNumber', '')
        if pub_num and pub_num not in unique_patents:
            unique_patents[pub_num] = p

    patents_list = list(unique_patents.values())

    print(f"\n{'='*70}")
    print(f"  📊 RESULTADOS")
    print(f"{'='*70}")
    print(f"   Total encontrado: {len(all_patents)}")
    print(f"   Únicas (sem duplicatas): {len(patents_list)}")
    print(f"{'='*70}\n")

    if len(patents_list) == 0:
        print("⚠️  Nenhuma patente encontrada!")
        return

    # Buscar detalhes completos se solicitado
    if extrair_detalhes and len(patents_list) > 0:
        print(f"\n{'='*70}")
        print(f"  🔍 BUSCANDO DETALHES COMPLETOS")
        print(f"{'='*70}")
        print(f"   ⚠️  Isso pode demorar ~5 segundos por patente")
        print(f"   Total de patentes: {len(patents_list)}")
        if max_detalhes:
            print(f"   Detalhando apenas: {max_detalhes}")
        print()

        try:
            patents_list = enriquecer_patentes_com_detalhes(
                patents_list,
                scraper.driver,
                max_detalhes=max_detalhes
            )
            print(f"\n   ✅ Detalhes completos extraídos!")
        except Exception as e:
            print(f"\n   ⚠️  Erro ao buscar detalhes: {e}")
            print(f"   Continuando sem detalhes completos...")

        print(f"{'='*70}\n")

    # Mostra primeiras patentes
    print("📄 Primeiras 5 patentes:\n")
    for i, p in enumerate(patents_list[:5], 1):
        print(f"{i}. {p.get('publicationNumber', 'N/A')}")
        print(f"   {p.get('title', 'N/A')[:70]}...")
        print(f"   📅 {p.get('publicationDate', 'N/A')}")
        print(f"   🏢 {', '.join(p.get('applicants', ['N/A'])[:2])}")
        print()

    # Salva JSON completo
    print("💾 Salvando arquivos...\n")

    # 1. JSON com todas as patentes (agrupado por publicationNumber)
    patents_agrupadas = agrupar_por_publication_number(patents_list)

    json_file = pasta_resultados / f"patents_complete.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(patents_agrupadas, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON completo (agrupado por publicationNumber): {json_file}")
    print(f"   {len(patents_agrupadas)} patentes únicas")

    # 2. JSON com resumo
    summary = {
        "search_info": {
            "termo": termo,
            "data_busca": datetime.now().isoformat(),
            "total_encontrado": len(all_patents),
            "total_unico": len(patents_list),
            "paises_filtro": paises,
            "limite": limite,
            "detalhes_completos": extrair_detalhes
        },
        "statistics": {
            "por_pais": {},
            "por_ano": {},
            "top_applicants": {},
            "top_inventors": {}
        },
        "patents": patents_list
    }

    # Estatísticas por país
    for p in patents_list:
        pub_num = p.get('publicationNumber', '')
        if pub_num and len(pub_num) >= 2:
            country = pub_num[:2]
            summary["statistics"]["por_pais"][country] = \
                summary["statistics"]["por_pais"].get(country, 0) + 1

    # Estatísticas por ano
    for p in patents_list:
        date = p.get('publicationDate', '')
        if date and len(date) >= 4:
            year = date[:4]
            summary["statistics"]["por_ano"][year] = \
                summary["statistics"]["por_ano"].get(year, 0) + 1

    # Top depositantes
    for p in patents_list:
        for app in p.get('applicants', []):
            if app:
                summary["statistics"]["top_applicants"][app] = \
                    summary["statistics"]["top_applicants"].get(app, 0) + 1

    # Top inventores
    for p in patents_list:
        for inv in p.get('inventors', []):
            if inv:
                summary["statistics"]["top_inventors"][inv] = \
                    summary["statistics"]["top_inventors"].get(inv, 0) + 1

    summary_file = pasta_resultados / f"summary_with_stats.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON com estatísticas: {summary_file}")

    # 3. CSV
    import pandas as pd
    df = pd.DataFrame(patents_list)
    csv_file = pasta_resultados / f"patents.csv"
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')  # utf-8-sig para Excel
    print(f"✅ CSV: {csv_file}")

    # 4. Copia screenshots existentes
    print(f"\n📸 Screenshots disponíveis:")
    screenshot_files = [
        "patentscope_debug.png",
        "patentscope_after_search.png",
        "improved_1_inicial.png",
        "improved_2_preenchido.png",
        "improved_3_resultados.png"
    ]

    for screenshot in screenshot_files:
        source = Path(screenshot)
        if source.exists():
            dest = pasta_resultados / screenshot
            import shutil
            shutil.copy(source, dest)
            print(f"   ✅ {screenshot}")

    # Resumo final
    print(f"\n{'='*70}")
    print(f"  ✅ BUSCA CONCLUÍDA")
    print(f"{'='*70}")
    print(f"\n📁 Arquivos salvos em: {pasta_resultados}")
    print(f"\n📄 Arquivos gerados:")
    print(f"   1. patents_complete.json - {len(patents_list)} patentes completas")
    print(f"   2. summary_with_stats.json - Resumo com estatísticas")
    print(f"   3. patents.csv - Planilha Excel")
    print(f"   4. Screenshots PNG da busca")

    print(f"\n📊 Estatísticas:")
    print(f"   Países: {len(summary['statistics']['por_pais'])}")
    print(f"   Anos: {len(summary['statistics']['por_ano'])}")
    print(f"   Depositantes únicos: {len(summary['statistics']['top_applicants'])}")
    print(f"   Inventores únicos: {len(summary['statistics']['top_inventors'])}")

    # Top 5 países
    if summary['statistics']['por_pais']:
        print(f"\n🌍 Top 5 Países:")
        top_countries = sorted(
            summary['statistics']['por_pais'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        for country, count in top_countries:
            print(f"   {country}: {count} patentes")

    # Top 5 depositantes
    if summary['statistics']['top_applicants']:
        print(f"\n🏢 Top 5 Depositantes:")
        top_applicants = sorted(
            summary['statistics']['top_applicants'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        for applicant, count in top_applicants:
            print(f"   {applicant[:50]}: {count} patentes")

    print(f"\n{'='*70}")
    print("  🎉 SUCESSO!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Busca interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
