from flask import Flask, render_template, request, jsonify

from datetime import datetime, date

from inspect import signature

from database.database import (
    inicializar_banco, salvar_paciente, listar_pacientes,
    salvar_profissional, listar_profissionais,
    salvar_registro_ria, listar_registros_ria,
)



from services.terminologias import (

    carregar_terminologia,

    validar_terminologia,

    TerminologiaIndisponivel,

)



from services.fhir_service import (

    cadastrar_vacinacao,

    buscar_registro_ria,

    FHIRServiceError,

)



from services.profissional_service import (

    cadastrar_profissional,

    buscar_profissional,

    ProfissionalFHIRServiceError,

)



from services.paciente_service import (

    cadastrar_paciente,

    buscar_paciente,

    PacienteFHIRServiceError,

)





app = Flask(__name__)



inicializar_banco()





DOSES = {

    "1": "1ª Dose",

    "2": "2ª Dose",

    "3": "3ª Dose",

    "4": "4ª Dose",

    "5": "5ª Dose",

    "6": "1º Reforço",

    "7": "2º Reforço",

    "9": "Dose Única",

    "37": "Dose Adicional",

    "38": "Reforço",

    "57": "Dose Zero",

}





CAMPOS_TERMINOLOGIA = {

    "imunobiologico": "imunobiologicos",

    "grupo_atendimento": "grupos_atendimento",

    "condicao_maternal": "condicao_maternal",

    "fabricante_pni": "fabricantes_pni",

    "local_aplicacao": "local_aplicacao",

    "via_administracao": "via_administracao",

    "estrategia_vacinacao": "estrategia_vacinacao",

    "cid10": "brcid10",

}





NOMES_TERMINOLOGIA = {

    "imunobiologico": "BRImunobiologico",

    "grupo_atendimento": "BRGrupoAtendimento",

    "condicao_maternal": "BRCondicaoMaternal",

    "fabricante_pni": "BRFabricantePNI",

    "local_aplicacao": "BRLocalAplicacao",

    "via_administracao": "BRViaAdministracao",

    "estrategia_vacinacao": "BREstrategiaVacinacao",

    "cid10": "BRCID10",

}





CAMPOS_INICIAIS = {

    "patient_id": "",

    "practitioner_id": "",

    "imunobiologico": "",

    "data_vacinacao": "",

    "lote": "",

    "dose": "",

    "grupo_atendimento": "",

    "cnes": "",

    "condicao_maternal": "",

    "fabricante_pni": "",

    "local_aplicacao": "",

    "via_administracao": "",

    "estrategia_vacinacao": "",

    "cid10": "",

}





def validar_cpf(cpf):

    cpf = "".join(filter(str.isdigit, cpf))



    if len(cpf) != 11:

        return False



    if cpf == cpf[0] * 11:

        return False



    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))

    digito = (soma * 10) % 11



    if digito == 10:

        digito = 0



    if digito != int(cpf[9]):

        return False



    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))

    digito = (soma * 10) % 11



    if digito == 10:

        digito = 0



    return digito == int(cpf[10])





def validar_cnes(cnes):

    cnes = "".join(filter(str.isdigit, str(cnes)))

    return len(cnes) == 7





def ordenar_terminologia(dados):

    def chave_ordenacao(item):

        codigo = str(item[0])

        if codigo.isdigit():

            return (0, int(codigo), codigo)

        return (1, codigo.lower(), codigo)



    return dict(sorted(dados.items(), key=chave_ordenacao))





def carregar_terminologias_tela():

    resultado = {}



    for nome_tela, chave in CAMPOS_TERMINOLOGIA.items():

        resultado[nome_tela] = ordenar_terminologia(

            carregar_terminologia(chave)

        )



    return resultado





def carregar_opcoes_pacientes():
    opcoes = []
    for registro in listar_pacientes():
        fhir_id = str(registro["fhir_id"])
        nome = "Paciente"
        try:
            recurso = buscar_paciente(fhir_id)
            nomes = recurso.get("name", [])
            if nomes:
                nome = nomes[0].get("text") or nome
        except PacienteFHIRServiceError:
            pass
        opcoes.append({"id": fhir_id, "nome": nome})
    return opcoes


