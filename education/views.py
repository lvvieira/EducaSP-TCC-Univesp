import gzip
import io
import json
import urllib.request
import zlib
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.cache import cache_page
from django.db.models import Avg, Max, Min, Count, Q
from .models import Municipio, IndicadorAnual, ClusterMunicipio, ResultadoModelo


# ── helpers ───────────────────────────────────────────────────────────────────
def _float(v):
    return round(float(v), 3) if v is not None else None


# Indicadores-chave usados em diagnósticos
INDICADORES_CHAVE = [
    # (campo, rótulo, melhor_é_menor?)
    ('abandono_med_total',          'Abandono EM (%)',         True),
    ('ideb_medio',                  'IDEB médio',              False),
    ('saeb_12_mt',                  'SAEB MT (3ª EM)',         False),
    ('saeb_12_lp',                  'SAEB LP (3ª EM)',         False),
    ('enem_media_geral',            'ENEM média geral',        False),
    ('gasto_aluno',                 'Gasto/aluno (R$)',        False),
    ('inse',                        'INSE',                    False),
    ('pib_percapita',               'PIB per capita (R$)',     False),
    ('tdi_med_total',               'TDI EM (%)',              True),
    ('aluno_doc_med',               'Alunos/docente EM',       True),
    ('taxa_analfabetismo',          'Analfabetismo (%)',       True),
    ('in_internet',                 'Escolas c/ internet',     False),
    ('in_laboratorio_informatica',  'Escolas c/ lab. info.',   False),
    ('in_biblioteca',               'Escolas c/ biblioteca',   False),
    ('bf_por_aluno',                'Bolsa Família por aluno', False),
]


def _ano_mais_recente_com(campo, ano_pref=2023):
    """Retorna o ano mais recente onde o campo tem dado em pelo menos N municípios."""
    qs = IndicadorAnual.objects.filter(**{f'{campo}__isnull': False}).values_list('ano', flat=True).distinct()
    anos = sorted(qs, reverse=True)
    if ano_pref in anos:
        return ano_pref
    return anos[0] if anos else None


def _percentil(valor, lista_valores):
    """Posição do valor na lista, em percentil (0–100)."""
    if valor is None or not lista_valores:
        return None
    abaixo = sum(1 for v in lista_valores if v is not None and v < valor)
    return round(100 * abaixo / len([v for v in lista_valores if v is not None]), 1)


# ══════════════════════════════════════════════════════════════════════════════
# VIEWS DE PÁGINA
# ══════════════════════════════════════════════════════════════════════════════

def index(request):
    stats = IndicadorAnual.objects.filter(ano=2023).aggregate(
        abandono_med=Avg('abandono_med_total'),
        ideb_med=Avg('ideb_medio'),
        gasto_med=Avg('gasto_aluno'),
        saeb_med=Avg('saeb_12_mt'),
        inse_med=Avg('inse'),
        n_mun=Count('municipio', distinct=True),
    )
    anos = sorted(IndicadorAnual.objects.order_by().values_list('ano', flat=True).distinct())

    series_anuais = {
        'abandono':  [],
        'ideb':      [],
        'saeb_mt':   [],
        'enem':      [],
        'gasto':     [],
        'tdi':       [],
    }
    for ano in anos:
        agg = IndicadorAnual.objects.filter(ano=ano).aggregate(
            abandono=Avg('abandono_med_total'),
            ideb=Avg('ideb_medio'),
            saeb=Avg('saeb_12_mt'),
            enem=Avg('enem_media_geral'),
            gasto=Avg('gasto_aluno'),
            tdi=Avg('tdi_med_total'),
        )
        series_anuais['abandono'].append({'ano': ano, 'valor': _float(agg['abandono'])})
        series_anuais['ideb'].append({'ano': ano, 'valor': _float(agg['ideb'])})
        series_anuais['saeb_mt'].append({'ano': ano, 'valor': _float(agg['saeb'])})
        series_anuais['enem'].append({'ano': ano, 'valor': _float(agg['enem'])})
        series_anuais['gasto'].append({'ano': ano, 'valor': _float(agg['gasto'])})
        series_anuais['tdi'].append({'ano': ano, 'valor': _float(agg['tdi'])})

    # Top 5 melhores e piores em IDEB e abandono (média todos os anos)
    top_ideb = list(
        Municipio.objects
        .annotate(ideb=Avg('indicadores__ideb_medio'))
        .filter(ideb__isnull=False)
        .order_by('-ideb')[:5].values('co_municipio', 'no_municipio', 'ideb')
    )
    pior_ideb = list(
        Municipio.objects
        .annotate(ideb=Avg('indicadores__ideb_medio'))
        .filter(ideb__isnull=False)
        .order_by('ideb')[:5].values('co_municipio', 'no_municipio', 'ideb')
    )
    top_abandono = list(
        Municipio.objects
        .annotate(ab=Avg('indicadores__abandono_med_total'))
        .filter(ab__isnull=False)
        .order_by('-ab')[:5].values('co_municipio', 'no_municipio', 'ab')
    )

    n_clusters = ClusterMunicipio.objects.values('cluster_num').distinct().count()

    ctx = {
        'stats': stats,
        'series_json': series_anuais,  # dict puro: json_script faz a serialização
        'n_municipios': Municipio.objects.count(),
        'n_clusters': n_clusters,
        'n_modelos': ResultadoModelo.objects.count(),
        'top_ideb': top_ideb,
        'pior_ideb': pior_ideb,
        'top_abandono': top_abandono,
    }
    return render(request, 'education/index.html', ctx)


