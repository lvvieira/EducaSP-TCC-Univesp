# EducaSP Analytics

Aplicação web Django que dá interface aos resultados do TCC **"Determinantes do Abandono Escolar e do Desempenho Acadêmico nos Municípios do Estado de São Paulo: uma Análise Exploratória e Preditiva com Dados Públicos"** (UNIVESP, Bacharelado em Ciência de Dados, 2026).

A aplicação consolida indicadores educacionais, socioeconômicos e de infraestrutura dos **645 municípios paulistas** em um painel interativo com mapa, ranqueamento, busca por município e visualização dos modelos preditivos (Random Forest) e da clusterização (K-Means).

Demo pública: https://204.168.152.11.nip.io/

## Stack

- Python 3.12
- Django 4.2
- SQLite (banco já populado em `db.sqlite3`, 645 municípios)
- WhiteNoise para servir estáticos
- Gunicorn em produção

## Rodando localmente (banca/orientadores)

```bash
python -m venv .venv
source .venv/bin/activate           # Linux/Mac/WSL
# .venv\Scripts\activate            # Windows PowerShell

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Acesse http://127.0.0.1:8000.

> Para ver a aplicação **com dados reais**, utilize a demo pública: https://204.168.152.11.nip.io/

## Estrutura

```
webapp/
├── manage.py
├── requirements.txt
├── db.sqlite3                      # apenas o esquema, sem dados (ver aviso acima)
├── tcc_webapp/                     # configurações Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── education/                      # app principal
│   ├── models.py                   # modelo Municipio
│   ├── admin.py
│   ├── management/commands/
│   │   └── importar_dados.py       # importa df_master_sp.csv
│   ├── migrations/
│   └── templates/education/        # templates HTML
└── static/css/main.css             # estilos da aplicação
```

## Variáveis de ambiente (produção)

Em produção, defina via `.env` ou `export`:

| Variável | Descrição | Exemplo |
|---|---|---|
| `SECRET_KEY` | Chave secreta do Django | string aleatória de 50+ caracteres |
| `DEBUG` | Modo debug | `False` |
| `ALLOWED_HOSTS` | Hosts permitidos | `meudominio.com,www.meudominio.com` |
| `CSRF_TRUSTED_ORIGINS` | Origens autorizadas para CSRF | `https://meudominio.com` |
| `DATABASE_URL` | URL do Postgres (opcional, usa SQLite por padrão) | `postgres://user:pass@host:5432/db` |
| `SECURE_SSL_REDIRECT` | Força HTTPS | `True` |
| `SECURE_HSTS_SECONDS` | Tempo de HSTS | `31536000` |

## Sobre o TCC

Apresentado na UNIVESP em junho de 2026 pela equipe (8 autores). Banco de dados consolidado a partir de fontes públicas (INEP, IBGE, FNDE, SEDUC-SP), totalizando **3.870 observações × 81 indicadores** entre 2017 e 2023.

Principais achados:
- O **INSE** (nível socioeconômico) é o determinante dominante do desempenho acadêmico (SAEB, ENEM)
- A **relação aluno-docente** é o determinante dominante do risco de abandono no Ensino Médio
- Abandono e desempenho **não compartilham os mesmos determinantes**, o que tem implicações para políticas públicas

## Licença

**Todos os direitos reservados.** Consulte o arquivo [`LICENSE`](LICENSE) para o texto integral (PT-BR e EN).

Contato: lucas.vieira@lvvieira.com
