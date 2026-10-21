from pathlib import Path
from functools import lru_cache
import json
import requests


# =========================================================
# CAMINHOS DO PROJETO
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


# =========================================================
# TERMINOLOGIAS DA CATEGORIA B
# =========================================================
# Cada item informa:
# - arquivo JSON local que será criado em /data
# - uma ou mais fontes FHIR para tentativa de download
#
# O código aceita tanto ValueSet quanto CodeSystem.
# Se a primeira fonte não trouxer os conceitos, tenta a próxima.
# =========================================================

TERMINOLOGIAS = {
    "imunobiologicos": {
        "arquivo": DATA_DIR / "imunobiologicos.json",
        "fontes": [
            "https://terminologia.saude.gov.br/fhir/ValueSet-BRImunobiologico.json",
            "https://fhir.saude.go.gov.br/r4/reds-go/CodeSystem-BRImunobiologico.json",
        ],
    },
    "grupos_atendimento": {
        "arquivo": DATA_DIR / "grupos_atendimento.json",
        "fontes": [
            "https://fhir.saude.go.gov.br/r4/reds-go/CodeSystem-BRGrupoAtendimento.json",
        ],
    },
    "condicao_maternal": {
        "arquivo": DATA_DIR / "condicao_maternal.json",
        "fontes": [
            "https://terminologia.saude.gov.br/fhir/ValueSet-BRCondicaoMaternal.json",
            "https://fhir.saude.go.gov.br/r4/reds-go/CodeSystem-BRCondicaoMaternal.json",
        ],
    },
    "fabricantes_pni": {
        "arquivo": DATA_DIR / "fabricantes_pni.json",
        "fontes": [
            "https://terminologia.saude.gov.br/fhir/ValueSet-BRFabricantePNI.json",
            "https://igorevan.github.io/ria-ig/CodeSystem-BRFabricantePNI.json",
        ],
    },
    "local_aplicacao": {
        "arquivo": DATA_DIR / "local_aplicacao.json",
        "fontes": [
            "https://terminologia.saude.gov.br/fhir/ValueSet-BRLocalAplicacao.json",
            "https://fhir.saude.go.gov.br/r4/reds-go/CodeSystem-BRLocalAplicacao.json",
        ],
    },
    "via_administracao": {
        "arquivo": DATA_DIR / "via_administracao.json",
        "fontes": [
            "https://terminologia.saude.gov.br/fhir/ValueSet-BRViaAdministracao.json",
            "https://fhir.saude.go.gov.br/r4/reds-go/CodeSystem-BRViaAdministracao.json",
        ],
    },
    "estrategia_vacinacao": {
        "arquivo": DATA_DIR / "estrategia_vacinacao.json",
        "fontes": [
            "https://terminologia.saude.gov.br/fhir/ValueSet-BREstrategiaVacinacao.json",
            "https://igorevan.github.io/ria-ig/CodeSystem-BREstrategiaVacinacao.json",
        ],
    },
    "registro_origem": {
        "arquivo": DATA_DIR / "registro_origem.json",
        "fontes": [
            "https://terminologia.saude.gov.br/fhir/ValueSet-BRRegistroOrigem.json",
        ],
    },
    "paises": {
        "arquivo": DATA_DIR / "paises.json",
        "fontes": [
            "https://terminologia.saude.gov.br/fhir/ValueSet-BRPais.json",
            "https://fhir.saude.go.gov.br/r4/reds-go/CodeSystem-BRPais.json",
        ],
    },
    "cbo": {
        "arquivo": DATA_DIR / "cbo.json",
        "fontes": [
            "https://terminologia.saude.gov.br/fhir/ValueSet-BROcupacao.json",
            "https://fhir.saude.go.gov.br/r4/reds-go/CodeSystem-BRCBO.json",
        ],
    },
    "brcid10": {
        "arquivo": DATA_DIR / "brcid10.json",
        "fontes": [
            "https://fhir.saude.gov.br/rira/en/CodeSystem-BRCID10.json",
        ],
    },
}


# =========================================================
# EXCEÇÃO
# =========================================================

class TerminologiaIndisponivel(Exception):
    pass


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def _baixar_json(url):
    resposta = requests.get(
        url,
        headers={
            "Accept": "application/fhir+json, application/json"
        },
        timeout=20,
    )
    resposta.raise_for_status()
    return resposta.json()


