from django.db import models


class Municipio(models.Model):
    co_municipio = models.CharField(max_length=10, unique=True, verbose_name="Código IBGE")
    no_municipio = models.CharField(max_length=120, verbose_name="Nome")
    uf           = models.CharField(max_length=2, default="SP")

    class Meta:
        verbose_name = "Município"
        verbose_name_plural = "Municípios"
        ordering = ["no_municipio"]

    def __str__(self):
        return f"{self.no_municipio} ({self.uf})"


class IndicadorAnual(models.Model):
    municipio   = models.ForeignKey(Municipio, on_delete=models.CASCADE,
                                    related_name="indicadores")
    ano         = models.SmallIntegerField(verbose_name="Ano")

    # Abandono
    abandono_med_total          = models.FloatField(null=True, blank=True)
    abandono_fund_total         = models.FloatField(null=True, blank=True)
    abandono_med_1serie         = models.FloatField(null=True, blank=True)
    abandono_med_2serie         = models.FloatField(null=True, blank=True)
    abandono_med_3serie         = models.FloatField(null=True, blank=True)

    # IDEB
    ideb_fund_ai  = models.FloatField(null=True, blank=True)
    ideb_fund_af  = models.FloatField(null=True, blank=True)
    ideb_medio    = models.FloatField(null=True, blank=True)

    # SAEB
    saeb_5_lp   = models.FloatField(null=True, blank=True)
    saeb_5_mt   = models.FloatField(null=True, blank=True)
    saeb_9_lp   = models.FloatField(null=True, blank=True)
    saeb_9_mt   = models.FloatField(null=True, blank=True)
    saeb_12_lp  = models.FloatField(null=True, blank=True)
    saeb_12_mt  = models.FloatField(null=True, blank=True)

    # ENEM
    enem_media_geral    = models.FloatField(null=True, blank=True)
    enem_media_mt       = models.FloatField(null=True, blank=True)
    enem_media_cn       = models.FloatField(null=True, blank=True)
    enem_media_ch       = models.FloatField(null=True, blank=True)
    enem_media_lc       = models.FloatField(null=True, blank=True)
    enem_media_redacao  = models.FloatField(null=True, blank=True)
    enem_participantes  = models.IntegerField(null=True, blank=True)

    # Financiamento
    gasto_aluno   = models.FloatField(null=True, blank=True)
    desp_edu_paga = models.FloatField(null=True, blank=True)

    # Socioeconômico
    pib_percapita       = models.FloatField(null=True, blank=True)
    renda_percapita     = models.FloatField(null=True, blank=True)
    inse                = models.FloatField(null=True, blank=True)
    taxa_analfabetismo  = models.FloatField(null=True, blank=True)
    bf_media_mensal     = models.FloatField(null=True, blank=True)
    bf_por_aluno        = models.FloatField(null=True, blank=True)

    # Infraestrutura escolar (proporção de escolas com o item)
    in_agua_potavel             = models.FloatField(null=True, blank=True)
    in_esgoto_rede_publica      = models.FloatField(null=True, blank=True)
    in_biblioteca               = models.FloatField(null=True, blank=True)
    in_laboratorio_informatica  = models.FloatField(null=True, blank=True)
    in_internet                 = models.FloatField(null=True, blank=True)
    in_quadra_esportes          = models.FloatField(null=True, blank=True)
    in_refeitorio               = models.FloatField(null=True, blank=True)

    # TDI e AFD
    tdi_med_total       = models.FloatField(null=True, blank=True)
    tdi_fund_total      = models.FloatField(null=True, blank=True)
    afd_med_adequado    = models.FloatField(null=True, blank=True)
    afd_fund_adequado   = models.FloatField(null=True, blank=True)

    # Censo escolar
    qt_mat_bas   = models.FloatField(null=True, blank=True)
    qt_mat_fund  = models.FloatField(null=True, blank=True)
    qt_mat_med   = models.FloatField(null=True, blank=True)
    qt_doc_med   = models.FloatField(null=True, blank=True)
    aluno_doc_med = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Indicador anual"
        verbose_name_plural = "Indicadores anuais"
        unique_together = ("municipio", "ano")
        ordering = ["municipio", "ano"]

    def __str__(self):
        return f"{self.municipio} — {self.ano}"


class ClusterMunicipio(models.Model):
    municipio     = models.OneToOneField(Municipio, on_delete=models.CASCADE,
                                          related_name="cluster")
    cluster_num   = models.SmallIntegerField(verbose_name="Cluster")
    cluster_label = models.CharField(max_length=30, verbose_name="Perfil")
    inse_medio    = models.FloatField(null=True, blank=True)
    abandono_medio = models.FloatField(null=True, blank=True)
    ideb_medio    = models.FloatField(null=True, blank=True)
    gasto_medio   = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Cluster"
        verbose_name_plural = "Clusters"
        ordering = ["cluster_num", "municipio"]

    def __str__(self):
        return f"{self.municipio} → {self.cluster_label}"


class ResultadoModelo(models.Model):
    nome          = models.CharField(max_length=80, unique=True)
    variavel_alvo = models.CharField(max_length=60)
    n_obs         = models.IntegerField()
    n_features    = models.SmallIntegerField()
    mediana_alvo  = models.FloatField()
    log_acuracia  = models.FloatField()
    log_auc       = models.FloatField()
    log_auc_cv    = models.FloatField()
    rf_acuracia   = models.FloatField()
    rf_auc        = models.FloatField()
    rf_auc_cv     = models.FloatField()
    top3_features = models.TextField()

    class Meta:
        verbose_name = "Resultado do modelo"
        verbose_name_plural = "Resultados dos modelos"
        ordering = ["-rf_auc"]

    def __str__(self):
        return f"{self.nome} (AUC RF={self.rf_auc:.3f})"
