# CRUD Interoperável para Registro de Imunobiológicos Administrados (RIA) para o SUS

## 1. Apresentação

Este repositório contém o protótipo desenvolvido como parte do **Trabalho de Conclusão de Curso (TCC)** do curso de **Tecnologia em Sistemas para Internet**, do **Instituto Federal Sul-rio-grandense (IFSul) — Câmpus Charqueadas**.

O projeto demonstra, de forma prática, como uma aplicação web pode cadastrar e consultar informações relacionadas à vacinação e representar esses dados por meio do padrão **HL7 FHIR R4**, considerando a estrutura do **Registro de Imunobiológico Administrado (RIA)** utilizada no contexto da **Rede Nacional de Dados em Saúde (RNDS)**.

**Autor:** Eduardo Steigleder  
**Natureza:** Projeto acadêmico / prova de conceito

> **Importante:** este é um ambiente de demonstração e estudo. A aplicação utiliza o servidor público de testes HAPI FHIR R4; **não representa uma integração homologada com a RNDS de produção** e não deve ser utilizada com dados pessoais reais ou sensíveis.

## 2. Objetivo

O objetivo é desenvolver uma interface web que permita:

- Cadastrar e consultar pacientes;
- Cadastrar e consultar profissionais de saúde;
- Registrar a administração de imunobiológicos;
- Validar campos com base em terminologias de saúde;
- Construir recursos no formato JSON compatível com a estrutura HL7 FHIR;
- Enviar e consultar recursos no servidor FHIR de testes;
- Consultar os registros de vacinação produzidos pela aplicação.

A proposta é aproximar o uso cotidiano de formulários web da representação padronizada de informações em saúde, demonstrando como diferentes sistemas podem trocar dados estruturados.

## 3. Tecnologias utilizadas

| Tecnologia | Utilização |
| --- | --- |
| **Python** | Linguagem principal do back-end |
| **Flask** | Aplicação web, rotas e renderização de páginas |
| **HTML, CSS e JavaScript** | Interface de usuário e interação com os formulários |
| **SQLite** | Armazenamento local de identificadores e referências dos cadastros |
| **Requests (Python)** | Comunicação HTTP com o servidor FHIR e fontes de terminologia |
| **HL7 FHIR R4 / JSON** | Estruturação e intercâmbio dos recursos de saúde |
| **HAPI FHIR R4** | Servidor público utilizado para os testes de envio e consulta |

O sistema combina **front-end e back-end em uma aplicação Flask**, com arquivos HTML na pasta `templates/` e regras de negócio separadas na pasta `services/`.

## 4. Organização do projeto

```text
tcc-ria/
├── app.py
├── requirements.txt
├── .gitignore
├── data/
│   ├── brcid10.json
│   ├── cbo.json
│   ├── condicao_maternal.json
│   ├── estrategia_vacinacao.json
│   ├── fabricantes_pni.json
│   ├── grupos_atendimento.json
│   ├── imunobiologicos.json
│   ├── local_aplicacao.json
│   ├── paises.json
│   ├── registro_origem.json
│   └── via_administracao.json
├── database/
│   └── database.py
├── services/
│   ├── fhir_service.py
│   ├── paciente_service.py
│   ├── profissional_service.py
│   └── terminologias.py
├── templates/
│   ├── home.html
│   ├── cadastro.html
│   ├── paciente.html
│   ├── pacientes.html
│   ├── profissional.html
│   ├── profissionais.html
│   └── registros_ria.html
└── logs/
    └── ria/
```

**Observação:** arquivos locais de banco de dados (`*.db`), logs de execução, ambientes virtuais e arquivos temporários Python são ignorados pelo Git e não precisam ser enviados ao repositório.

## 5. Páginas do sistema (front-end)

O front-end está dividido em **sete arquivos HTML**, localizados em `templates/`.

| Arquivo | Finalidade |
| --- | --- |
| `home.html` | Página inicial, com acesso às funcionalidades do sistema. |
| `pacientes.html` | Listagem e consulta dos pacientes cadastrados. |
| `paciente.html` | Formulário de cadastro de paciente, associado ao recurso FHIR `Patient`. |
| `profissionais.html` | Listagem e consulta dos profissionais de saúde. |
| `profissional.html` | Formulário de cadastro de profissional, associado ao recurso FHIR `Practitioner`. |
| `cadastro.html` | Formulário de registro de vacinação, com campos do RIA e seleção de paciente e profissional. |
| `registros_ria.html` | Consulta e listagem dos registros RIA gerados. |

Essas páginas são renderizadas pelo Flask e permitem interagir com o sistema por meio do navegador, sem a necessidade de escrever requisições FHIR manualmente.

## 6. Arquivos Python e responsabilidades

### `app.py` — aplicação principal

É o ponto de entrada do sistema. Inicializa o Flask e o banco local, define as rotas das páginas, recebe os dados dos formulários e chama os serviços responsáveis pelo processamento.