def municipio_list(request):
    q     = request.GET.get('q', '').strip()
    ano   = int(request.GET.get('ano', 2023))
    ordem = request.GET.get('ordem', 'no_municipio')
    ordem_map = {
        'abandono':  'indicadores__abandono_med_total',
        'ideb':      'indicadores__ideb_medio',
        'gasto':     'indicadores__gasto_aluno',
        'saeb':      'indicadores__saeb_12_mt',
        'no_municipio': 'no_municipio',
    }
    campo = ordem_map.get(ordem, 'no_municipio')
    desc  = request.GET.get('desc', '0') == '1'

    muns = (
        Municipio.objects
        .filter(indicadores__ano=ano)
        .annotate(
            abandono=Avg('indicadores__abandono_med_total'),
            ideb=Avg('indicadores__ideb_medio'),
            gasto=Avg('indicadores__gasto_aluno'),
            saeb=Avg('indicadores__saeb_12_mt'),
            inse=Avg('indicadores__inse'),
        )
    )
    if q:
        muns = muns.filter(no_municipio__icontains=q)
    muns = muns.order_by(f'-{campo}' if desc else campo)

    anos = sorted(IndicadorAnual.objects.order_by().values_list('ano', flat=True).distinct())
    ctx = {'municipios': muns, 'q': q, 'ano': ano, 'anos': anos,
           'ordem': ordem, 'desc': desc}
    return render(request, 'education/municipio_list.html', ctx)