def _salvar_cache(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as file:
        json.dump(
            dados,
            file,
            ensure_ascii=False,
            indent=4,
            sort_keys=True,
        )


def _carregar_cache(arquivo):
    if not arquivo.exists():
        return None

    try:
        with open(arquivo, "r", encoding="utf-8") as file:
            dados = json.load(file)
        if isinstance(dados, dict):
            return dados
    except (json.JSONDecodeError, OSError):
        pass

    return None


def _conceito_inativo(conceito):
    if conceito.get("inactive") is True:
        return True

    for propriedade in conceito.get("property", []):
        if (
            propriedade.get("code") == "inactive"
            and propriedade.get("valueBoolean") is True
        ):
            return True

    return False


def _extrair_conceitos_codesystem(conceitos, resultado):
    for conceito in conceitos:
        codigo = str(conceito.get("code", "")).strip()
        descricao = str(conceito.get("display", "")).strip()

        if codigo and not _conceito_inativo(conceito):
            resultado[codigo] = descricao or codigo

        filhos = conceito.get("concept", [])
        if filhos:
            _extrair_conceitos_codesystem(filhos, resultado)


def _extrair_expansion(contains, resultado):
    for item in contains:
        codigo = str(item.get("code", "")).strip()
        descricao = str(item.get("display", "")).strip()

        if codigo and not _conceito_inativo(item):
            resultado[codigo] = descricao or codigo

        filhos = item.get("contains", [])
        if filhos:
            _extrair_expansion(filhos, resultado)


def _extrair_compose(includes, resultado):
    for include in includes:
        for conceito in include.get("concept", []):
            codigo = str(conceito.get("code", "")).strip()
            descricao = str(conceito.get("display", "")).strip()

            if codigo and not _conceito_inativo(conceito):
                resultado[codigo] = descricao or codigo


def _extrair_de_recurso_fhir(recurso):
    resultado = {}
    tipo = recurso.get("resourceType")

    if tipo == "CodeSystem":
        _extrair_conceitos_codesystem(
            recurso.get("concept", []),
            resultado,
        )

    elif tipo == "ValueSet":
        compose = recurso.get("compose", {})
        _extrair_compose(
            compose.get("include", []),
            resultado,
        )

        if not resultado:
            expansion = recurso.get("expansion", {})
            _extrair_expansion(
                expansion.get("contains", []),
                resultado,
            )

    return resultado


def _baixar_terminologia(chave):
    configuracao = TERMINOLOGIAS[chave]
    erros = []

    for url in configuracao["fontes"]:
        try:
            recurso = _baixar_json(url)
            dados = _extrair_de_recurso_fhir(recurso)

            if dados:
                return dados

            erros.append(
                f"{url}: recurso sem conceitos disponíveis"
            )

        except (requests.RequestException, ValueError) as erro:
            erros.append(f"{url}: {erro}")

    detalhes = " | ".join(erros)
    raise TerminologiaIndisponivel(
        f"Não foi possível carregar a terminologia '{chave}'. "
        f"Detalhes: {detalhes}"
    )


@lru_cache(maxsize=None)
def carregar_terminologia(chave):
    if chave not in TERMINOLOGIAS:
        raise ValueError(f"Terminologia desconhecida: {chave}")

    arquivo = TERMINOLOGIAS[chave]["arquivo"]

    # CBO É UMA LISTA CURADA E FIXA: NÃO BAIXAR NEM SOBRESCREVER.
    # VALE TAMBÉM PARA atualizar_terminologias() E PARA VALIDAÇÃO.
    if chave == "cbo":
        dados = _carregar_cache(arquivo)
        if not dados:
            raise TerminologiaIndisponivel(
                "Lista CBO local indisponível ou vazia: data/cbo.json"
            )
        return dados

    try:
        dados = _baixar_terminologia(chave)
        _salvar_cache(arquivo, dados)
        return dados

    except TerminologiaIndisponivel as erro:
        cache = _carregar_cache(arquivo)

        if cache:
            return cache

        raise TerminologiaIndisponivel(
            f"{erro} E ainda não existe cache local em '{arquivo.name}'."
        ) from erro


def validar_terminologia(chave, codigo):
    codigo = str(codigo).strip()
    dados = carregar_terminologia(chave)
    descricao = dados.get(codigo)

    return {
        "valido": descricao is not None,
        "codigo": codigo,
        "descricao": descricao or "",
    }


# =========================================================
# FUNÇÕES COMPATÍVEIS COM O APP.PY ATUAL
# =========================================================

def carregar_imunobiologicos():
    return carregar_terminologia("imunobiologicos")


def validar_imunobiologico(codigo):
    return validar_terminologia("imunobiologicos", codigo)


def carregar_grupos_atendimento():
    return carregar_terminologia("grupos_atendimento")


def validar_grupo_atendimento(codigo):
    return validar_terminologia("grupos_atendimento", codigo)


# =========================================================
# NOVAS TERMINOLOGIAS
# =========================================================

def validar_condicao_maternal(codigo):
    return validar_terminologia("condicao_maternal", codigo)


def validar_fabricante_pni(codigo):
    return validar_terminologia("fabricantes_pni", codigo)


def validar_local_aplicacao(codigo):
    return validar_terminologia("local_aplicacao", codigo)


def validar_via_administracao(codigo):
    return validar_terminologia("via_administracao", codigo)


def validar_estrategia_vacinacao(codigo):
    return validar_terminologia("estrategia_vacinacao", codigo)


def validar_registro_origem(codigo):
    return validar_terminologia("registro_origem", codigo)


def validar_pais(codigo):
    return validar_terminologia("paises", codigo)


def validar_cbo(codigo):
    return validar_terminologia("cbo", codigo)


# =========================================================
# ATUALIZAÇÃO/Geração DE TODOS OS JSONS
# =========================================================

def atualizar_terminologias():
    carregar_terminologia.cache_clear()

    resultado = {}

    for chave in TERMINOLOGIAS:
        dados = carregar_terminologia(chave)
        resultado[chave] = len(dados)

    return resultado


# =========================================================
# TESTE DIRETO DO ARQUIVO
# =========================================================

if __name__ == "__main__":
    try:
        resultado = atualizar_terminologias()

        print("Terminologias carregadas com sucesso.\n")

        for chave, quantidade in resultado.items():
            arquivo = TERMINOLOGIAS[chave]["arquivo"].name
            print(f"{arquivo}: {quantidade} códigos")

        print(f"\nArquivos gravados em: {DATA_DIR}")

    except TerminologiaIndisponivel as erro:
        print("Erro:", erro)
