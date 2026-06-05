from django.contrib import admin
from .models import Municipio, IndicadorAnual, ClusterMunicipio, ResultadoModelo


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display  = ('co_municipio', 'no_municipio', 'uf')
    search_fields = ('no_municipio', 'co_municipio')
    list_filter   = ('uf',)


@admin.register(IndicadorAnual)
class IndicadorAnualAdmin(admin.ModelAdmin):
    list_display  = ('municipio', 'ano', 'abandono_med_total', 'ideb_medio', 'gasto_aluno')
    list_filter   = ('ano',)
    search_fields = ('municipio__no_municipio',)
    raw_id_fields = ('municipio',)


@admin.register(ClusterMunicipio)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ('municipio', 'cluster_label', 'abandono_medio', 'ideb_medio')
    list_filter  = ('cluster_num',)


@admin.register(ResultadoModelo)
class ResultadoModeloAdmin(admin.ModelAdmin):
    list_display = ('nome', 'n_obs', 'rf_auc', 'rf_auc_cv', 'top3_features')