def municipio_detail(request, co):
    mun  = get_object_or_404(Municipio, co_municipio=co)
    inds = mun.indicadores.order_by('ano')

    anos    = [i.ano for i in inds]
    cluster = getattr(mun, 'cluster', None)

    series = {
        'anos':          anos,
        'abandono_med':  [_float(i.abandono_med_total)  for i in inds],
        'abandono_fund': [_float(i.abandono_fund_total) for i in inds],
        'ideb_ai':       [_float(i.ideb_fund_ai)        for i in inds],
        'ideb_af':       [_float(i.ideb_fund_af)        for i in inds],
        'ideb_med':      [_float(i.ideb_medio)          for i in inds],
        'saeb_mt':       [_float(i.saeb_12_mt)          for i in inds],
        'saeb_lp':       [_float(i.saeb_12_lp)          for i in inds],
        'enem_geral':    [_float(i.enem_media_geral)    for i in inds],
        'gasto':         [_float(i.gasto_aluno)         for i in inds],
        'inse':          [_float(i.inse)                for i in inds],
        'tdi_med':       [_float(i.tdi_med_total)       for i in inds],
        'aluno_doc':     [_float(i.aluno_doc_med)       for i in inds],
    }
    infra_2023 = inds.filter(ano=2023).first()

    # ─── DIAGNÓSTICO MUNICIPAL ─────────────────────────────────────────────────
    # Para cada indicador-chave, calcular: valor do município, média SP,
    # média do cluster pareado, percentil entre os 645 municípios.
    diagnostico = []
    radar = {'labels': [], 'mun': [], 'media_sp': [], 'media_cluster': []}

    for campo, rotulo, menor_eh_melhor in INDICADORES_CHAVE:
        ano_ref = _ano_mais_recente_com(campo)
        if ano_ref is None:
            continue

        # valor do município no ano de referência
        ind_mun = inds.filter(ano=ano_ref).first()
        valor = getattr(ind_mun, campo, None) if ind_mun else None

        # média SP no ano
        media_sp = IndicadorAnual.objects.filter(ano=ano_ref).aggregate(m=Avg(campo))['m']

        # média do cluster pareado
        media_cluster = None
        if cluster:
            media_cluster = IndicadorAnual.objects.filter(
                ano=ano_ref, municipio__cluster__cluster_num=cluster.cluster_num
            ).aggregate(m=Avg(campo))['m']

        # percentil entre todos os municípios no ano
        valores_ano = list(
            IndicadorAnual.objects
            .filter(ano=ano_ref, **{f'{campo}__isnull': False})
            .values_list(campo, flat=True)
        )
        pct = _percentil(valor, valores_ano)

        # classificação ("força", "alerta", "vulnerabilidade")
        if pct is None:
            classe = 'sem_dado'
        else:
            # se "menor é melhor", invertemos o percentil para a classificação
            score = (100 - pct) if menor_eh_melhor else pct
            if score >= 70:
                classe = 'forca'
            elif score >= 30:
                classe = 'alerta'
            else:
                classe = 'vulnerabilidade'

        diagnostico.append({
            'campo': campo,
            'rotulo': rotulo,
            'ano': ano_ref,
            'valor': _float(valor),
            'media_sp': _float(media_sp),
            'media_cluster': _float(media_cluster),
            'percentil': pct,
            'classe': classe,
            'menor_eh_melhor': menor_eh_melhor,
        })

    # Top 3 forças e top 3 vulnerabilidades
    forcas = sorted(
        [d for d in diagnostico if d['classe'] == 'forca'],
        key=lambda d: -((100 - d['percentil']) if d['menor_eh_melhor'] else d['percentil'])
    )[:3]
    vulneras = sorted(
        [d for d in diagnostico if d['classe'] == 'vulnerabilidade'],
        key=lambda d: ((100 - d['percentil']) if d['menor_eh_melhor'] else d['percentil'])
    )[:3]

    # Radar normalizado: para cada indicador, normalizar (0..1) onde 1 = melhor.
    radar_campos = ['ideb_medio', 'saeb_12_mt', 'enem_media_geral', 'gasto_aluno', 'inse', 'in_internet']
    radar_labels = {
        'ideb_medio':        'IDEB',
        'saeb_12_mt':        'SAEB MT',
        'enem_media_geral':  'ENEM',
        'gasto_aluno':       'Gasto/aluno',
        'inse':              'INSE',
        'in_internet':       'Internet',
    }
    radar_data = {'labels': [], 'mun': [], 'media_sp': [], 'media_cluster': []}
    for c in radar_campos:
        d = next((x for x in diagnostico if x['campo'] == c), None)
        if not d or d['valor'] is None or d['media_sp'] is None or d['media_sp'] == 0:
            continue
        radar_data['labels'].append(radar_labels[c])
        radar_data['mun'].append(d['valor'])
        radar_data['media_sp'].append(d['media_sp'])
        radar_data['media_cluster'].append(d['media_cluster'] if d['media_cluster'] else d['media_sp'])

    # Classificação preditiva (regra simples: pelo abandono e pelo desempenho)
    abandono_mun = next((d['valor'] for d in diagnostico if d['campo'] == 'abandono_med_total'), None)
    abandono_med = IndicadorAnual.objects.aggregate(m=Avg('abandono_med_total'))['m'] or 0
    risco_abandono = None
    if abandono_mun is not None:
        risco_abandono = 'alto' if abandono_mun > abandono_med else 'baixo'

    ideb_mun = next((d['valor'] for d in diagnostico if d['campo'] == 'ideb_medio'), None)
    ideb_med = IndicadorAnual.objects.aggregate(m=Avg('ideb_medio'))['m'] or 0
    nivel_desempenho = None
    if ideb_mun is not None:
        nivel_desempenho = 'alto' if ideb_mun >= ideb_med else 'baixo'

    ctx = {
        'mun':           mun,
        'cluster':       cluster,
        'inds':          inds,
        'series_json':   series,        # dict puro: json_script serializa
        'radar_json':    radar_data,    # dict puro: json_script serializa
        'infra':         infra_2023,
        'diagnostico':   diagnostico,
        'forcas':        forcas,
        'vulneras':      vulneras,
        'risco_abandono':   risco_abandono,
        'nivel_desempenho': nivel_desempenho,
    }
    return render(request, 'education/municipio_detail.html', ctx)


