import os
import sqlite3
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tcc.db")


def conectar():
    conexao = sqlite3.connect(DB_PATH)
    conexao.row_factory = sqlite3.Row
    return conexao


def inicializar_banco():
    with conectar() as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS pacientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fhir_id TEXT NOT NULL UNIQUE,
                data_cadastro TEXT NOT NULL
            )
        """)
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS profissionais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fhir_id TEXT NOT NULL UNIQUE,
                data_cadastro TEXT NOT NULL
            )
        """)
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS registros_ria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bundle_fhir_id TEXT NOT NULL UNIQUE,
                composition_fhir_id TEXT NOT NULL,
                immunization_fhir_id TEXT NOT NULL,
                condition_fhir_id TEXT,
                patient_fhir_id TEXT NOT NULL,
                practitioner_fhir_id TEXT NOT NULL,
                data_cadastro TEXT NOT NULL
            )
        """)
        colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(registros_ria)")}
        if "condition_fhir_id" not in colunas:
            conexao.execute("ALTER TABLE registros_ria ADD COLUMN condition_fhir_id TEXT")
        conexao.commit()


def salvar_paciente(fhir_id):
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO pacientes (fhir_id, data_cadastro)
            VALUES (?, ?)
            """,
            (
                str(fhir_id),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conexao.commit()


def listar_pacientes():
    with conectar() as conexao:
        return conexao.execute(
            """
            SELECT id, fhir_id, data_cadastro
            FROM pacientes
            ORDER BY id DESC
            """
        ).fetchall()


def salvar_profissional(fhir_id):
    with conectar() as conexao:
        conexao.execute(
            "INSERT INTO profissionais (fhir_id, data_cadastro) VALUES (?, ?)",
            (str(fhir_id), datetime.now().isoformat(timespec="seconds")),
        )
        conexao.commit()


def listar_profissionais():
    with conectar() as conexao:
        return conexao.execute(
            "SELECT id, fhir_id, data_cadastro FROM profissionais ORDER BY id DESC"
        ).fetchall()


def salvar_registro_ria(bundle_fhir_id, composition_fhir_id, immunization_fhir_id, patient_fhir_id, practitioner_fhir_id, condition_fhir_id=None):
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO registros_ria (
                bundle_fhir_id, composition_fhir_id, immunization_fhir_id,
                condition_fhir_id, patient_fhir_id, practitioner_fhir_id, data_cadastro
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(bundle_fhir_id), str(composition_fhir_id), str(immunization_fhir_id),
             str(condition_fhir_id) if condition_fhir_id else None,
             str(patient_fhir_id), str(practitioner_fhir_id),
             datetime.now().isoformat(timespec="seconds")),
        )
        conexao.commit()


def listar_registros_ria():
    with conectar() as conexao:
        return conexao.execute(
            """
            SELECT id, bundle_fhir_id, composition_fhir_id, immunization_fhir_id,
                   condition_fhir_id, patient_fhir_id, practitioner_fhir_id, data_cadastro
            FROM registros_ria ORDER BY id DESC
            """
        ).fetchall()