def carregar_opcoes_profissionais():
    opcoes = []
    for registro in listar_profissionais():
        fhir_id = str(registro["fhir_id"])
        nome = "Profissional"
        try:
            recurso = buscar_profissional(fhir_id)
            nomes = recurso.get("name", [])
            if nomes:
                nome = nomes[0].get("text") or nome
        except ProfissionalFHIRServiceError:
            pass
        opcoes.append({"id": fhir_id, "nome": nome})
    return opcoes


def renderizar(dados, mensagem=None, erro=None):

    try:

        terminologias = carregar_terminologias_tela()

    except TerminologiaIndisponivel as e:

        terminologias = {campo: {} for campo in CAMPOS_TERMINOLOGIA}

        if not erro:

            erro = str(e)



    return render_template(

        "cadastro.html",

        mensagem=mensagem,

        erro=erro,

        dados=dados,

        doses=DOSES,

        terminologias=terminologias,

        pacientes_cadastrados=carregar_opcoes_pacientes(),

        profissionais_cadastrados=carregar_opcoes_profissionais(),

    )





def validar_campos_terminologia(dados):

    descricoes = {}



    for campo, chave in CAMPOS_TERMINOLOGIA.items():

        codigo = dados.get(campo, "").strip()



        if not codigo:

            return None, f"Selecione um valor para {NOMES_TERMINOLOGIA[campo]}."



        resultado = validar_terminologia(chave, codigo)



        if not resultado["valido"]:

            return None, f"Código {NOMES_TERMINOLOGIA[campo]} inválido."



        descricoes[campo] = resultado["descricao"]



    return descricoes, None





@app.route("/validar-cpf/<cpf>")

def rota_validar_cpf(cpf):

    cpf_numerico = "".join(filter(str.isdigit, cpf))

    return jsonify({"valido": validar_cpf(cpf_numerico)})





@app.route("/validar-cnes/<cnes>")

def rota_validar_cnes(cnes):

    cnes_numerico = "".join(filter(str.isdigit, cnes))

    return jsonify({

        "valido": validar_cnes(cnes_numerico),

        "cnes": cnes_numerico,

    })





@app.route("/")

def home():

    return render_template("home.html")





@app.route("/profissionais")
def profissionais():
    lista = []
    generos = {"male": "Masculino", "female": "Feminino", "other": "Outro", "unknown": "Não informado"}
    for registro in listar_profissionais():
        item = {"fhir_id": str(registro["fhir_id"]), "nome": "-", "cpf": "-", "cns": "-", "genero": "-", "cbo": "-", "data_cadastro": registro["data_cadastro"], "disponivel": False}
        try:
            recurso = buscar_profissional(item["fhir_id"])
            nomes = recurso.get("name", [])
            if nomes: item["nome"] = nomes[0].get("text") or "-"
            for ident in recurso.get("identifier", []):
                valor = ident.get("value") or "-"
                for coding in ident.get("type", {}).get("coding", []):
                    if coding.get("code") == "TAX": item["cpf"] = valor
                    elif coding.get("code") == "HC": item["cns"] = valor
            item["genero"] = generos.get(recurso.get("gender"), recurso.get("gender") or "-")
            quals = recurso.get("qualification", [])
            if quals:
                codings = quals[0].get("code", {}).get("coding", [])
                if codings:
                    codigo_cbo = codings[0].get("code") or "-"
                    try:
                        descricao_cbo = carregar_terminologia("cbo").get(codigo_cbo)
                    except TerminologiaIndisponivel:
                        descricao_cbo = None
                    item["cbo"] = descricao_cbo or codigo_cbo
            item["disponivel"] = True
        except ProfissionalFHIRServiceError:
            pass
        lista.append(item)
    return render_template("profissionais.html", profissionais=lista)


