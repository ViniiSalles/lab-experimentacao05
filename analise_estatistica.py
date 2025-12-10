import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import shapiro, wilcoxon, ttest_rel

# Configuração visual
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

# ============================================
# CARREGAR DADOS
# ============================================
print("📂 Carregando dados...")
df = pd.read_csv("resultados_experimento.csv")

print(f"✅ {len(df)} medições carregadas")
print(f"📋 Colunas: {list(df.columns)}")
print(f"\n📊 Resumo dos dados:")
print(df.groupby(['api_type', 'query_type']).size())

# ============================================
# 1. ESTATÍSTICAS DESCRITIVAS
# ============================================
print("\n" + "="*60)
print("📈 ESTATÍSTICAS DESCRITIVAS")
print("="*60)

# Agrupar por API e Query Type
summary = df.groupby(['api_type', 'query_type']).agg({
 'response_time_ms': ['mean', 'std', 'median', 'min', 'max'],
 'payload_size_bytes': ['mean', 'std', 'median', 'min', 'max']
}).round(2)

print("\n🕐 TEMPO DE RESPOSTA (ms):")
print(summary['response_time_ms'])

print("\n📦 TAMANHO DO PAYLOAD (bytes):")
print(summary['payload_size_bytes'])

# Salvar estatísticas
summary.to_csv("estatisticas_descritivas.csv")
print("\n💾 Salvo em: estatisticas_descritivas.csv")

# ============================================
# 2. TESTE DE NORMALIDADE
# ============================================
print("\n" + "="*60)
print("🔍 TESTE DE NORMALIDADE (Shapiro-Wilk)")
print("="*60)
print("H0: Os dados seguem distribuição normal")
print("Se p-value < 0.05 → Rejeita H0 (NÃO é normal)\n")

normalidade_resultados = []

for api in df['api_type'].unique():
 for qtype in df['query_type'].unique():
     subset = df[(df['api_type'] == api) & (df['query_type'] == qtype)]
     
     # Teste para tempo
     stat_time, p_time = shapiro(subset['response_time_ms'])
     # Teste para tamanho
     stat_size, p_size = shapiro(subset['payload_size_bytes'])
     
     normalidade_resultados.append({
         'api': api,
         'query': qtype,
         'tempo_stat': stat_time,
         'tempo_p': p_time,
         'tempo_normal': 'SIM' if p_time > 0.05 else 'NÃO',
         'tamanho_stat': stat_size,
         'tamanho_p': p_size,
         'tamanho_normal': 'SIM' if p_size > 0.05 else 'NÃO'
     })

norm_df = pd.DataFrame(normalidade_resultados)
print(norm_df.to_string(index=False))

# Decisão do teste
usa_parametrico = norm_df['tempo_normal'].eq('SIM').all() and norm_df['tamanho_normal'].eq('SIM').all()
teste_escolhido = "t-test pareado" if usa_parametrico else "Wilcoxon signed-rank"

print(f"\n🎯 DECISÃO: Usar {teste_escolhido}")
print(f"   Motivo: Dados {'SÃO' if usa_parametrico else 'NÃO SÃO'} normalmente distribuídos")

# ============================================
# 3. TESTE DE HIPÓTESE - RQ1 (TEMPO)
# ============================================
print("\n" + "="*60)
print("⏱️  RQ1: TESTE DE HIPÓTESE - TEMPO DE RESPOSTA")
print("="*60)
print("H0: Não há diferença significativa entre GraphQL e REST")
print("H1: Há diferença significativa entre GraphQL e REST\n")

rq1_resultados = []

