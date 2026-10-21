import os
import json
from pathlib import Path
from datetime import datetime
import requests

HAPI_BASE_URL = os.getenv("FHIR_BASE_URL", "https://hapi.fhir.org/baseR4").rstrip("/")
HEADERS = {"Accept": "application/fhir+json", "Content-Type": "application/fhir+json"}
LOG_DIR = Path(__file__).resolve().parent.parent / "logs" / "ria"

class FHIRServiceError(Exception):
    pass

def _erro_resposta(resp):
    try:
        data = resp.json()
        if data.get("resourceType") == "OperationOutcome":
            textos = [i.get("diagnostics") or i.get("details", {}).get("text") for i in data.get("issue", [])]
            return "; ".join(t for t in textos if t)
    except Exception:
        pass
    return resp.text[:500] or f"HTTP {resp.status_code}"

def _post(resource_type, resource):
    try:
        resp = requests.post(f"{HAPI_BASE_URL}/{resource_type}", headers=HEADERS, json=resource, timeout=30)
    except requests.RequestException as e:
        raise FHIRServiceError(f"Falha de comunicação com o HAPI FHIR: {e}") from e
    if resp.status_code not in (200, 201):
        raise FHIRServiceError(f"Erro ao criar {resource_type}: {_erro_resposta(resp)}")
    data = resp.json()
    if not data.get("id"):
        raise FHIRServiceError(f"O HAPI não retornou o id de {resource_type}.")
    return data

def _get(resource_type, resource_id):
    try:
        resp = requests.get(
            f"{HAPI_BASE_URL}/{resource_type}/{resource_id}",
            headers={"Accept": "application/fhir+json"},
            timeout=30,
        )
    except requests.RequestException as e:
        raise FHIRServiceError(f"Falha ao consultar {resource_type} no HAPI FHIR: {e}") from e
    if resp.status_code != 200:
        raise FHIRServiceError(f"Não foi possível localizar {resource_type}/{resource_id} no HAPI FHIR: {_erro_resposta(resp)}")
    data = resp.json()
    if data.get("resourceType") != resource_type:
        raise FHIRServiceError(f"O recurso informado não é um {resource_type} válido.")
    return data

def _cpf_patient(patient):
    for identificador in patient.get("identifier", []):
        for coding in identificador.get("type", {}).get("coding", []):
            if coding.get("code") == "TAX" and identificador.get("value"):
                return "".join(filter(str.isdigit, str(identificador["value"])))
    raise FHIRServiceError("O Patient informado não possui CPF para montar o BRIndividuo do Condition.")


def _condition(cpf, cid10):
    return {
        "resourceType": "Condition",
        "meta": {"profile": ["http://www.saude.gov.br/fhir/r4/StructureDefinition/BRCID10Avaliado-1.0"]},
        "code": {"coding": [{"system": "http://www.saude.gov.br/fhir/r4/CodeSystem/BRCID10", "code": cid10}]},
        "subject": {
            "identifier": {
                "system": "http://www.saude.gov.br/fhir/r4/StructureDefinition/BRIndividuo-1.0",
                "value": cpf,
            }
        },
    }


def _salvar_log_json(nome, recurso):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    caminho = LOG_DIR / nome
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(recurso, arquivo, ensure_ascii=False, indent=2)
    return str(caminho)


def _immunization(*, patient_id, practitioner_id, imunobiologico, data_vacinacao, lote, dose,
                  grupo_atendimento, condicao_maternal, fabricante_pni, local_aplicacao,
                  via_administracao, estrategia_vacinacao, condition_id):
    return {
        "resourceType": "Immunization",
        "meta": {"profile": ["http://www.saude.gov.br/fhir/r4/StructureDefinition/BRImunobiologicoAdministrado-3.0"]},
        "extension": [
            {"url": "http://www.saude.gov.br/fhir/r4/StructureDefinition/BRGrupoAtendimento",
             "valueCodeableConcept": {"coding": [{"system": "http://www.saude.gov.br/fhir/r4/CodeSystem/BRGrupoAtendimento", "code": grupo_atendimento}]}},
            {"url": "http://www.saude.gov.br/fhir/r4/StructureDefinition/BRCondicaoMaternal",
             "valueCodeableConcept": {"coding": [{"system": "http://www.saude.gov.br/fhir/r4/CodeSystem/BRCondicaoMaternal", "code": condicao_maternal}]}}
        ],
        "status": "completed",
        "vaccineCode": {"coding": [{"system": "http://www.saude.gov.br/fhir/r4/CodeSystem/BRImunobiologico", "code": imunobiologico}]},
        "patient": {"reference": f"Patient/{patient_id}"},
        "occurrenceDateTime": data_vacinacao,
        "primarySource": True,
        "manufacturer": {"identifier": {"system": "http://www.saude.gov.br/fhir/r4/CodeSystem/BRFabricantePNI", "value": fabricante_pni}},
        "lotNumber": lote,
        "site": {"coding": [{"system": "http://www.saude.gov.br/fhir/r4/CodeSystem/BRLocalAplicacao", "code": local_aplicacao}]},
        "route": {"coding": [{"system": "http://www.saude.gov.br/fhir/r4/CodeSystem/BRViaAdministracao", "code": via_administracao}]},
        "performer": [{"actor": {"reference": f"Practitioner/{practitioner_id}"}}],
        "reasonReference": [{"reference": f"Condition/{condition_id}"}],
        "protocolApplied": [{
            "extension": [{"url": "http://www.saude.gov.br/fhir/r4/StructureDefinition/BREstrategiaVacinacao-1.0",
                           "valueCodeableConcept": {"coding": [{"system": "http://www.saude.gov.br/fhir/r4/CodeSystem/BREstrategiaVacinacao", "code": estrategia_vacinacao}]}}],
            "doseNumberString": dose
        }]
    }

