"""
Importa dados gerados pelos scripts do TCC para o banco SQLite do Django.

Lê:
  - Output/df_master_sp.csv      → Municipio + IndicadorAnual
  - graficos/kmeans_clusters_sp.csv → ClusterMunicipio
  - graficos/metricas_modelos_sp.csv → ResultadoModelo

Uso:
  python manage.py importar_dados
  python manage.py importar_dados --master /caminho/df_master.csv --clusters /caminho/clusters.csv
"""
import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from education.models import Municipio, IndicadorAnual, ClusterMunicipio, ResultadoModelo


def _f(v):
    if v is None or v == "" or v == "nan":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _i(v):
    f = _f(v)
    return int(f) if f is not None else None


# Rótulos amigáveis para os clusters (k=2: SP é razoavelmente homogêneo)
CLUSTER_LABELS = {
    1: "Mais favorecido",
    2: "Mais vulnerável",
}


class Command(BaseCommand):
    help = "Importa CSVs do pipeline TCC para o banco SQLite."

    def add_arguments(self, parser):
        base = Path(__file__).resolve().parents[4]  # webapp/../
        parser.add_argument("--master",   default=str(base / "Output" / "df_master_sp.csv"))
        parser.add_argument("--clusters", default=str(base / "graficos" / "kmeans_clusters_sp.csv"))
        parser.add_argument("--modelos",  default=str(base / "graficos" / "metricas_modelos_sp.csv"))

    def handle(self, *args, **opts):
        self._importar_master(opts["master"])
        self._importar_clusters(opts["clusters"])
        self._importar_modelos(opts["modelos"])
        self.stdout.write(self.style.SUCCESS("✔ Importação concluída."))

    # ─── Master / Indicadores anuais ──────────────────────────────────────────
    @transaction.atomic
    def _importar_master(self, path):
        path = Path(path)
        if not path.exists():
            self.stdout.write(self.style.ERROR(f"Arquivo master não encontrado: {path}"))
            return

        self.stdout.write(f"→ Importando indicadores anuais de {path.name}…")
        IndicadorAnual.objects.all().delete()

        munis_cache = {}
        criados = 0

        with open(path, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, delimiter=";")
            for row in reader:
                co = str(row["CO_MUNICIPIO"]).strip()
                if not co or co == "nan":
                    continue
                co = co.split(".")[0]  # remove .0 if pandas exported as float

                if co not in munis_cache:
                    mun, _ = Municipio.objects.get_or_create(
                        co_municipio=co,
                        defaults={
                            "no_municipio": row.get("NO_MUNICIPIO", co).strip(),
                            "uf": "SP",
                        },
                    )
                    munis_cache[co] = mun

                ano = _i(row.get("ANO"))
                if ano is None:
                    continue

                IndicadorAnual.objects.update_or_create(
                    municipio=munis_cache[co],
                    ano=ano,
                    defaults=dict(
                        # Abandono
                        abandono_med_total   = _f(row.get("ABANDONO_MED_TOTAL")),
                        abandono_fund_total  = _f(row.get("ABANDONO_FUND_TOTAL")),
                        abandono_med_1serie  = _f(row.get("ABANDONO_MED_1SERIE")),
                        abandono_med_2serie  = _f(row.get("ABANDONO_MED_2SERIE")),
                        abandono_med_3serie  = _f(row.get("ABANDONO_MED_3SERIE")),
                        # IDEB
                        ideb_fund_ai  = _f(row.get("IDEB_FUND_AI")),
                        ideb_fund_af  = _f(row.get("IDEB_FUND_AF")),
                        ideb_medio    = _f(row.get("IDEB_MEDIO")),
                        # SAEB
                        saeb_5_lp   = _f(row.get("SAEB_5_LP")),
                        saeb_5_mt   = _f(row.get("SAEB_5_MT")),
                        saeb_9_lp   = _f(row.get("SAEB_9_LP")),
                        saeb_9_mt   = _f(row.get("SAEB_9_MT")),
                        saeb_12_lp  = _f(row.get("SAEB_12_LP")),
                        saeb_12_mt  = _f(row.get("SAEB_12_MT")),
                        # ENEM
                        enem_media_geral   = _f(row.get("ENEM_MEDIA_GERAL")),
                        enem_media_mt      = _f(row.get("ENEM_MEDIA_MT")),
                        enem_media_cn      = _f(row.get("ENEM_MEDIA_CN")),
                        enem_media_ch      = _f(row.get("ENEM_MEDIA_CH")),
                        enem_media_lc      = _f(row.get("ENEM_MEDIA_LC")),
                        enem_media_redacao = _f(row.get("ENEM_MEDIA_REDACAO")),
                        enem_participantes = _i(row.get("ENEM_PARTICIPANTES")),
                        # Financiamento
                        gasto_aluno   = _f(row.get("GASTO_ALUNO")),
                        desp_edu_paga = _f(row.get("DESP_EDU_PAGA")),
                        # Socioeconômico
                        pib_percapita      = _f(row.get("PIB_PERCAPITA")),
                        renda_percapita    = _f(row.get("RENDA_PERCAPITA")),
                        inse               = _f(row.get("INSE")),
                        taxa_analfabetismo = _f(row.get("TAXA_ANALFABETISMO")),
                        bf_media_mensal    = _f(row.get("BF_MEDIA_MENSAL")),
                        bf_por_aluno       = _f(row.get("BF_POR_ALUNO")),
                        # Infraestrutura
                        in_agua_potavel            = _f(row.get("IN_AGUA_POTAVEL")),
                        in_esgoto_rede_publica     = _f(row.get("IN_ESGOTO_REDE_PUBLICA")),
                        in_biblioteca              = _f(row.get("IN_BIBLIOTECA")),
                        in_laboratorio_informatica = _f(row.get("IN_LABORATORIO_INFORMATICA")),
                        in_internet                = _f(row.get("IN_INTERNET")),
                        in_quadra_esportes         = _f(row.get("IN_QUADRA_ESPORTES")),
                        in_refeitorio              = _f(row.get("IN_REFEITORIO")),
                        # TDI / AFD
                        tdi_med_total     = _f(row.get("TDI_MED_TOTAL")),
                        tdi_fund_total    = _f(row.get("TDI_FUND_TOTAL")),
                        afd_med_adequado  = _f(row.get("AFD_MED_ADEQUADO")),
                        afd_fund_adequado = _f(row.get("AFD_FUND_ADEQUADO")),
                        # Censo
                        qt_mat_bas    = _f(row.get("QT_MAT_BAS")),
                        qt_mat_fund   = _f(row.get("QT_MAT_FUND")),
                        qt_mat_med    = _f(row.get("QT_MAT_MED")),
                        qt_doc_med    = _f(row.get("QT_DOC_MED")),
                        aluno_doc_med = _f(row.get("ALUNO_DOC_MED")),
                    ),
                )
                criados += 1

        self.stdout.write(self.style.SUCCESS(
            f"  ✔ {len(munis_cache)} municípios · {criados} indicadores anuais"
        ))

    # ─── Clusters ────────────────────────────────────────────────────────────
    @transaction.atomic
    def _importar_clusters(self, path):
        path = Path(path)
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"  Clusters não encontrados: {path}"))
            return

        self.stdout.write(f"→ Importando clusters de {path.name}…")
        ClusterMunicipio.objects.all().delete()

        criados = 0
        with open(path, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, delimiter=";")
            for row in reader:
                nome = row["NO_MUNICIPIO"].strip()
                # Localizar município pelo nome (não temos co_municipio no kmeans CSV)
                mun = Municipio.objects.filter(no_municipio__iexact=nome).first()
                if not mun:
                    continue

                num   = _i(row.get("CLUSTER")) or 0
                label = CLUSTER_LABELS.get(num, f"Cluster {num}")

                ClusterMunicipio.objects.update_or_create(
                    municipio=mun,
                    defaults=dict(
                        cluster_num=num,
                        cluster_label=label,
                        inse_medio    = _f(row.get("INSE")),
                        abandono_medio = _f(row.get("ABANDONO_MED_TOTAL")),
                        ideb_medio    = _f(row.get("IDEB_MEDIO")),
                        gasto_medio   = _f(row.get("GASTO_ALUNO")),
                    ),
                )
                criados += 1

        self.stdout.write(self.style.SUCCESS(f"  ✔ {criados} municípios clusterizados"))

    # ─── Modelos preditivos ──────────────────────────────────────────────────
    @transaction.atomic
    def _importar_modelos(self, path):
        path = Path(path)
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"  Métricas de modelos não encontradas: {path}"))
            return

        self.stdout.write(f"→ Importando métricas de modelos de {path.name}…")
        ResultadoModelo.objects.all().delete()

        # Mapa nome → variável-alvo legível
        alvo_map = {
            "M1_Abandono_EM":         "ABANDONO_MED_TOTAL",
            "M2_Desempenho_SAEB_MT":  "SAEB_12_MT",
            "M3_Desempenho_ENEM":     "ENEM_MEDIA_GERAL",
            "M4_Abandono_EM_TDI_AFD": "ABANDONO_MED_TOTAL (+ TDI/AFD)",
        }

        criados = 0
        with open(path, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, delimiter=";")
            for row in reader:
                nome = row["Modelo"].strip()
                ResultadoModelo.objects.update_or_create(
                    nome=nome,
                    defaults=dict(
                        variavel_alvo = alvo_map.get(nome, "—"),
                        n_obs         = _i(row.get("N_obs")) or 0,
                        n_features    = _i(row.get("N_features")) or 0,
                        mediana_alvo  = _f(row.get("Mediana_alvo")) or 0,
                        log_acuracia  = _f(row.get("LogReg_Acuracia")) or 0,
                        log_auc       = _f(row.get("LogReg_AUC")) or 0,
                        log_auc_cv    = _f(row.get("LogReg_AUC_CV")) or 0,
                        rf_acuracia   = _f(row.get("RF_Acuracia")) or 0,
                        rf_auc        = _f(row.get("RF_AUC")) or 0,
                        rf_auc_cv     = _f(row.get("RF_AUC_CV")) or 0,
                        top3_features = row.get("Top3_MDI", "").strip(),
                    ),
                )
                criados += 1

        self.stdout.write(self.style.SUCCESS(f"  ✔ {criados} modelos preditivos"))
