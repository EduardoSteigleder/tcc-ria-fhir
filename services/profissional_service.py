import os
import re
from typing import Optional

import requests


HAPI_BASE_URL = os.getenv(
    "FHIR_BASE_URL",
    "https://hapi.fhir.org/baseR4"
).rstrip("/")

TIPO_DOCUMENTO_SYSTEM = (
    "http://terminology.hl7.org/CodeSystem/v2-0203"
)

TIPO_IDENTIFICADOR_RNDS_SYSTEM = (
    "https://rnds-fhir.saude.gov.br/CodeSystem/BRTipoIdentificador"
)

CBO_SYSTEM = (
    "https://rnds-fhir.saude.gov.br/CodeSystem/BRCBO"
)


# O BRProfissional usa Practitioner.identifier para os documentos.
# O "system" direto de Identifier é proibido no BRDocumentoIndividuo;
# por isso o tipo é informado em identifier.type.coding.
TIPOS_CONSELHO = {
    "CRM": {
        "system": TIPO_DOCUMENTO_SYSTEM,
        "code": "MD",
    },
    "COREN": {
        "system": TIPO_DOCUMENTO_SYSTEM,
        "code": "RN",
    },
    "CRO": {
        "system": TIPO_DOCUMENTO_SYSTEM,
        "code": "DDS",
    },
    "CRF": {
        "system": TIPO_IDENTIFICADOR_RNDS_SYSTEM,
        "code": "BRACRF",
    },
    "CREFITO": {
        "system": TIPO_IDENTIFICADOR_RNDS_SYSTEM,
        "code": "BRACREFITO",
    },
    "CRN": {
        "system": TIPO_IDENTIFICADOR_RNDS_SYSTEM,
        "code": "BRACRN",
    },
    "CRP": {
        "system": TIPO_IDENTIFICADOR_RNDS_SYSTEM,
        "code": "BRACRP",
    },
}


class ProfissionalFHIRServiceError(Exception):
    pass


def _somente_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def _documento(system: str, code: str, value: str) -> dict:
    return {
        "use": "official",
        "type": {
            "coding": [
                {
                    "system": system,
                    "code": code,
                }
            ]
        },
        "value": value,
    }


def montar_practitioner(
    *,
    nome: str,
    cpf: str,
    cns: str,
    genero: str,
    data_nascimento: str,
    cbo: str,
    conselho: str,
    numero_registro: str,
) -> dict:
    """
    Monta um Practitioner seguindo as restrições relevantes
    do perfil RNDS BRProfissional-1.0 usadas neste protótipo.

    Importante:
    - active é sempre true;
    - name.use é sempre official;
    - CPF/CNS/registro profissional entram como identifier;
    - CBO entra em qualification.code;
    - qualification.identifier NÃO é usado, pois o perfil o proíbe.
    """

    nome = (nome or "").strip()
    cpf = _somente_digitos(cpf)
    cns = _somente_digitos(cns)
    genero = (genero or "").strip()
    data_nascimento = (data_nascimento or "").strip()
    cbo = (cbo or "").strip()
    conselho = (conselho or "").strip().upper()
    numero_registro = (numero_registro or "").strip()

    if not nome:
        raise ProfissionalFHIRServiceError(
            "Nome do profissional não informado."
        )

    if len(cpf) != 11:
        raise ProfissionalFHIRServiceError(
            "CPF deve possuir 11 dígitos."
        )

    if cns and len(cns) != 15:
        raise ProfissionalFHIRServiceError(
            "CNS deve possuir 15 dígitos."
        )

    if genero not in {"male", "female", "other", "unknown"}:
        raise ProfissionalFHIRServiceError(
            "Gênero FHIR inválido."
        )

    if not data_nascimento:
        raise ProfissionalFHIRServiceError(
            "Data de nascimento não informada."
        )

    if not cbo:
        raise ProfissionalFHIRServiceError(
            "CBO não informado."
        )

    tipo_conselho = TIPOS_CONSELHO.get(conselho)
    if not tipo_conselho:
        raise ProfissionalFHIRServiceError(
            "Conselho profissional ainda não mapeado para "
            "BRTipoDocumentoIndividuo."
        )

    if not numero_registro:
        raise ProfissionalFHIRServiceError(
            "Número do registro profissional não informado."
        )

    identifiers = [
        _documento(
            TIPO_DOCUMENTO_SYSTEM,
            "TAX",
            cpf,
        )
    ]

    if cns:
        identifiers.append(
            _documento(
                TIPO_DOCUMENTO_SYSTEM,
                "HC",
                cns,
            )
        )

    identifiers.append(
        _documento(
            tipo_conselho["system"],
            tipo_conselho["code"],
            numero_registro,
        )
    )

    practitioner = {
        "resourceType": "Practitioner",
        "identifier": identifiers,
        "active": True,
        "name": [
            {
                "use": "official",
                "text": nome,
            }
        ],
        "gender": genero,
        "birthDate": data_nascimento,
        "qualification": [
            {
                "code": {
                    "coding": [
                        {
                            "system": CBO_SYSTEM,
                            "code": cbo,
                        }
                    ]
                }
            }
        ],
    }

    return practitioner