@app.route("/profissional", methods=["GET", "POST"])

def cadastro_profissional():

    dados_profissional = {

        "nome": "",

        "cpf": "",

        "cns": "",

        "genero": "",

        "data_nascimento": "",

        "cbo": "",

        "conselho": "",

        "numero_registro": "",

    }



    try:

        cbos = ordenar_terminologia(

            carregar_terminologia("cbo")

        )

    except TerminologiaIndisponivel as e:

        cbos = {}

        return render_template(

            "profissional.html",

            dados=dados_profissional,

            cbos=cbos,

            mensagem=None,

            erro=str(e),

        )



    if request.method == "GET":

        return render_template(

            "profissional.html",

            dados=dados_profissional,

            cbos=cbos,

            mensagem=None,

            erro=None,

        )



    dados_profissional = {

        campo: request.form.get(campo, "").strip()

        for campo in dados_profissional

    }



    cpf_numerico = "".join(

        filter(str.isdigit, dados_profissional["cpf"])

    )

    cns_numerico = "".join(

        filter(str.isdigit, dados_profissional["cns"])

    )



    if len(dados_profissional["nome"]) < 3:

        return render_template(

            "profissional.html",

            dados=dados_profissional,

            cbos=cbos,

            mensagem=None,

            erro="Informe o nome completo do profissional.",

        )



    if not validar_cpf(cpf_numerico):

        return render_template(

            "profissional.html",

            dados=dados_profissional,

            cbos=cbos,

            mensagem=None,

            erro="CPF inválido.",

        )



    if cns_numerico and len(cns_numerico) != 15:

        return render_template(

            "profissional.html",

            dados=dados_profissional,

            cbos=cbos,

            mensagem=None,

            erro="O CNS deve possuir 15 dígitos.",

        )



    if dados_profissional["genero"] not in {

        "male", "female", "other", "unknown"

    }:

        return render_template(

            "profissional.html",

            dados=dados_profissional,

            cbos=cbos,

            mensagem=None,

            erro="Selecione um gênero válido.",

        )



    try:

        nascimento = datetime.strptime(

            dados_profissional["data_nascimento"],

            "%Y-%m-%d",

        ).date()

    except ValueError:

        return render_template(

            "profissional.html",

            dados=dados_profissional,

            cbos=cbos,

            mensagem=None,

            erro="Data de nascimento inválida.",

        )



    if nascimento > date.today():

        return render_template(

            "profissional.html",

            dados=dados_profissional,

            cbos=cbos,

            mensagem=None,

            erro="A data de nascimento não pode ser futura.",

        )



    resultado_cbo = validar_terminologia(

        "cbo",

        dados_profissional["cbo"],

    )



    if not resultado_cbo["valido"]:

        return render_template(

            "profissional.html",

            dados=dados_profissional,

            cbos=cbos,

            mensagem=None,

            erro="Selecione um CBO válido.",

        )



    if not dados_profissional["conselho"]:

        return render_template(

            "profissional.html",

            dados=dados_profissional,

            cbos=cbos,

            mensagem=None,

            erro="Selecione o conselho profissional.",

        )



    if not dados_profissional["numero_registro"]:

        return render_template(

            "profissional.html",

            dados=dados_profissional,

            cbos=cbos,

            mensagem=None,

            erro="Informe o número do registro profissional.",

        )



    try:

        resultado = cadastrar_profissional(

            nome=dados_profissional["nome"],

            cpf=cpf_numerico,

            cns=cns_numerico,

            genero=dados_profissional["genero"],

            data_nascimento=dados_profissional["data_nascimento"],

            cbo=dados_profissional["cbo"],

            conselho=dados_profissional["conselho"],

            numero_registro=dados_profissional["numero_registro"],

        )

        salvar_profissional(resultado["id"])

    except ProfissionalFHIRServiceError as e:

        return render_template(

            "profissional.html",

            dados=dados_profissional,

            cbos=cbos,

            mensagem=None,

            erro=str(e),

        )



    return render_template(

        "profissional.html",

        dados={

            "nome": "",

            "cpf": "",

            "cns": "",

            "genero": "",

            "data_nascimento": "",

            "cbo": "",

            "conselho": "",

            "numero_registro": "",

        },

        cbos=cbos,

        mensagem=(

            "Profissional cadastrado no HAPI FHIR com sucesso! "

            f"Referência: {resultado['reference']}"

        ),

        erro=None,

    )






