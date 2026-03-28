# emendas-smspa-web

Site desenvolvido para a Secretaria Municipal de Saúde de Porto Alegre (SMS-PA).

O objetivo é ter um portal que funcione como um site de vendas. Os "compradores" são os parlamentares e os "produtos" são nossas sugestões de emenda.

## Instruções

### Pré-requisitos

- uv 
- python (>=3.13)

Checar ./pyproject.toml para as bibliotecas utilizadas.


### Setup

```sh
uv sync
uv venv
uv run ./src/manage.py createsuperuser
source .venv/bin/activate
```

### Migrações
```sh
uv run ./src/manage.py makemigrations
uv run ./src/manage.py migrate
```

### Arquivos estáticos:
```sh
uv run ./src/manage.py collectstatic
```

### Live-dev
```sh
uv run ./src/manage.py runserver
```

### Deploy

TBD (provavelmente uvicorn + whitenoise)