def mapa(request):
    indicadores = [
        ('abandono_med_total', 'Abandono Ensino Médio (%)', True),
        ('ideb_medio',         'IDEB médio',                False),
        ('gasto_aluno',        'Gasto por aluno (R$)',      False),
        ('saeb_12_mt',         'SAEB Matemática (3ª EM)',   False),
        ('inse',               'INSE',                      False),
        ('tdi_med_total',      'TDI Ensino Médio (%)',      True),
    ]
    anos = sorted(IndicadorAnual.objects.order_by().values_list('ano', flat=True).distinct())
    ctx = {'indicadores': indicadores, 'anos': anos}
    return render(request, 'education/mapa.html', ctx)


def modelos(request):
    resultados = ResultadoModelo.objects.all().order_by('nome')
    ctx = {'resultados': resultados}
    return render(request, 'education/modelos.html', ctx)


def modelo_detail(request, nome):
    """Detalhe de um modelo específico com painéis completos do pipeline."""
    r = get_object_or_404(ResultadoModelo, nome=nome)

    # Mapa nome → arquivos PNG do pipeline
    paineis_map = {
        'M1_Abandono_EM':         ('M1_abandono_painel_completo_sp.png',     'M1_abandono_importancia_permutacao_sp.png'),
        'M2_Desempenho_SAEB_MT':  ('M2_saeb_mt_painel_completo_sp.png',      'M2_saeb_mt_importancia_permutacao_sp.png'),
        'M3_Desempenho_ENEM':     ('M3_enem_painel_completo_sp.png',         'M3_enem_importancia_permutacao_sp.png'),
        'M4_Abandono_EM_TDI_AFD': ('M4_abandono_ext_painel_completo_sp.png', 'M4_abandono_ext_importancia_permutacao_sp.png'),
    }
    painel_completo, importancia_perm = paineis_map.get(r.nome, (None, None))

    # Outros modelos para nav lateral
    todos = ResultadoModelo.objects.exclude(pk=r.pk).order_by('nome')

    ctx = {
        'r': r,
        'painel_completo': painel_completo,
        'importancia_perm': importancia_perm,
        'todos': todos,
    }
    return render(request, 'education/modelo_detail.html', ctx)