@app.route("/api/paciente/<patient_id>")
def api_paciente(patient_id):
    try:
        return jsonify(buscar_paciente(patient_id))
    except PacienteFHIRServiceError as e:
        return jsonify({"erro": str(e)}), 404


@app.route("/api/profissional/<practitioner_id>")
def api_profissional(practitioner_id):
    try:
        return jsonify(buscar_profissional(practitioner_id))
    except ProfissionalFHIRServiceError as e:
        return jsonify({"erro": str(e)}), 404


@app.route("/api/registro-ria/<bundle_id>")
def api_registro_ria(bundle_id):
    try:
        return jsonify(buscar_registro_ria(bundle_id))
    except FHIRServiceError as e:
        return jsonify({"erro": str(e)}), 404


@app.route("/api/terminologias-consulta")
def api_terminologias_consulta():
    chaves = [
        "imunobiologicos", "grupos_atendimento", "condicao_maternal",
        "fabricantes_pni", "local_aplicacao", "via_administracao",
        "estrategia_vacinacao", "brcid10", "cbo",
    ]
    dados = {}
    for chave in chaves:
        try:
            dados[chave] = carregar_terminologia(chave)
        except TerminologiaIndisponivel:
            dados[chave] = {}
    dados["doses"] = DOSES
    return jsonify(dados)


@app.route("/pacientes")
def pacientes():
    registros = listar_pacientes()
    pacientes_lista = []

    generos = {
        "male": "Masculino",
        "female": "Feminino",
        "other": "Outro",
        "unknown": "Não informado",
    }

    for registro in registros:
        fhir_id = str(registro["fhir_id"])

        paciente = {
            "fhir_id": fhir_id,
            "referencia": f"Patient/{fhir_id}",
            "nome": "-",
            "cpf": "-",
            "cns": "-",
            "genero": "-",
            "data_nascimento": "-",
            "data_cadastro": registro["data_cadastro"],
            "disponivel": False,
        }

        try:
            recurso = buscar_paciente(fhir_id)

            nomes = recurso.get("name", [])
            if nomes:
                paciente["nome"] = nomes[0].get("text") or "-"

            for identificador in recurso.get("identifier", []):
                codigos_tipo = identificador.get("type", {}).get("coding", [])
                valor = identificador.get("value", "")

                for codigo_tipo in codigos_tipo:
                    codigo = codigo_tipo.get("code")

                    if codigo == "TAX":
                        paciente["cpf"] = valor
                    elif codigo == "HC":
                        paciente["cns"] = valor

            paciente["genero"] = generos.get(
                recurso.get("gender"),
                recurso.get("gender") or "-",
            )

            paciente["data_nascimento"] = recurso.get("birthDate") or "-"
            paciente["disponivel"] = True

        except PacienteFHIRServiceError:
            pass

        pacientes_lista.append(paciente)

    return render_template(
        "pacientes.html",
        pacientes=pacientes_lista,
    )


@app.route("/paciente", methods=["GET", "POST"])