def _composition(patient_id, cnes, immunization_id):
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "resourceType": "Composition",
        "meta": {"profile": ["http://www.saude.gov.br/fhir/r4/StructureDefinition/BRRegistroImunobiologicoAdministradoRotina-2.0"]},
        "status": "final",
        "type": {"coding": [{"system": "http://www.saude.gov.br/fhir/r4/CodeSystem/BRTipoDocumento", "code": "RIA"}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "date": agora,
        "author": [{"identifier": {"system": "http://www.saude.gov.br/fhir/r4/StructureDefinition/BREstabelecimentoSaude-1.0", "value": cnes}}],
        "title": "Registro de Imunobiologico Administrado na Rotina",
        "section": [{"entry": [{"reference": f"Immunization/{immunization_id}"}]}]
    }

def cadastrar_vacinacao(*, patient_id, practitioner_id, imunobiologico, descricao_imunobiologico,
                         data_vacinacao, lote, dose, grupo_atendimento, descricao_grupo, cnes,
                         condicao_maternal, fabricante_pni, local_aplicacao, via_administracao,
                         estrategia_vacinacao, cid10):
    patient_id = "".join(filter(str.isdigit, str(patient_id)))
    practitioner_id = "".join(filter(str.isdigit, str(practitioner_id)))
    if not patient_id:
        raise FHIRServiceError("Informe o código do paciente.")
    if not practitioner_id:
        raise FHIRServiceError("Informe o código do profissional de saúde.")
    patient = _get("Patient", patient_id)
    practitioner = _get("Practitioner", practitioner_id)

    cpf = _cpf_patient(patient)
    condition_enviado = _condition(cpf, cid10)
    condition = _post("Condition", condition_enviado)

    immunization_enviado = _immunization(
        patient_id=patient_id, practitioner_id=practitioner_id,
        imunobiologico=imunobiologico, data_vacinacao=data_vacinacao, lote=lote, dose=dose,
        grupo_atendimento=grupo_atendimento, condicao_maternal=condicao_maternal,
        fabricante_pni=fabricante_pni, local_aplicacao=local_aplicacao,
        via_administracao=via_administracao, estrategia_vacinacao=estrategia_vacinacao,
        condition_id=condition["id"],
    )
    immunization = _post("Immunization", immunization_enviado)

    composition_enviado = _composition(patient_id, cnes, immunization["id"])
    composition = _post("Composition", composition_enviado)

    bundle_enviado = {
        "resourceType": "Bundle",
        "type": "document",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "entry": [
            {"fullUrl": f"{HAPI_BASE_URL}/Composition/{composition['id']}", "resource": composition},
            {"fullUrl": f"{HAPI_BASE_URL}/Immunization/{immunization['id']}", "resource": immunization},
            {"fullUrl": f"{HAPI_BASE_URL}/Condition/{condition['id']}", "resource": condition},
            {"fullUrl": f"{HAPI_BASE_URL}/Patient/{patient_id}", "resource": patient},
            {"fullUrl": f"{HAPI_BASE_URL}/Practitioner/{practitioner_id}", "resource": practitioner},
        ],
    }
    bundle = _post("Bundle", bundle_enviado)

    _salvar_log_json(f"Condition_{condition['id']}.json", condition_enviado)
    _salvar_log_json(f"Immunization_{immunization['id']}.json", immunization_enviado)
    _salvar_log_json(f"Composition_{composition['id']}.json", composition_enviado)
    log_bundle = _salvar_log_json(f"Bundle_{bundle['id']}.json", bundle_enviado)

    return {
        "immunization_id": immunization["id"],
        "condition_id": condition["id"],
        "composition_id": composition["id"],
        "bundle_id": bundle["id"],
        "patient_reference": f"Patient/{patient_id}",
        "practitioner_reference": f"Practitioner/{practitioner_id}",
        "json_condition": condition_enviado,
        "json_immunization": immunization_enviado,
        "json_composition": composition_enviado,
        "json_bundle": bundle_enviado,
        "log_bundle": log_bundle,
    }



def buscar_registro_ria(bundle_id):
    return _get("Bundle", str(bundle_id))