for qtype in df['query_type'].unique():
 rest_data = df[(df['api_type'] == 'REST') & (df['query_type'] == qtype)]['response_time_ms']
 graphql_data = df[(df['api_type'] == 'GraphQL') & (df['query_type'] == qtype)]['response_time_ms']
 
 # Calcula diferença média
 diff_mean = graphql_data.mean() - rest_data.mean()
 diff_percent = (diff_mean / rest_data.mean()) * 100
 
 # Escolhe o teste apropriado
 if usa_parametrico:
     stat, p_value = ttest_rel(rest_data, graphql_data)
     teste = "t-test"
 else:
     stat, p_value = wilcoxon(rest_data, graphql_data)
     teste = "Wilcoxon"
 
 # Calcula Cohen's d (tamanho do efeito)
 cohens_d = (graphql_data.mean() - rest_data.mean()) / np.sqrt(
     (rest_data.std()**2 + graphql_data.std()**2) / 2
 )
 
 # Interpreta tamanho do efeito
 if abs(cohens_d) < 0.2:
     efeito = "Trivial"
 elif abs(cohens_d) < 0.5:
     efeito = "Pequeno"
 elif abs(cohens_d) < 0.8:
     efeito = "Médio"
 else:
     efeito = "Grande"
 
 resultado = "SIGNIFICATIVO" if p_value < 0.05 else "NÃO SIGNIFICATIVO"
 
 print(f"\n📌 Query: {qtype.upper()}")
 print(f"   REST média:     {rest_data.mean():.2f} ms (±{rest_data.std():.2f})")
 print(f"   GraphQL média:  {graphql_data.mean():.2f} ms (±{graphql_data.std():.2f})")
 print(f"   Diferença:      {diff_mean:+.2f} ms ({diff_percent:+.1f}%)")
 print(f"   Teste:          {teste}")
 print(f"   Estatística:    {stat:.4f}")
 print(f"   P-value:        {p_value:.6f}")
 print(f"   Cohen's d:      {cohens_d:.4f} ({efeito})")
 print(f"   ✓ Resultado:    {resultado}")
 
 rq1_resultados.append({
     'query': qtype,
     'rest_mean': rest_data.mean(),
     'graphql_mean': graphql_data.mean(),
     'diff_ms': diff_mean,
     'diff_percent': diff_percent,
     'p_value': p_value,
     'cohens_d': cohens_d,
     'effect_size': efeito,
     'significativo': resultado
 })

rq1_df = pd.DataFrame(rq1_resultados)
rq1_df.to_csv("rq1_resultados_tempo.csv", index=False)

# ============================================
# 4. TESTE DE HIPÓTESE - RQ2 (TAMANHO)
# ============================================
print("\n" + "="*60)
print("📦 RQ2: TESTE DE HIPÓTESE - TAMANHO DO PAYLOAD")
print("="*60)
print("H0: Não há diferença significativa entre GraphQL e REST")
print("H1: Há diferença significativa entre GraphQL e REST\n")

rq2_resultados = []

for qtype in df['query_type'].unique():
 rest_data = df[(df['api_type'] == 'REST') & (df['query_type'] == qtype)]['payload_size_bytes']
 graphql_data = df[(df['api_type'] == 'GraphQL') & (df['query_type'] == qtype)]['payload_size_bytes']
 
 diff_mean = graphql_data.mean() - rest_data.mean()
 diff_percent = (diff_mean / rest_data.mean()) * 100
 
 if usa_parametrico:
     stat, p_value = ttest_rel(rest_data, graphql_data)
     teste = "t-test"
 else:
     stat, p_value = wilcoxon(rest_data, graphql_data)
     teste = "Wilcoxon"
 
 cohens_d = (graphql_data.mean() - rest_data.mean()) / np.sqrt(
     (rest_data.std()**2 + graphql_data.std()**2) / 2
 )
 
 if abs(cohens_d) < 0.2:
     efeito = "Trivial"
 elif abs(cohens_d) < 0.5:
     efeito = "Pequeno"
 elif abs(cohens_d) < 0.8:
     efeito = "Médio"
 else:
     efeito = "Grande"
 
 resultado = "SIGNIFICATIVO" if p_value < 0.05 else "NÃO SIGNIFICATIVO"
 
 print(f"\n📌 Query: {qtype.upper()}")
 print(f"   REST média:     {rest_data.mean():.0f} bytes (±{rest_data.std():.0f})")
 print(f"   GraphQL média:  {graphql_data.mean():.0f} bytes (±{graphql_data.std():.0f})")
 print(f"   Diferença:      {diff_mean:+.0f} bytes ({diff_percent:+.1f}%)")
 print(f"   Teste:          {teste}")
 print(f"   Estatística:    {stat:.4f}")
 print(f"   P-value:        {p_value:.6f}")
 print(f"   Cohen's d:      {cohens_d:.4f} ({efeito})")
 print(f"   ✓ Resultado:    {resultado}")
 
 rq2_resultados.append({
     'query': qtype,
     'rest_mean': rest_data.mean(),
     'graphql_mean': graphql_data.mean(),
     'diff_bytes': diff_mean,
     'diff_percent': diff_percent,
     'p_value': p_value,
     'cohens_d': cohens_d,
     'effect_size': efeito,
     'significativo': resultado
 })

rq2_df = pd.DataFrame(rq2_resultados)
rq2_df.to_csv("rq2_resultados_tamanho.csv", index=False)