Entre as rotas implementadas estão:

| Rota | Função |
| --- | --- |
| `/` | Página inicial |
| `/pacientes` | Listagem de pacientes |
| `/paciente` | Cadastro de paciente |
| `/profissionais` | Listagem de profissionais |
| `/profissional` | Cadastro de profissional |
| `/vacinacao` | Formulário e envio do registro de vacinação |
| `/registros-ria` | Listagem dos registros RIA |
| `/api/paciente/<patient_id>` | Consulta de paciente pelo identificador FHIR |
| `/api/profissional/<practitioner_id>` | Consulta de profissional pelo identificador FHIR |
| `/api/registro-ria/<bundle_id>` | Consulta de um `Bundle` pelo identificador |
| `/api/terminologias-consulta` | Consulta de terminologias utilizadas pela interface |

O arquivo também contém rotinas de validação de dados, incluindo CPF, CNES e campos relacionados às terminologias.

### `services/paciente_service.py` — pacientes

Contém a lógica para montar, enviar e consultar recursos FHIR do tipo **`Patient`**. O cadastro reúne as informações recebidas do formulário e as transforma em uma representação estruturada.

### `services/profissional_service.py` — profissionais

Contém a lógica de montagem, envio e consulta dos recursos **`Practitioner`**, utilizados para representar o profissional relacionado ao atendimento.

### `services/fhir_service.py` — registro de vacinação

É o serviço responsável pelo fluxo principal do RIA. Ele consulta o paciente e o profissional, constrói os recursos de vacinação, envia os JSONs ao HAPI FHIR e registra os identificadores retornados.

No fluxo implementado, são utilizados os recursos **`Condition`**, **`Immunization`**, **`Composition`** e **`Bundle`**, além das referências a `Patient` e `Practitioner`.

### `services/terminologias.py` — terminologias

Centraliza o carregamento e a validação de códigos usados nos formulários. O módulo consulta fontes de terminologia FHIR, trabalha com recursos como **`CodeSystem`** e **`ValueSet`** e utiliza arquivos JSON locais para apoiar o preenchimento dos campos.

### `database/database.py` — persistência local

Gerencia o banco **SQLite**, incluindo a criação das tabelas e o armazenamento e a listagem de identificadores de pacientes, profissionais e registros RIA. O banco local auxilia a navegação e a recuperação dos registros, enquanto os recursos FHIR são enviados ao servidor de testes.

## 7. Como funciona o registro de vacinação

O fluxo principal pode ser resumido assim:

1. O usuário cadastra ou seleciona um **paciente** (`Patient`).
2. Cadastra ou seleciona um **profissional de saúde** (`Practitioner`).
3. Abre o formulário de vacinação e informa os dados solicitados, como imunobiológico, data, dose, lote, fabricante e demais códigos.
4. A aplicação valida os campos e consulta os recursos necessários no servidor FHIR.
5. O serviço cria um **`Condition`**, associado ao código CID-10 informado.
6. Cria um **`Immunization`**, que representa a administração do imunobiológico e faz referência ao paciente, ao profissional e à condição.
7. Cria uma **`Composition`**, que organiza o conteúdo do registro.
8. Monta um **`Bundle` do tipo `document`**, reunindo `Composition`, `Immunization`, `Condition`, `Patient` e `Practitioner`.
9. Envia os recursos ao servidor **HAPI FHIR R4** e utiliza os identificadores retornados para consultas posteriores.

**Fluxo simplificado:**

```text
Navegador (formulário HTML)
          ↓
       Flask / app.py
          ↓
 Validações e terminologias
          ↓
    Serviços Python
          ↓
 Recursos JSON HL7 FHIR R4
          ↓
  Servidor HAPI FHIR de testes
          ↓
 Identificadores e consultas
```

### Recursos FHIR utilizados

| Recurso | Papel no projeto |
| --- | --- |
| `Patient` | Representa o paciente. |
| `Practitioner` | Representa o profissional de saúde. |
| `Condition` | Registra uma condição codificada, associada ao contexto da vacinação. |
| `Immunization` | Representa a aplicação do imunobiológico. |
| `Composition` | Organiza o documento clínico e referencia o registro de vacinação. |
| `Bundle` | Agrupa os recursos em um documento FHIR. |

A utilização desses recursos demonstra a organização e o relacionamento de dados de saúde em uma estrutura interoperável.

## 8. Terminologias e arquivos da pasta `data/`

A pasta `data/` contém arquivos JSON utilizados para disponibilizar opções e validar códigos dos formulários. Entre os conjuntos contemplados estão:

