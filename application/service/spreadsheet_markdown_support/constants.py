"""Constants shared by spreadsheet markdown helpers."""

MAX_SPREADSHEET_ROWS = 1000
MAX_SPREADSHEET_COLUMNS = 40
MAX_SAMPLE_VALUES = 5
MAX_CELL_CHARS = 200
CSV_SNIFF_DELIMITERS = ",;\t|"

PERSON_BLOCKLIST = {
    "nome",
    "tbd",
    "total",
    "totais",
    "subtotal",
    "sub total",
    "target",
    "rpa",
    "profissionais",
    "bolsas",
    "custo dell",
    "custo total de rh mensal",
    "encargos clt",
    "descricoes",
    "descricao",
    "historico de margem para prestacao de contas dell",
    "rh direto bolsas",
    "rh direto celetistas",
    "rh indireto administrativo",
}

PERSON_PREFIX_BLOCKLIST = (
    "rh ",
    "sub total",
    "subtotal",
    "total ",
    "totais ",
    "custo ",
    "historico ",
    "margem ",
)

ROLE_BLOCKLIST = {
    "ufc",
    "s vinculo",
    "column",
    "custo dell",
    "total",
    "totais",
}
