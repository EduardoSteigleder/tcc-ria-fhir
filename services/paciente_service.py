import os
import requests


HAPI_BASE_URL = os.getenv(
    "FHIR_BASE_URL",
    "https://hapi.fhir.org/baseR4",
).rstrip("/")

FHIR_HEADERS = {
    "Accept": "application/fhir+json",
    "Content-Type": "application/fhir+json",
}

BR_PAIS_EXTENSION = (
    "https://rnds-fhir.saude.gov.br/StructureDefinition/BRPais-1.0"
)
BR_PAIS_SYSTEM = "http://www.saude.gov.br/fhir/r4/CodeSystem/BRPais"
TIPO_DOCUMENTO_SYSTEM = "http://terminology.hl7.org/CodeSystem/v2-0203"


class PacienteFHIRServiceError(Exception):
    pass


def _somente_digitos(valor):
    return "".join(filter(str.isdigit, str(valor or "")))


def _documento(codigo_tipo, valor):
    return {
        "use": "official",
        "type": {
            "coding": [
                {
                    "system": TIPO_DOCUMENTO_SYSTEM,
                    "code": codigo_tipo,
                }
            ]
        },
        "value": valor,
    }


def montar_patient(
    nome,
    cpf,
    cns,
    genero,
    data_nascimento,
):
    nome = str(nome or "").strip()
    cpf = _somente_digitos(cpf)
    cns = _somente_digitos(cns)
    genero = str(genero or "").strip()
    data_nascimento = str(data_nascimento or "").strip()

    if len(nome) < 3:
        raise PacienteFHIRServiceError(
            "Informe o nome completo do paciente."
        )

    if len(cpf) != 11:
        raise PacienteFHIRServiceError(
            "O CPF deve possuir 11 dígitos."
        )

    if cns and len(cns) != 15:
        raise PacienteFHIRServiceError(
            "O CNS deve possuir 15 dígitos."
        )

    if genero not in {"male", "female", "other", "unknown"}:
        raise PacienteFHIRServiceError(
            "Gênero FHIR inválido."
        )

    if not data_nascimento:
        raise PacienteFHIRServiceError(
            "Informe a data de nascimento."
        )

    identificadores = [
        _documento("TAX", cpf),
    ]

    if cns:
        identificadores.append(
            _documento("HC", cns)
        )

    # Deliberadamente sem meta.profile.
    # No ambiente de testes usado na PoC, o Simplifier não conseguiu
    # resolver o canonical do BRIndividuo quando declarado em meta.profile.
    patient = {
        "resourceType": "Patient",
        "extension": [
            {
                "url": BR_PAIS_EXTENSION,
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": BR_PAIS_SYSTEM,
                            "code": "10",
                        }
                    ]
                },
            }
        ],
        "identifier": identificadores,
        "active": True,
        "name": [
            {
                "use": "official",
                "text": nome,
            }
        ],
        "gender": genero,
        "birthDate": data_nascimento,
    }

    return patient


def _diagnostico_operation_outcome(resposta):
    try:
        corpo = resposta.json()
    except ValueError:
        return resposta.text.strip()

    if corpo.get("resourceType") != "OperationOutcome":
        return ""

    mensagens = []

    for issue in corpo.get("issue", []):
        diagnostico = issue.get("diagnostics")
        detalhes = (
            issue.get("details", {}).get("text")
        )

        if diagnostico:
            mensagens.append(diagnostico)
        elif detalhes:
            mensagens.append(detalhes)

    return " | ".join(mensagens)


def enviar_patient(patient):
    url = f"{HAPI_BASE_URL}/Patient"

    try:
        resposta = requests.post(
            url,
            json=patient,
            headers=FHIR_HEADERS,
            timeout=30,
        )
    except requests.RequestException as e:
        raise PacienteFHIRServiceError(
            f"Erro ao conectar com o HAPI FHIR: {e}"
        ) from e

    if resposta.status_code not in (200, 201):
        diagnostico = _diagnostico_operation_outcome(resposta)

        mensagem = (
            f"HAPI FHIR retornou HTTP {resposta.status_code}."
        )

        if diagnostico:
            mensagem += f" {diagnostico}"

        raise PacienteFHIRServiceError(mensagem)

    try:
        recurso = resposta.json()
    except ValueError as e:
        raise PacienteFHIRServiceError(
            "O HAPI FHIR retornou uma resposta inválida."
        ) from e

    patient_id = recurso.get("id")

    if not patient_id:
        raise PacienteFHIRServiceError(
            "O HAPI FHIR criou o recurso, mas não retornou o ID do Patient."
        )

    return {
        "id": patient_id,
        "reference": f"Patient/{patient_id}",
        "resource": recurso,
        "status_code": resposta.status_code,
        "url": f"{HAPI_BASE_URL}/Patient/{patient_id}",
    }


def cadastrar_paciente(
    nome,
    cpf,
    cns,
    genero,
    data_nascimento,
):
    patient = montar_patient(
        nome=nome,
        cpf=cpf,
        cns=cns,
        genero=genero,
        data_nascimento=data_nascimento,
    )

    resultado = enviar_patient(patient)
    resultado["json_enviado"] = patient

    return resultado


def buscar_paciente(patient_id):
    url = f"{HAPI_BASE_URL}/Patient/{patient_id}"

    try:
        resposta = requests.get(
            url,
            headers=FHIR_HEADERS,
            timeout=30,
        )
    except requests.RequestException as e:
        raise PacienteFHIRServiceError(
            f"Erro ao conectar com o HAPI FHIR: {e}"
        ) from e

    if resposta.status_code != 200:
        raise PacienteFHIRServiceError(
            f"Não foi possível buscar Patient/{patient_id}."
        )

    try:
        return resposta.json()
    except ValueError as e:
        raise PacienteFHIRServiceError(
            "O HAPI FHIR retornou uma resposta inválida."
        ) from e
