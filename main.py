import requests
import time
import pandas as pd
import random
import os
from datetime import datetime

import dotenv
dotenv.load_dotenv()

# ============================================
# CONFIGURAÇÃO
# ============================================
TOKEN = os.getenv("GITHUB_TOKEN")
if not TOKEN:
    print("❌ ERRO: GITHUB_TOKEN não configurado!")
    exit(1)

HEADERS = {"Authorization": f"Bearer {TOKEN}"}
GRAPHQL_URL = "https://api.github.com/graphql"
REST_URL = "https://api.github.com"

NUM_TRIALS = 30
WARMUP_RUNS = 5

# ============================================
# QUERIES REST
# ============================================
REST_QUERIES = {
"simple": {
    "url": f"{REST_URL}/users/gaearon",
    "desc": "Perfil do usuário"
},
"medium": {
    "url": f"{REST_URL}/repos/facebook/react/issues?per_page=5&state=open",
    "desc": "5 issues do repositório"
},
"complex": {
    "urls": [
        f"{REST_URL}/repos/facebook/react",
        f"{REST_URL}/repos/facebook/react/pulls?per_page=3",
        f"{REST_URL}/repos/facebook/react/commits?per_page=3"
    ],
    "desc": "Repo + PRs + Commits (3 requests)"
}
}

# ============================================
# QUERIES GRAPHQL
# ============================================
GRAPHQL_QUERIES = {
"simple": """
    query {
      user(login: "gaearon") {
        login
        name
        bio
        followers { totalCount }
        following { totalCount }
      }
    }
""",
"medium": """
    query {
      repository(owner: "facebook", name: "react") {
        name
        description
        stargazerCount
        issues(first: 5, states: OPEN) {
          nodes {
            title
            number
            createdAt
          }
        }
      }
    }
""",
"complex": """
    query {
      repository(owner: "facebook", name: "react") {
        name
        stargazerCount
        pullRequests(first: 3, states: OPEN) {
          nodes { title number }
        }
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 3) {
                nodes { messageHeadline oid }
              }
            }
          }
        }
      }
    }
"""
}

# ============================================
# FUNÇÕES DE EXECUÇÃO
# ============================================
def executar_rest(query_name):
    """Executa query REST e retorna tempo + tamanho"""
    query = REST_QUERIES[query_name]

    start = time.perf_counter()

    if "urls" in query:  # Múltiplas requests (complex)
        total_size = 0
        for url in query["urls"]:
            resp = requests.get(url, headers=HEADERS)
            resp.raise_for_status()
            total_size += len(resp.content)
        payload_size = total_size
    else:  # Single request
        resp = requests.get(query["url"], headers=HEADERS)
        resp.raise_for_status()
        payload_size = len(resp.content)

    elapsed = (time.perf_counter() - start) * 1000
    return elapsed, payload_size

def executar_graphql(query_name):
    """Executa query GraphQL e retorna tempo + tamanho"""
    query = GRAPHQL_QUERIES[query_name]
    start = time.perf_counter()
    resp = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
    resp.raise_for_status()
    elapsed = (time.perf_counter() - start) * 1000
    payload_size = len(resp.content)
    return elapsed, payload_size

# ============================================
# EXPERIMENTO PRINCIPAL
# ============================================
def rodar_experimento():
    print("🔬 Iniciando experimento GraphQL vs REST")
    print("=" * 50)

    # Warm-up
    print(f"\n🔥 Realizando {WARMUP_RUNS} warm-up runs...")
    for _ in range(WARMUP_RUNS):
        executar_rest("simple")
        executar_graphql("simple")
    print("✅ Warm-up concluído!\n")

    # Coleta de dados
    results = []
    query_types = ["simple", "medium", "complex"]

    for trial in range(1, NUM_TRIALS + 1):
        print(f"📊 Trial {trial}/{NUM_TRIALS}")
        
        # Randomiza ordem
        apis = ["REST", "GraphQL"]
        random.shuffle(apis)
        random.shuffle(query_types)
        
        for api in apis:
            for qtype in query_types:
                try:
                    if api == "REST":
                        time_ms, size_bytes = executar_rest(qtype)
                    else:
                        time_ms, size_bytes = executar_graphql(qtype)
                    
                    results.append({
                        "query_type": qtype,
                        "api_type": api,
                        "response_time_ms": time_ms,
                        "payload_size_bytes": size_bytes,
                        "trial": trial,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"  ✓ {api:8s} {qtype:8s} - {time_ms:6.2f}ms, {size_bytes:6d} bytes")
                    
                except Exception as e:
                    print(f"  ❌ ERRO {api} {qtype}: {e}")
                
                time.sleep(0.5)  # Evita rate limit

    # Salvar resultados
    df = pd.DataFrame(results)
    filename = "resultados_experimento.csv"
    df.to_csv(filename, index=False)

    print(f"\n✅ Experimento concluído!")
    print(f"📁 Resultados salvos em: {filename}")
    print(f"📈 Total de medições: {len(results)}")

    return df

# ============================================
# EXECUÇÃO
# ============================================
if __name__ == "__main__":
    df = rodar_experimento()

    # Preview dos resultados
    print("\n" + "="*50)
    print("📊 PREVIEW DOS RESULTADOS:")
    print("="*50)
    print(df.groupby(['api_type', 'query_type'])[['response_time_ms', 'payload_size_bytes']].mean())