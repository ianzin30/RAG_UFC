"""Small, versioned Portuguese corpus; no claims about production quality."""

DOCUMENTS = {
    "marco.md": "# Ata de março\n\n## Projeto Atlas\nJoão Silva ficou responsável pelo Projeto Atlas. O identificador interno do projeto é ZX-741.\n",
    "abril.md": "# Ata de abril\n\n## Coordenação\nMaria Costa substituiu João Silva na coordenação do Projeto Atlas em abril.\n",
    "registro.md": "# Registro interno\n\n## ZX-741\nO projeto ZX-741 recebeu financiamento da Fundação Aurora.\n",
    "equipe.md": "# Equipe\n\n## Participantes\nAna Lima é engenheira. Bruno Reis é analista. Ambos trabalham em Fortaleza.\n",
    "custos.md": "# Custos\nDocument Type: spreadsheet\n\n## Sheet: Gastos\n- Spreadsheet file custos.xlsx | Sheet Gastos | Row 2: Item: Servidor | Valor: 100\n- Spreadsheet file custos.xlsx | Sheet Gastos | Row 3: Item: Rede | Valor: 200\n",
}
CASES = [
    {
        "id": "fact",
        "category": "single-document factual",
        "question": "Quem ficou responsável pelo Projeto Atlas em março?",
        "expected": ["João Silva"],
        "required": [["João Silva ficou responsável"]],
    },
    {
        "id": "cross",
        "category": "cross-document",
        "question": "Compare os responsáveis pelo Atlas na ata de março e na ata de abril.",
        "expected": ["João Silva", "Maria Costa"],
        "required": [["João Silva ficou responsável"], ["Maria Costa substituiu"]],
    },
    {
        "id": "hop",
        "category": "multi-hop",
        "question": "Qual fundação financiou o projeto coordenado por João Silva em março?",
        "expected": ["Fundação Aurora"],
        "required": [["ZX-741"], ["Fundação Aurora"]],
    },
    {
        "id": "entity",
        "category": "entity lookup",
        "question": "Qual é a profissão de Ana Lima?",
        "expected": ["engenheira"],
        "required": [["Ana Lima é engenheira"]],
    },
    {
        "id": "list",
        "category": "list/aggregation",
        "question": "Liste os participantes da equipe e suas profissões.",
        "expected": ["Ana Lima", "Bruno Reis"],
        "required": [["Ana Lima é engenheira"], ["Bruno Reis é analista"]],
    },
    {
        "id": "summary",
        "category": "summary",
        "question": "Resuma as mudanças na coordenação do Atlas entre março e abril.",
        "expected": ["João Silva", "Maria Costa"],
        "required": [["João Silva ficou responsável"], ["Maria Costa substituiu"]],
    },
    {
        "id": "table",
        "category": "spreadsheet/table",
        "question": "Qual é o valor do item Servidor na planilha de custos?",
        "expected": ["100"],
        "required": [["Servidor | Valor: 100"]],
    },
    {
        "id": "absent",
        "category": "unanswerable",
        "question": "Qual é o CPF de Ana Lima?",
        "expected": [],
        "required": [],
    },
    {
        "id": "follow",
        "category": "follow-up conversational",
        "question": "E quem o substituiu em abril?",
        "history": [
            {"role": "user", "content": "Quem coordenava o Atlas em março?"},
            {"role": "assistant", "content": "João Silva."},
        ],
        "expected": ["Maria Costa"],
        "required": [["Maria Costa substituiu"]],
    },
]