def cadastro_paciente():

    dados_paciente = {

        "nome": "",

        "cpf": "",

        "cns": "",

        "genero": "",

        "data_nascimento": "",

    }



    if request.method == "GET":

        return render_template(

            "paciente.html",

            dados=dados_paciente,

            mensagem=None,

            erro=None,

        )



    dados_paciente = {

        campo: request.form.get(campo, "").strip()

        for campo in dados_paciente

    }



    cpf_numerico = "".join(filter(str.isdigit, dados_paciente["cpf"]))

    cns_numerico = "".join(filter(str.isdigit, dados_paciente["cns"]))



    if len(dados_paciente["nome"]) < 3:

        return render_template(

            "paciente.html",

            dados=dados_paciente,

            mensagem=None,

            erro="Informe o nome completo do paciente.",

        )



    if not validar_cpf(cpf_numerico):

        return render_template(

            "paciente.html",

            dados=dados_paciente,

            mensagem=None,

            erro="CPF inválido.",

        )



    if cns_numerico and len(cns_numerico) != 15:

        return render_template(

            "paciente.html",

            dados=dados_paciente,

            mensagem=None,

            erro="O CNS deve possuir 15 dígitos.",

        )



    if dados_paciente["genero"] not in {

        "male", "female", "other", "unknown"

    }:

        return render_template(

            "paciente.html",

            dados=dados_paciente,

            mensagem=None,

            erro="Selecione um gênero válido.",

        )



    try:

        nascimento = datetime.strptime(

            dados_paciente["data_nascimento"],

            "%Y-%m-%d",

        ).date()

    except ValueError:

        return render_template(

            "paciente.html",

            dados=dados_paciente,

            mensagem=None,

            erro="Data de nascimento inválida.",

        )



    if nascimento > date.today():

        return render_template(

            "paciente.html",

            dados=dados_paciente,

            mensagem=None,

            erro="A data de nascimento não pode ser futura.",

        )



    try:

        resultado = cadastrar_paciente(

            nome=dados_paciente["nome"],

            cpf=cpf_numerico,

            cns=cns_numerico,

            genero=dados_paciente["genero"],

            data_nascimento=dados_paciente["data_nascimento"],

        )

        salvar_paciente(resultado["id"])

    except PacienteFHIRServiceError as e:

        return render_template(

            "paciente.html",

            dados=dados_paciente,

            mensagem=None,

            erro=str(e),

        )



    return render_template(

        "paciente.html",

        dados={

            "nome": "",

            "cpf": "",

            "cns": "",

            "genero": "",

            "data_nascimento": "",

        },

        mensagem=(

            "Paciente cadastrado no HAPI FHIR com sucesso! "

            f"Referência: {resultado['reference']}"

        ),

        erro=None,

    )





@app.route("/registros-ria")
def registros_ria():
    lista = []
    for registro in listar_registros_ria():
        item = {
            "bundle_id": str(registro["bundle_fhir_id"]),
            "composition_id": str(registro["composition_fhir_id"]),
            "immunization_id": str(registro["immunization_fhir_id"]),
            "condition_id": str(registro["condition_fhir_id"] or "-"),
            "patient_id": str(registro["patient_fhir_id"]),
            "practitioner_id": str(registro["practitioner_fhir_id"]),
            "imunobiologico": "-", "data_vacinacao": "-", "lote": "-",
            "paciente_nome": "-", "profissional_nome": "-",
            "data_cadastro": registro["data_cadastro"], "disponivel": False,
        }
        try:
            bundle = buscar_registro_ria(item["bundle_id"])
            immunization = None
            for entry in bundle.get("entry", []):
                recurso = entry.get("resource", {})
                if recurso.get("resourceType") == "Immunization":
                    immunization = recurso
                    break
            if immunization:
                codings = immunization.get("vaccineCode", {}).get("coding", [])
                if codings:
                    codigo_imuno = codings[0].get("code") or "-"
                    try:
                        descricao_imuno = carregar_terminologia("imunobiologicos").get(codigo_imuno)
                    except TerminologiaIndisponivel:
                        descricao_imuno = None
                    item["imunobiologico"] = descricao_imuno or codigo_imuno
                item["data_vacinacao"] = immunization.get("occurrenceDateTime") or "-"
                item["lote"] = immunization.get("lotNumber") or "-"
            for entry in bundle.get("entry", []):
                recurso = entry.get("resource", {})
                if recurso.get("resourceType") == "Patient":
                    nomes = recurso.get("name", [])
                    if nomes: item["paciente_nome"] = nomes[0].get("text") or "-"
                elif recurso.get("resourceType") == "Practitioner":
                    nomes = recurso.get("name", [])
                    if nomes: item["profissional_nome"] = nomes[0].get("text") or "-"
            item["disponivel"] = True
        except FHIRServiceError:
            pass
        lista.append(item)
    return render_template("registros_ria.html", registros=lista)