def analise(request):
    """Galeria de análise exploratória — agrupa todos os PNGs do pipeline por tema."""
    secoes = [
        {
            'titulo': 'Abandono escolar',
            'icone':  'trending_down',
            'cor':    'red',
            'descricao': 'Evolução temporal, séries, top municípios, comparativos por porte e por rede.',
            'figs': [
                ('A1_abandono_evolucao_sp.png',                        'Evolução do abandono no Ensino Médio e Fundamental (2019–2024)'),
                ('A2_abandono_por_serie_sp.png',                       'Abandono por série do Ensino Médio (1ª, 2ª, 3ª)'),
                ('A3_top10_abandono_medio_sp.png',                     'Top 10 municípios com maior abandono médio'),
                ('A4_abandono_por_porte_sp.png',                       'Abandono por porte municipal (matrículas)'),
                ('A5_abandono_ensino_médio_por_rede_sp.png',           'Abandono no Ensino Médio por rede de ensino'),
                ('A5_abandono_ensino_fundamental_por_rede_sp.png',     'Abandono no Ensino Fundamental por rede de ensino'),
                ('A7_abandono_comparativo_redes_sp.png',               'Comparativo direto entre redes (estadual × municipal × privada)'),
            ],
        },
        {
            'titulo': 'Desempenho acadêmico',
            'icone':  'school',
            'cor':    'green',
            'descricao': 'IDEB, SAEB e ENEM ao longo do tempo, e relações com abandono.',
            'figs': [
                ('B1_ideb_evolucao_sp.png',         'Evolução do IDEB médio'),
                ('B2_top10_melhora_ideb_sp.png',    'Top 10 municípios com maior melhora no IDEB'),
                ('B3_saeb_evolucao_sp.png',         'Evolução das proficiências SAEB'),
                ('B4_enem_evolucao_sp.png',         'Evolução das médias do ENEM'),
                ('B5_ideb_vs_abandono_sp.png',      'IDEB × Abandono (dispersão)'),
                ('B6_enem_vs_abandono_sp.png',      'ENEM × Abandono (dispersão)'),
            ],
        },
        {
            'titulo': 'Financiamento e contexto socioeconômico',
            'icone':  'payments',
            'cor':    'amber',
            'descricao': 'Gasto por aluno, PIB, renda, INSE, analfabetismo, Bolsa Família e razão aluno/docente em diálogo com os desfechos.',
            'figs': [
                ('C1_gasto_aluno_evolucao_sp.png',         'Evolução do gasto público por aluno'),
                ('C2_gasto_vs_abandono_sp.png',            'Gasto/aluno × abandono (dispersão)'),
                ('C3_gasto_vs_desempenho_sp.png',          'Gasto/aluno × desempenho (dispersão)'),
                ('C4_top10_gasto_aluno_sp.png',            'Top 10 municípios com maior gasto/aluno'),
                ('C5_inse_vs_outcomes_sp.png',             'INSE × abandono e desempenho'),
                ('C6_pib_vs_outcomes_sp.png',              'PIB per capita × abandono e desempenho'),
                ('C7_renda_vs_outcomes_sp.png',            'Renda per capita × abandono e desempenho'),
                ('C8_analfabetismo_vs_outcomes_sp.png',    'Taxa de analfabetismo × abandono e desempenho'),
                ('C9_bf_vs_outcomes_sp.png',               'Bolsa Família × abandono e desempenho'),
                ('C10_aluno_doc_vs_outcomes_sp.png',       'Razão aluno/docente × abandono e desempenho'),
            ],
        },
        {
            'titulo': 'Infraestrutura escolar',
            'icone':  'home_work',
            'cor':    'blue',
            'descricao': 'Como a presença de biblioteca, laboratório, internet e demais itens se associa aos resultados.',
            'figs': [
                ('D1_infra_vs_abandono_sp.png',     'Infraestrutura × abandono'),
                ('D2_infra_vs_desempenho_sp.png',   'Infraestrutura × desempenho'),
            ],
        },
        {
            'titulo': 'Correlações',
            'icone':  'grid_view',
            'cor':    'purple',
            'descricao': 'Síntese visual das correlações entre todas as variáveis analisadas.',
            'figs': [
                ('E1_resumo_correlacoes_sp.png',           'Síntese das correlações entre preditores e desfechos'),
                ('E2_matriz_correlacao_completa_sp.png',   'Matriz de correlação completa (heatmap)'),
            ],
        },
        {
            'titulo': 'Distorção idade-série e formação docente (TDI/AFD)',
            'icone':  'history_edu',
            'cor':    'brown',
            'descricao': 'Defasagem dos alunos e adequação da formação dos professores e seus reflexos no abandono e desempenho.',
            'figs': [
                ('F1_tdi_evolucao_sp.png',          'Evolução da distorção idade-série'),
                ('F2_tdi_por_serie_sp.png',         'TDI por série do Ensino Médio'),
                ('F3_tdi_vs_abandono_sp.png',       'TDI × abandono (dispersão)'),
                ('F4_tdi_vs_desempenho_sp.png',     'TDI × desempenho (dispersão)'),
                ('F5_afd_evolucao_sp.png',          'Evolução da adequação da formação docente'),
                ('F6_afd_vs_outcomes_sp.png',       'AFD × abandono e desempenho'),
                ('F7_tdi_afd_heatmap_sp.png',       'Heatmap conjunto TDI × AFD'),
            ],
        },
    ]
    ctx = {'secoes': secoes}
    return render(request, 'education/analise.html', ctx)