- **Imunobiológicos:** códigos dos produtos administrados;
- **Grupos de atendimento:** identificação do grupo relacionado ao atendimento;
- **Condição maternal:** informações codificadas referentes à condição maternal;
- **Fabricantes PNI:** fabricantes dos imunobiológicos;
- **Local de aplicação e via de administração:** informações sobre a aplicação;
- **Estratégia de vacinação:** estratégia relacionada ao registro;
- **CID-10:** classificação de condições;
- **CBO:** ocupações profissionais;
- **Países e registro de origem:** códigos auxiliares utilizados no cadastro.

O módulo `terminologias.py` contém a lógica de consulta a fontes externas e de utilização dos arquivos locais. A disponibilidade das fontes pode variar, pois elas são mantidas por serviços externos ao projeto.

## 9. Como executar o projeto

### Pré-requisitos

- Python 3 instalado;
- `pip` disponível;
- Acesso à internet para comunicação com o servidor HAPI FHIR e, quando necessário, com fontes de terminologia;
- Git (opcional, para clonar o repositório).

### Passo 1 — obter o código

```bash
git clone https://github.com/EduardoSteigleder/tcc-ria-fhir.git
cd tcc-ria-fhir
```

Também é possível baixar o ZIP do repositório pelo GitHub e abrir a pasta no VS Code.

### Passo 2 — criar um ambiente virtual

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Passo 3 — instalar as dependências

O código importa diretamente as bibliotecas externas **Flask** e **Requests**. Para instalar o necessário:

```bash
python -m pip install Flask requests
```

> **Atenção:** na versão analisada do projeto, o arquivo `requirements.txt` está vazio. Portanto, **não basta executar `pip install -r requirements.txt`** até que esse arquivo seja preenchido. Uma sugestão de conteúdo é:
>
> ```text
> Flask
> requests
> ```

### Passo 4 — configurar o servidor FHIR (opcional)

Por padrão, a aplicação utiliza:

```text
https://hapi.fhir.org/baseR4
```

É possível alterar o endereço definindo a variável de ambiente `FHIR_BASE_URL` antes da execução.

**PowerShell:**

```powershell
$env:FHIR_BASE_URL = "https://hapi.fhir.org/baseR4"
```

**Linux / macOS:**

```bash
export FHIR_BASE_URL="https://hapi.fhir.org/baseR4"
```

### Passo 5 — iniciar a aplicação

Na pasta principal do projeto, execute:

```bash
python app.py
```

O Flask inicia um servidor de desenvolvimento. Na configuração padrão, a aplicação fica disponível em:

```text
http://127.0.0.1:5000
```

Abra esse endereço no navegador para acessar a página inicial.

### Passo 6 — testar o fluxo

1. Acesse a página de **profissionais** e cadastre um profissional de teste.
2. Acesse a página de **pacientes** e cadastre um paciente fictício.
3. Abra o formulário de **vacinação**.
4. Selecione os cadastros e preencha os campos exigidos.
5. Envie o registro e consulte os resultados em **registros RIA**.

O funcionamento das operações remotas depende da disponibilidade do servidor FHIR e da validade dos dados e códigos utilizados.

## 10. Registros locais e logs

A aplicação mantém informações auxiliares em dois locais:

- **`database/tcc.db`**: banco SQLite criado e utilizado localmente;
- **`logs/ria/`**: arquivos JSON de registros gerados durante os testes.

Esses arquivos não devem ser publicados com informações pessoais reais. O `.gitignore` do projeto exclui o banco local e a pasta de logs do versionamento.

## 11. Limitações e escopo

- O projeto é uma **prova de conceito acadêmica**, não um sistema de prontuário pronto para produção.
- A comunicação ocorre com o **HAPI FHIR R4 público de testes**, e não com o ambiente produtivo da RNDS.
- A construção dos recursos segue perfis e terminologias estudados no contexto do RIA, mas o envio bem-sucedido ao HAPI **não comprova, por si só, homologação ou conformidade integral com todas as validações da RNDS**.
- O servidor de testes e as fontes externas de terminologia podem estar indisponíveis ou sofrer alterações.
- A execução com `debug=True` em `app.py` é adequada apenas para desenvolvimento local.
- Recomenda-se utilizar **somente dados fictícios** em todas as demonstrações.

## 12. Contexto acadêmico

Este projeto foi desenvolvido para apoiar a investigação sobre **interoperabilidade de dados de vacinação**, com foco na estruturação de registros por meio do padrão **HL7 FHIR R4** e na aplicação prática dos conceitos estudados no TCC.

A interface web, os serviços Python, os arquivos de terminologia e os recursos FHIR permitem acompanhar o percurso das informações desde o preenchimento de um formulário até sua representação em JSON e seu armazenamento em um servidor de testes.

---

**Desenvolvimento:** Eduardo Steigleder  
**Curso:** Tecnologia em Sistemas para Internet  
**Instituição:** Instituto Federal Sul-rio-grandense (IFSul) — Câmpus Charqueadas  
**Finalidade:** Trabalho de Conclusão de Curso (TCC)