@app.route("/vacinacao", methods=["GET", "POST"])

def vacinacao():

    dados = dict(CAMPOS_INICIAIS)



    if request.method == "GET":

        return renderizar(dados)



    dados = {

        campo: request.form.get(campo, "").strip()

        for campo in CAMPOS_INICIAIS

    }



    patient_id = "".join(filter(str.isdigit, dados["patient_id"]))

    practitioner_id = "".join(filter(str.isdigit, dados["practitioner_id"]))

    cnes_numerico = "".join(filter(str.isdigit, dados["cnes"]))



    if not patient_id:

        return renderizar(dados, erro="Informe o código do paciente.")



    if not practitioner_id:

        return renderizar(dados, erro="Informe o código do profissional de saúde.")



    if not validar_cnes(cnes_numerico):

        return renderizar(

            dados,

            erro="CNES inválido. Informe um código CNES com 7 dígitos.",

        )



    descricoes, erro_terminologia = validar_campos_terminologia(dados)

    if erro_terminologia:

        return renderizar(dados, erro=erro_terminologia)



    if dados["dose"] not in DOSES:

        return renderizar(dados, erro="Dose inválida.")



    if not dados["lote"]:

        return renderizar(dados, erro="Informe o lote.")



    if len(dados["lote"]) > 50:

        return renderizar(dados, erro="O lote informado é muito longo.")



    try:

        data_obj = datetime.strptime(

            dados["data_vacinacao"],

            "%Y-%m-%d",

        ).date()

    except ValueError:

        return renderizar(dados, erro="Data da vacinação inválida.")



    if data_obj > date.today():

        return renderizar(

            dados,

            erro="A data da vacinação não pode ser futura.",

        )



    # Valores fixos do fluxo atual da PoC:

    # - BRTipoDocumento = RIA (tratado no serviço FHIR)

    # - primarySource = true (tratado no serviço FHIR)

    # - reportOrigin não é solicitado neste fluxo

    # - país não é solicitado na tela



    argumentos = {

        "patient_id": patient_id,

        "practitioner_id": practitioner_id,

        "imunobiologico": dados["imunobiologico"],

        "descricao_imunobiologico": descricoes["imunobiologico"],

        "data_vacinacao": dados["data_vacinacao"],

        "lote": dados["lote"],

        "dose": dados["dose"],

        "grupo_atendimento": dados["grupo_atendimento"],

        "descricao_grupo": descricoes["grupo_atendimento"],

        "cnes": cnes_numerico,

        "condicao_maternal": dados["condicao_maternal"],

        "fabricante_pni": dados["fabricante_pni"],

        "local_aplicacao": dados["local_aplicacao"],

        "via_administracao": dados["via_administracao"],

        "estrategia_vacinacao": dados["estrategia_vacinacao"],
        "cid10": dados["cid10"],

    }



    try:

        resultado = cadastrar_vacinacao(**argumentos)

        salvar_registro_ria(
            resultado["bundle_id"],
            resultado["composition_id"],
            resultado["immunization_id"],
            patient_id,
            practitioner_id,
            resultado["condition_id"],
        )

    except FHIRServiceError as e:

        return renderizar(dados, erro=str(e))



    mensagem = (

        "Vacinação cadastrada com sucesso! "

        f"Immunization: {resultado['immunization_id']} | "

        f"Condition: {resultado['condition_id']} | "

        f"Composition: {resultado['composition_id']} | "

        f"Bundle: {resultado['bundle_id']}"

    )



    return renderizar(

        dict(CAMPOS_INICIAIS),

        mensagem=mensagem,

    )





if __name__ == "__main__":

    app.run(debug=True)