def clusters(request):
    perfis_qs = (
        ClusterMunicipio.objects
        .values('cluster_num', 'cluster_label')
        .annotate(
            n=Count('id'),
            abandono=Avg('abandono_medio'),
            ideb=Avg('ideb_medio'),
            gasto=Avg('gasto_medio'),
            inse=Avg('inse_medio'),
        )
        .order_by('cluster_num')
    )
    perfis = list(perfis_qs)

    # Versão "limpa" (com floats) para serializar em JSON sem problemas de l10n
    perfis_json = [
        {
            'num':       p['cluster_num'],
            'label':     p['cluster_label'],
            'n':         p['n'],
            'abandono':  _float(p['abandono']),
            'ideb':      _float(p['ideb']),
            'gasto':     _float(p['gasto']),
            'inse':      _float(p['inse']),
        }
        for p in perfis
    ]

    municipios_cluster = (
        ClusterMunicipio.objects
        .select_related('municipio')
        .order_by('cluster_num', 'municipio__no_municipio')
    )

    ctx = {
        'perfis':       perfis,
        'perfis_json':  perfis_json,   # lista pura: json_script serializa
        'municipios':   municipios_cluster,
    }
    return render(request, 'education/clusters.html', ctx)


# ══════════════════════════════════════════════════════════════════════════════
# API JSON (para Chart.js / OpenLayers)
# ══════════════════════════════════════════════════════════════════════════════

def api_municipios(request):
    ano = int(request.GET.get('ano', 2023))
    muns = (
        Municipio.objects
        .filter(indicadores__ano=ano)
        .annotate(
            abandono=Avg('indicadores__abandono_med_total'),
            ideb=Avg('indicadores__ideb_medio'),
            gasto=Avg('indicadores__gasto_aluno'),
            saeb=Avg('indicadores__saeb_12_mt'),
            inse=Avg('indicadores__inse'),
            tdi=Avg('indicadores__tdi_med_total'),
        )
        .order_by('no_municipio')
    )
    data = [
        {
            'co': m.co_municipio,
            'nome': m.no_municipio,
            'abandono': _float(m.abandono),
            'ideb': _float(m.ideb),
            'gasto': _float(m.gasto),
            'saeb': _float(m.saeb),
            'inse': _float(m.inse),
            'tdi': _float(m.tdi),
        }
        for m in muns
    ]
    return JsonResponse({'municipios': data, 'ano': ano})


def api_municipio(request, co):
    mun  = get_object_or_404(Municipio, co_municipio=co)
    inds = mun.indicadores.order_by('ano')
    data = {
        'co': mun.co_municipio,
        'nome': mun.no_municipio,
        'series': [
            {
                'ano': i.ano,
                'abandono_med': _float(i.abandono_med_total),
                'abandono_fund': _float(i.abandono_fund_total),
                'ideb_medio': _float(i.ideb_medio),
                'saeb_12_mt': _float(i.saeb_12_mt),
                'saeb_12_lp': _float(i.saeb_12_lp),
                'enem_geral': _float(i.enem_media_geral),
                'gasto_aluno': _float(i.gasto_aluno),
                'inse': _float(i.inse),
                'tdi_med': _float(i.tdi_med_total),
            }
            for i in inds
        ]
    }
    return JsonResponse(data)