# ============================================
# 5. VISUALIZAÇÕES
# ============================================
print("\n" + "="*60)
print("📊 GERANDO VISUALIZAÇÕES...")
print("="*60)

# Figura 1: Boxplots de Tempo
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('Tempo de Resposta: REST vs GraphQL', fontsize=16, fontweight='bold')

for idx, qtype in enumerate(['simple', 'medium', 'complex']):
 subset = df[df['query_type'] == qtype]
 sns.boxplot(data=subset, x='api_type', y='response_time_ms', ax=axes[idx], palette='Set2')
 axes[idx].set_title(f'{qtype.capitalize()}', fontsize=12)
 axes[idx].set_xlabel('API Type', fontsize=10)
 axes[idx].set_ylabel('Tempo (ms)', fontsize=10)

plt.tight_layout()
plt.savefig('fig1_tempo_boxplot.png', dpi=300, bbox_inches='tight')
print("✅ Salvo: fig1_tempo_boxplot.png")

# Figura 2: Boxplots de Tamanho
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('Tamanho do Payload: REST vs GraphQL', fontsize=16, fontweight='bold')

for idx, qtype in enumerate(['simple', 'medium', 'complex']):
 subset = df[df['query_type'] == qtype]
 sns.boxplot(data=subset, x='api_type', y='payload_size_bytes', ax=axes[idx], palette='Set1')
 axes[idx].set_title(f'{qtype.capitalize()}', fontsize=12)
 axes[idx].set_xlabel('API Type', fontsize=10)
 axes[idx].set_ylabel('Tamanho (bytes)', fontsize=10)

plt.tight_layout()
plt.savefig('fig2_tamanho_boxplot.png', dpi=300, bbox_inches='tight')
print("✅ Salvo: fig2_tamanho_boxplot.png")

# Figura 3: Violin Plots (Tempo)
fig, ax = plt.subplots(figsize=(12, 6))
sns.violinplot(data=df, x='query_type', y='response_time_ms', hue='api_type', 
            split=True, palette='muted', ax=ax)
ax.set_title('Distribuição do Tempo de Resposta', fontsize=14, fontweight='bold')
ax.set_xlabel('Tipo de Query', fontsize=12)
ax.set_ylabel('Tempo (ms)', fontsize=12)
plt.legend(title='API Type')
plt.tight_layout()
plt.savefig('fig3_tempo_violin.png', dpi=300, bbox_inches='tight')
print("✅ Salvo: fig3_tempo_violin.png")

# Figura 4: Barras com erro (Comparação direta)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Tempo
summary_time = df.groupby(['query_type', 'api_type'])['response_time_ms'].agg(['mean', 'std']).reset_index()
summary_time_pivot = summary_time.pivot(index='query_type', columns='api_type', values='mean')
summary_time_std = summary_time.pivot(index='query_type', columns='api_type', values='std')
summary_time_pivot.plot(kind='bar', ax=ax1, yerr=summary_time_std, capsize=4, color=['#ff7f0e', '#2ca02c'])
ax1.set_title('Tempo Médio de Resposta', fontsize=12, fontweight='bold')
ax1.set_ylabel('Tempo (ms)')
ax1.set_xlabel('Tipo de Query')
ax1.legend(title='API')
ax1.grid(axis='y', alpha=0.3)

# Tamanho
summary_size = df.groupby(['query_type', 'api_type'])['payload_size_bytes'].agg(['mean', 'std']).reset_index()
summary_size_pivot = summary_size.pivot(index='query_type', columns='api_type', values='mean')
summary_size_std = summary_size.pivot(index='query_type', columns='api_type', values='std')
summary_size_pivot.plot(kind='bar', ax=ax2, yerr=summary_size_std, capsize=4, color=['#ff7f0e', '#2ca02c'])
ax2.set_title('Tamanho Médio do Payload', fontsize=12, fontweight='bold')
ax2.set_ylabel('Tamanho (bytes)')
ax2.set_xlabel('Tipo de Query')
ax2.legend(title='API')
ax2.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('fig4_comparacao_barras.png', dpi=300, bbox_inches='tight')
print("✅ Salvo: fig4_comparacao_barras.png")

print("\n✅ ANÁLISE COMPLETA!")
print("📁 Arquivos gerados:")
print("   - estatisticas_descritivas.csv")
print("   - rq1_resultados_tempo.csv")
print("   - rq2_resultados_tamanho.csv")
print("   - fig1_tempo_boxplot.png")
print("   - fig2_tamanho_boxplot.png")
print("   - fig3_tempo_violin.png")
print("   - fig4_comparacao_barras.png")