def enviar_practitioner(
    practitioner: dict,
    *,
    base_url: Optional[str] = None,
    timeout: int = 30,
) -> dict:
    url_base = (base_url or HAPI_BASE_URL).rstrip("/")
    url = f"{url_base}/Practitioner"

    try:
        resposta = requests.post(
            url,
            json=practitioner,
            headers={
                "Accept": "application/fhir+json",
                "Content-Type": "application/fhir+json",
            },
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise ProfissionalFHIRServiceError(
            f"Erro de comunicação com o servidor FHIR: {exc}"
        ) from exc

    try:
        corpo = resposta.json()
    except ValueError:
        corpo = {
            "raw": resposta.text
        }

    if resposta.status_code not in {200, 201}:
        diagnostico = None

        if isinstance(corpo, dict):
            issues = corpo.get("issue") or []
            if issues:
                diagnostico = issues[0].get("diagnostics")

        detalhe = diagnostico or str(corpo)

        raise ProfissionalFHIRServiceError(
            f"HAPI FHIR retornou HTTP {resposta.status_code}: {detalhe}"
        )

    if not isinstance(corpo, dict) or not corpo.get("id"):
        raise ProfissionalFHIRServiceError(
            "Servidor FHIR respondeu sem o id do Practitioner."
        )

    return {
        "id": corpo["id"],
        "reference": f"Practitioner/{corpo['id']}",
        "resource": corpo,
        "status_code": resposta.status_code,
        "url": url,
    }


def cadastrar_profissional(**dados) -> dict:
    practitioner = montar_practitioner(**dados)
    resultado = enviar_practitioner(practitioner)

    # Mantemos também o JSON enviado para facilitar os testes da PoC.
    resultado["json_enviado"] = practitioner

    return resultado



def buscar_profissional(practitioner_id: str) -> dict:
    url = f"{HAPI_BASE_URL}/Practitioner/{practitioner_id}"
    try:
        resposta = requests.get(url, headers={"Accept": "application/fhir+json"}, timeout=30)
    except requests.RequestException as exc:
        raise ProfissionalFHIRServiceError(f"Erro de comunicação com o servidor FHIR: {exc}") from exc
    if resposta.status_code != 200:
        raise ProfissionalFHIRServiceError(f"Não foi possível buscar Practitioner/{practitioner_id}.")
    try:
        recurso = resposta.json()
    except ValueError as exc:
        raise ProfissionalFHIRServiceError("O HAPI FHIR retornou uma resposta inválida.") from exc
    if recurso.get("resourceType") != "Practitioner":
        raise ProfissionalFHIRServiceError("O recurso retornado não é um Practitioner.")
    return recurso
