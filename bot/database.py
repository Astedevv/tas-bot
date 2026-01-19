"""
Gerenciamento do banco de dados (compatível com SQLite e PostgreSQL)

Comportamento:
- Usa `DATABASE_URL` do ambiente (Postgres) se disponível.
- Caso contrário, usa um arquivo SQLite em `DATABASE_PATH`.

Esta implementação adapta placeholders automaticamente: se estiver usando psycopg2, substitui
os `?` por `%s` antes de executar queries.
"""
import os
import sqlite3
from datetime import datetime
from config import DATABASE_PATH, DATABASE_URL

USE_POSTGRES = False
psycopg2 = None

if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    try:
        import psycopg2
        import psycopg2.extras
        psycopg2 = psycopg2
        USE_POSTGRES = True
    except Exception:
        USE_POSTGRES = False


class Database:
    def __init__(self):
        self.sqlite_path = DATABASE_PATH
        self.database_url = DATABASE_URL
        self.use_postgres = USE_POSTGRES
        self.ensure_db_exists()

    # ---- Connection helpers ----
    def get_connection(self):
        if self.use_postgres:
            return psycopg2.connect(self.database_url)
        else:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            return conn

    def _execute(self, sql, params=None, fetchone=False, fetchall=False, commit=False):
        # Adapt placeholder style for psycopg2: replace ? -> %s
        if params is None:
            params = ()

        if self.use_postgres:
            sql_exec = sql.replace("?", "%s")
        else:
            sql_exec = sql

        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(sql_exec, params)
            result = None
            if commit:
                conn.commit()
            if fetchone:
                result = cur.fetchone()
            if fetchall:
                result = cur.fetchall()
            cur.close()
            return result
        finally:
            conn.close()

    # ---- Schema / migration ----
    def ensure_db_exists(self):
        # Ensure data folder exists for sqlite
        if not os.path.exists("./data"):
            os.makedirs("./data")

        # Create tables using SQL compatible with Postgres and SQLite.
        # Adjust types where necessary (SERIAL vs AUTOINCREMENT) by using dialect-specific SQL.
        if self.use_postgres:
            cliente_id = "SERIAL PRIMARY KEY"
            transporte_id = "SERIAL PRIMARY KEY"
            autoinc = "SERIAL PRIMARY KEY"
            boolean_false = "FALSE"
            
            # Disable FK constraints temporarily to avoid creation order issues
            conn = self.get_connection()
            conn.set_session(autocommit=True)
            try:
                conn.cursor().execute("ALTER SESSION SET CONSTRAINTS = DEFERRED")
            except:
                pass  # Ignore if not supported
            conn.close()
        else:
            cliente_id = "INTEGER PRIMARY KEY"
            transporte_id = "INTEGER PRIMARY KEY AUTOINCREMENT"
            autoinc = "INTEGER PRIMARY KEY AUTOINCREMENT"
            boolean_false = "0"

        # clientes - CREATE FIRST (no dependencies)
        self._execute(f"""
            CREATE TABLE IF NOT EXISTS clientes (
                id {cliente_id},
                discord_id TEXT UNIQUE NOT NULL,
                username TEXT,
                email TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_transportes INTEGER DEFAULT 0,
                status_verificado BOOLEAN DEFAULT {boolean_false}
            )
        """, commit=True)

        # transportes - CREATE SECOND (depends on clientes)
        # Note: use simple types; some defaults differ but are compatible
        self._execute("""
            CREATE TABLE IF NOT EXISTS transportes (
                id %s,
                numero_ticket INTEGER UNIQUE,
                cliente_id INTEGER NOT NULL,
                status TEXT,
                origem TEXT,
                destino TEXT DEFAULT 'Caerleon',
                valor_estimado INTEGER,
                prioridade TEXT,
                taxa_final REAL,
                comprovante_pagamento TEXT,
                print_items_origem TEXT,
                print_items_destino TEXT,
                confirmacao_deposito_origem BOOLEAN DEFAULT %s,
                confirmacao_transporte BOOLEAN DEFAULT %s,
                confirmacao_entrega BOOLEAN DEFAULT %s,
                ticket_channel_id TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_pagamento TIMESTAMP,
                data_conclusao TIMESTAMP,
                notas TEXT,
                staff_message_id TEXT,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
            )
        """ % (autoinc, boolean_false, boolean_false, boolean_false), commit=True)

        # log_transportes - CREATE THIRD (depends on transportes)
        self._execute("""
            CREATE TABLE IF NOT EXISTS log_transportes (
                id %s,
                transporte_id INTEGER NOT NULL,
                origem TEXT,
                destino TEXT,
                valor_aproximado TEXT,
                prioridade TEXT,
                status_final TEXT,
                data_conclusao TIMESTAMP,
                message_id TEXT,
                FOREIGN KEY (transporte_id) REFERENCES transportes(id) ON DELETE CASCADE
            )
        """ % (autoinc,), commit=True)

        # configuracoes - NO DEPENDENCIES
        self._execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT,
                tipo TEXT
            )
        """, commit=True)

        # auditorias - NO DEPENDENCIES (but references transporte_id for data integrity)
        self._execute("""
            CREATE TABLE IF NOT EXISTS auditorias (
                id %s,
                staff_id TEXT,
                acao TEXT,
                transporte_id INTEGER,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                detalhes TEXT
            )
        """ % (autoinc,), commit=True)

    # ---- Compatibility helpers ----
    def _column_exists(self, table, column):
        if self.use_postgres:
            sql = "SELECT column_name FROM information_schema.columns WHERE table_name=%s AND column_name=%s"
            return bool(self._execute(sql, (table, column), fetchall=True))
        else:
            sql = "PRAGMA table_info(%s)" % table
            cols = self._execute(sql, fetchall=True)
            if not cols:
                return False
            colnames = [c[1] for c in cols]
            return column in colnames

    def add_column_if_missing(self, table, column_sql):
        # column_sql example: 'staff_message_id TEXT'
        column_name = column_sql.split()[0]
        if not self._column_exists(table, column_name):
            sql = f"ALTER TABLE {table} ADD COLUMN {column_sql}"
            self._execute(sql, commit=True)

    # ---- Public API (methods adapted from previous SQLite implementation) ----
    def get_or_create_cliente(self, discord_id, username=None):
        cliente = self._execute("SELECT * FROM clientes WHERE discord_id = ?", (discord_id,), fetchone=True)
        if not cliente:
            self._execute(
                "INSERT INTO clientes (discord_id, username) VALUES (?, ?)",
                (discord_id, username), commit=True
            )
            cliente = self._execute("SELECT * FROM clientes WHERE discord_id = ?", (discord_id,), fetchone=True)
        return cliente

    def get_cliente(self, discord_id):
        return self._execute("SELECT * FROM clientes WHERE discord_id = ?", (discord_id,), fetchone=True)

    def create_transporte(self, cliente_id, origem, valor_estimado, prioridade, taxa_final, ticket_channel_id):
        self._execute(
            """
            INSERT INTO transportes 
            (cliente_id, numero_ticket, status, origem, destino, valor_estimado, prioridade, taxa_final, ticket_channel_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (cliente_id, None, "AGUARDANDO_PAGAMENTO", origem, "Caerleon", valor_estimado, prioridade, taxa_final, ticket_channel_id),
            commit=True
        )

        # Get last inserted id
        if self.use_postgres:
            # Fetch the last created transporte by highest id
            transporte = self._execute("SELECT * FROM transportes ORDER BY id DESC LIMIT 1", fetchone=True)
        else:
            transporte = self._execute("SELECT * FROM transportes ORDER BY id DESC LIMIT 1", fetchone=True)

        transporte_id = transporte[0]
        numero_ticket = 1000 + transporte_id
        self._execute("UPDATE transportes SET numero_ticket = ? WHERE id = ?", (numero_ticket, transporte_id), commit=True)
        transporte = self._execute("SELECT * FROM transportes WHERE id = ?", (transporte_id,), fetchone=True)
        return transporte

    def get_transporte(self, transporte_id):
        return self._execute("SELECT * FROM transportes WHERE id = ?", (transporte_id,), fetchone=True)

    def get_transporte_by_numero(self, numero_ticket):
        return self._execute("SELECT * FROM transportes WHERE numero_ticket = ?", (numero_ticket,), fetchone=True)

    def get_transportes_cliente(self, cliente_id):
        return self._execute("SELECT * FROM transportes WHERE cliente_id = ? ORDER BY data_criacao DESC", (cliente_id,), fetchall=True)

    def update_transporte_status(self, transporte_id, novo_status):
        self._execute("UPDATE transportes SET status = ? WHERE id = ?", (novo_status, transporte_id), commit=True)

    def update_transporte(self, transporte_id, **kwargs):
        campos = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        valores = list(kwargs.values()) + [transporte_id]
        self._execute(f"UPDATE transportes SET {campos} WHERE id = ?", tuple(valores), commit=True)

    def get_transportes_by_status(self, status):
        return self._execute("SELECT * FROM transportes WHERE status = ? ORDER BY data_criacao ASC", (status,), fetchall=True)

    def get_transportes_por_status(self, status_list):
        placeholders = ",".join(["?" for _ in status_list])
        sql = f"SELECT * FROM transportes WHERE status IN ({placeholders}) ORDER BY prioridade DESC, data_criacao ASC"
        return self._execute(sql, tuple(status_list), fetchall=True)

    def get_all_transportes(self):
        return self._execute("SELECT * FROM transportes ORDER BY data_criacao DESC", fetchall=True)

    def delete_transporte(self, transporte_id):
        self._execute("DELETE FROM transportes WHERE id = ?", (transporte_id,), commit=True)

    def create_log_transporte(self, transporte_id, origem, destino, valor_aproximado, prioridade, status_final, message_id=None):
        self._execute(
            """
            INSERT INTO log_transportes 
            (transporte_id, origem, destino, valor_aproximado, prioridade, status_final, data_conclusao, message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (transporte_id, origem, destino, valor_aproximado, prioridade, status_final, datetime.now().isoformat(), message_id),
            commit=True
        )
        # return last id
        last = self._execute("SELECT id FROM log_transportes ORDER BY id DESC LIMIT 1", fetchone=True)
        return last[0] if last else None

    def get_logs_transportes(self, limite=50):
        return self._execute("SELECT * FROM log_transportes ORDER BY data_conclusao DESC LIMIT ?", (limite,), fetchall=True)

    def create_auditoria(self, staff_id, acao, transporte_id, detalhes=None):
        self._execute(
            "INSERT INTO auditorias (staff_id, acao, transporte_id, detalhes) VALUES (?, ?, ?, ?)",
            (staff_id, acao, transporte_id, detalhes), commit=True
        )

    def get_config(self, chave):
        res = self._execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,), fetchone=True)
        return res[0] if res else None

    def set_config(self, chave, valor, tipo="string"):
        existe = self._execute("SELECT * FROM configuracoes WHERE chave = ?", (chave,), fetchone=True)
        if existe:
            self._execute("UPDATE configuracoes SET valor = ?, tipo = ? WHERE chave = ?", (valor, tipo, chave), commit=True)
        else:
            self._execute("INSERT INTO configuracoes (chave, valor, tipo) VALUES (?, ?, ?)", (chave, valor, tipo), commit=True)


# Instância global
db = Database()

