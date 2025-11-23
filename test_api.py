"""
Script de teste simples para verificar a API localmente
"""
import requests
import json


def test_health():
    """Testa health check"""
    print("🔍 Testando health check...")
    response = requests.get("http://localhost:8000/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()


def test_search():
    """Testa busca por molécula"""
    print("🔍 Testando busca por molécula (glucose)...")
    
    payload = {
        "molecule": "glucose",
        "search_type": "exact",
        "page": 1,
        "page_size": 5
    }
    
    response = requests.post(
        "http://localhost:8000/search",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Query: {data['query']}")
        print(f"Total resultados: {data['pagination']['total_results']}")
        print(f"Página: {data['pagination']['current_page']}/{data['pagination']['total_pages']}")
        
        print(f"\n📄 Primeiros resultados:")
        for i, patent in enumerate(data['results'][:3], 1):
            print(f"\n{i}. {patent['publication_number']}")
            print(f"   Título: {patent['title'][:100]}...")
            print(f"   Aplicantes: {', '.join(patent['applicants'][:2])}")
            print(f"   URL: {patent['url']}")
    else:
        print(f"❌ Erro: {response.text}")
    
    print()


def test_pagination():
    """Testa paginação"""
    print("🔍 Testando paginação...")
    
    # Página 1
    payload = {
        "molecule": "aspirin",
        "page": 1,
        "page_size": 5
    }
    
    response = requests.post("http://localhost:8000/search", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Página 1: {len(data['results'])} resultados")
        print(f"Has next: {data['pagination']['has_next']}")
        
        if data['pagination']['has_next']:
            # Página 2
            payload['page'] = 2
            response = requests.post("http://localhost:8000/search", json=payload)
            data = response.json()
            print(f"Página 2: {len(data['results'])} resultados")
            print(f"Has previous: {data['pagination']['has_previous']}")
    else:
        print(f"❌ Erro: {response.text}")
    
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TESTE DA API - PATENT SCRAPER")
    print("=" * 60)
    print()
    
    try:
        test_health()
        test_search()
        test_pagination()
        
        print("✅ Todos os testes concluídos!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar à API")
        print("   Certifique-se que o servidor está rodando:")
        print("   python -m uvicorn app.main:app --reload")
    
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
