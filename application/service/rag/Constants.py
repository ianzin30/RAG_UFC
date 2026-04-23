# Simple: Keywords and settings for the search system
PERSON_QUERY_TERMS = {
    "nome",
    "nomes",
    "pessoa",
    "pessoas",
    "trabalhador",
    "trabalhadores",
    "funcionario",
    "funcionarios",
    "funcionaria",
    "funcionarias",
    "colaborador",
    "colaboradores",
    "pesquisador",
    "pesquisadores",
    "coordenador",
    "coordenadores",
    "equipe",
    "quem",
}
ROLE_HINT_TERMS = {
    "coordenador",
    "pesquisador",
    "analista",
    "desenvolvedor",
    "testador",
    "designer",
    "consultor",
    "gerente",
    "especialista",
}
QUERY_STOPWORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "ou",
    "para",
    "por",
    "qual",
    "quais",
    "que",
    "sobre",
    "sao",
    "se",
    "um",
    "uma",
}
MONTH_NAME_TO_NUMBER = {
    "janeiro": "01",
    "fevereiro": "02",
    "marco": "03",
    "abril": "04",
    "maio": "05",
    "junho": "06",
    "julho": "07",
    "agosto": "08",
    "setembro": "09",
    "outubro": "10",
    "novembro": "11",
    "dezembro": "12",
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}
MONTH_NUMBER_TO_NAME = {
    "01": "janeiro",
    "02": "fevereiro",
    "03": "marco",
    "04": "abril",
    "05": "maio",
    "06": "junho",
    "07": "julho",
    "08": "agosto",
    "09": "setembro",
    "10": "outubro",
    "11": "novembro",
    "12": "dezembro",
}
SPREADSHEET_SUFFIXES = (".xlsx", ".csv")
ROOT_COLLECTION_KEY = "__root__"
RAG_INDEX_CACHE_VERSION = 7
MODE_CASUAL = "casual"
MODE_RETRIEVAL = "retrieval"
MODE_SWITCH_TO_RETRIEVAL_COMMAND = "BUSCAR"
MODE_SWITCH_TO_CASUAL_COMMAND = "CASUAL"
CASUAL_RESPONSE_TITLE = "CASUAL"
RETRIEVAL_RESPONSE_TITLE = "RETRIEVAL"
CASUAL_RESPONSE_FOOTER = 'Para trocar para o modo de retrieval, digite "BUSCAR".'
RETRIEVAL_RESPONSE_FOOTER = 'Para sair do modo de retrieval, digite "CASUAL".'
REWRITE_REFERENCE_MARKERS = (
    "daquele",
    "daquela",
    "daqueles",
    "daquelas",
    "desse",
    "dessa",
    "desses",
    "dessas",
    "nele",
    "nela",
    "neles",
    "nelas",
    "sobre ele",
    "sobre ela",
    "sobre isso",
    "sobre essa",
    "sobre esse",
)


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default