def api_mapa(request):
    ano       = int(request.GET.get('ano', 2023))
    indicador = request.GET.get('indicador', 'abandono_med_total')
    campo_map = {
        'abandono_med_total': 'abandono_med_total',
        'ideb_medio':         'ideb_medio',
        'gasto_aluno':        'gasto_aluno',
        'saeb_12_mt':         'saeb_12_mt',
        'inse':               'inse',
        'tdi_med_total':      'tdi_med_total',
    }
    campo = campo_map.get(indicador, 'abandono_med_total')
    inds = (
        IndicadorAnual.objects
        .filter(ano=ano)
        .select_related('municipio')
        .values('municipio__co_municipio', 'municipio__no_municipio', campo)
    )
    # Valores não nulos para cálculo de percentil
    valores = [i[campo] for i in inds if i[campo] is not None]
    valores_sorted = sorted(valores)
    n_valid = len(valores_sorted)

    def percentil(v):
        if v is None or n_valid == 0:
            return None
        # bisect-like
        lo, hi = 0, n_valid
        while lo < hi:
            mid = (lo + hi) // 2
            if valores_sorted[mid] < v:
                lo = mid + 1
            else:
                hi = mid
        return round(100 * lo / n_valid, 1)

    media = sum(valores) / n_valid if n_valid else None

    data = [
        {
            'co':     i['municipio__co_municipio'],
            'nome':   i['municipio__no_municipio'],
            'valor':  _float(i[campo]),
            'pct':    percentil(i[campo]),
        }
        for i in inds
    ]
    return JsonResponse({
        'features': data,
        'indicador': indicador,
        'ano': ano,
        'media': _float(media),
        'min': _float(min(valores)) if valores else None,
        'max': _float(max(valores)) if valores else None,
        'n':   n_valid,
    })


def api_modelos(request):
    resultados = ResultadoModelo.objects.all().order_by('nome')
    data = [
        {
            'nome':          r.nome,
            'alvo':          r.variavel_alvo,
            'n_obs':         r.n_obs,
            'log_auc':       r.log_auc,
            'log_auc_cv':    r.log_auc_cv,
            'log_acuracia':  r.log_acuracia,
            'rf_auc':        r.rf_auc,
            'rf_auc_cv':     r.rf_auc_cv,
            'rf_acuracia':   r.rf_acuracia,
            'top3':          r.top3_features,
        }
        for r in resultados
    ]
    return JsonResponse({'modelos': data})


# ─── GeoJSON proxy: contorna CORS do IBGE ─────────────────────────────────────
@cache_page(60 * 60 * 24)  # cache de 24h (a malha quase nunca muda)
def api_malha_municipios(request):
    """Proxy que busca a malha do IBGE server-side e devolve com CORS local.

    O IBGE responde com Content-Encoding: gzip mesmo quando não pedimos.
    Detectamos pela assinatura do gzip (\\x1f\\x8b) e descomprimimos.
    """
    url = ('https://servicodados.ibge.gov.br/api/v3/malhas/estados/35'
           '?formato=application/vnd.geo+json&intrarregiao=municipio')
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'EducaSP-Analytics/1.0',
            'Accept-Encoding': 'gzip, deflate',
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            encoding = (resp.headers.get('Content-Encoding') or '').lower()

        # Descomprime se necessário (header explícito ou assinatura mágica do gzip)
        if encoding == 'gzip' or raw[:2] == b'\x1f\x8b':
            raw = gzip.decompress(raw)
        elif encoding == 'deflate':
            raw = zlib.decompress(raw)

        # Garante que é JSON válido (lança se não for)
        json.loads(raw)

        return HttpResponse(
            raw,
            content_type='application/geo+json',
            headers={
                'Cache-Control': 'public, max-age=86400',
                'Access-Control-Allow-Origin': '*',
            },
        )
    except Exception as e:
        return JsonResponse({'error': str(e), 'url': url}, status=502)


def api_clusters(request):
    clusters = (
        ClusterMunicipio.objects
        .select_related('municipio')
        .values(
            'municipio__co_municipio', 'municipio__no_municipio',
            'cluster_num', 'cluster_label',
            'abandono_medio', 'ideb_medio', 'gasto_medio', 'inse_medio',
        )
        .order_by('cluster_num', 'municipio__no_municipio')
    )
    data = [
        {
            'co':      c['municipio__co_municipio'],
            'nome':    c['municipio__no_municipio'],
            'cluster': c['cluster_num'],
            'label':   c['cluster_label'],
            'abandono': _float(c['abandono_medio']),
            'ideb':     _float(c['ideb_medio']),
            'gasto':    _float(c['gasto_medio']),
            'inse':     _float(c['inse_medio']),
        }
        for c in clusters
    ]
    return JsonResponse({'clusters': data})
