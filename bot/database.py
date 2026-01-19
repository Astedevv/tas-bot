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
        else:
            cliente_id = "INTEGER PRIMARY KEY"
            transporte_id = "INTEGER PRIMARY KEY AUTOINCREMENT"
            autoinc = "INTEGER PRIMARY KEY AUTOINCREMENT"
            boolean_false = "0"

        # clientes
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

        # transportes
        # Note: use simple types; some defaults differ but are compatible
        self._execute("""
            CREATE TABLE IF NOT EXISTS transportes (
                id %s PRIMARY KEY,
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
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        """ % (autoinc, boolean_false, boolean_false, boolean_false), commit=True)

        # log_transportes
        self._execute("""
            CREATE TABLE IF NOT EXISTS log_transportes (
                id %s PRIMARY KEY,
                transporte_id INTEGER,
                origem TEXT,
                destino TEXT,
                valor_aproximado TEXT,
                prioridade TEXT,
                status_final TEXT,
                data_conclusao TIMESTAMP,
                message_id TEXT,
                FOREIGN KEY (transporte_id) REFERENCES transportes(id)
            )
        """ % (autoinc,), commit=True)

        # configuracoes
        self._execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT,
                tipo TEXT
            )
        """, commit=True)

        # auditorias
        self._execute("""
            CREATE TABLE IF NOT EXISTS auditorias (
                id %s PRIMARY KEY,
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
"""
Gerenciamento do banco de dados SQLite
"""
import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.ensure_db_exists()
    
    def ensure_db_exists(self):
        """Cria o banco se não existir"""
        if not os.path.exists("./data"):
            os.makedirs("./data")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Tabela: clientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY,
                discord_id TEXT UNIQUE NOT NULL,
                username TEXT,
                email TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_transportes INTEGER DEFAULT 0,
                status_verificado BOOLEAN DEFAULT 0
            )
        """)
        
        # Tabela: transportes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transportes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                confirmacao_deposito_origem BOOLEAN DEFAULT 0,
                confirmacao_transporte BOOLEAN DEFAULT 0,
                confirmacao_entrega BOOLEAN DEFAULT 0,
                ticket_channel_id TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_pagamento TIMESTAMP,
                data_conclusao TIMESTAMP,
                notas TEXT,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        """)
        
        # Tabela: log_transportes (histórico público)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_transportes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transporte_id INTEGER,
                origem TEXT,
                destino TEXT,
                valor_aproximado TEXT,
                prioridade TEXT,
                status_final TEXT,
                data_conclusao TIMESTAMP,
                message_id TEXT,
                FOREIGN KEY (transporte_id) REFERENCES transportes(id)
            )
        """)
        
        # Tabela: configurações
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT,
                tipo TEXT
            )
        """)
        
        # Tabela: auditorias
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auditorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id TEXT,
                acao TEXT,
                transporte_id INTEGER,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                detalhes TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Adiciona colunas que podem estar faltando
        self._add_missing_columns()
    
    def _add_missing_columns(self):
        """Adiciona colunas que podem estar faltando em tabelas existentes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Verifica e adiciona coluna staff_message_id se não existir
        try:
            cursor.execute("PRAGMA table_info(transportes)")
            colunas = [coluna[1] for coluna in cursor.fetchall()]
            
            if "staff_message_id" not in colunas:
                print("➕ Adicionando coluna staff_message_id...")
                cursor.execute("ALTER TABLE transportes ADD COLUMN staff_message_id TEXT")
                conn.commit()
                print("✅ Coluna staff_message_id adicionada")
        except Exception as e:
            print(f"⚠️  Erro ao adicionar coluna: {e}")
        
        conn.close()
    
    def get_connection(self):
        """Retorna uma conexão com o banco"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ===== CLIENTES =====
    def get_or_create_cliente(self, discord_id, username=None):
        """Pega ou cria um cliente"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM clientes WHERE discord_id = ?", (discord_id,))
        cliente = cursor.fetchone()
        
        if not cliente:
            cursor.execute(
                "INSERT INTO clientes (discord_id, username) VALUES (?, ?)",
                (discord_id, username)
            )
            conn.commit()
            cursor.execute("SELECT * FROM clientes WHERE discord_id = ?", (discord_id,))
            cliente = cursor.fetchone()
        
        conn.close()
        return cliente
    
    def get_cliente(self, discord_id):
        """Pega um cliente pelo discord_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes WHERE discord_id = ?", (discord_id,))
        cliente = cursor.fetchone()
        conn.close()
        return cliente
    
    # ===== TRANSPORTES =====
    def create_transporte(self, cliente_id, origem, valor_estimado, prioridade, taxa_final, ticket_channel_id):
        """Cria um novo transporte"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO transportes 
            (cliente_id, numero_ticket, status, origem, destino, valor_estimado, prioridade, taxa_final, ticket_channel_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cliente_id, None, "AGUARDANDO_PAGAMENTO", origem, "Caerleon", valor_estimado, prioridade, taxa_final, ticket_channel_id))
        
        conn.commit()
        transporte_id = cursor.lastrowid
        
        # Gera número do ticket
        numero_ticket = 1000 + transporte_id
        cursor.execute("UPDATE transportes SET numero_ticket = ? WHERE id = ?", (numero_ticket, transporte_id))
        conn.commit()
        
        cursor.execute("SELECT * FROM transportes WHERE id = ?", (transporte_id,))
        transporte = cursor.fetchone()
        conn.close()
        
        return transporte
    
    def get_transporte(self, transporte_id):
        """Pega um transporte pelo ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transportes WHERE id = ?", (transporte_id,))
        transporte = cursor.fetchone()
        conn.close()
        return transporte
    
    def get_transporte_by_numero(self, numero_ticket):
        """Pega um transporte pelo número"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transportes WHERE numero_ticket = ?", (numero_ticket,))
        transporte = cursor.fetchone()
        conn.close()
        return transporte
    
    def get_transportes_cliente(self, cliente_id):
        """Pega todos os transportes de um cliente"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transportes WHERE cliente_id = ? ORDER BY data_criacao DESC", (cliente_id,))
        transportes = cursor.fetchall()
        conn.close()
        return transportes
    
    def update_transporte_status(self, transporte_id, novo_status):
        """Atualiza o status de um transporte"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE transportes SET status = ? WHERE id = ?", (novo_status, transporte_id))
        conn.commit()
        conn.close()
    
    def update_transporte(self, transporte_id, **kwargs):
        """Atualiza múltiplos campos de um transporte"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        campos = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        valores = list(kwargs.values()) + [transporte_id]
        
        cursor.execute(f"UPDATE transportes SET {campos} WHERE id = ?", valores)
        conn.commit()
        conn.close()
    
    def get_transportes_by_status(self, status):
        """Pega todos os transportes com um determinado status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transportes WHERE status = ? ORDER BY data_criacao ASC", (status,))
        transportes = cursor.fetchall()
        conn.close()
        return transportes
    
    def get_transportes_por_status(self, status_list):
        """Pega transportes com múltiplos status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        placeholders = ",".join(["?" for _ in status_list])
        cursor.execute(f"SELECT * FROM transportes WHERE status IN ({placeholders}) ORDER BY prioridade DESC, data_criacao ASC", status_list)
        transportes = cursor.fetchall()
        conn.close()
        return transportes
    
    def get_all_transportes(self):
        """Pega todos os transportes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transportes ORDER BY data_criacao DESC")
        transportes = cursor.fetchall()
        conn.close()
        return transportes
    
    def delete_transporte(self, transporte_id):
        """Deleta um transporte"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transportes WHERE id = ?", (transporte_id,))
        conn.commit()
        conn.close()
    
    # ===== LOG TRANSPORTES =====
    def create_log_transporte(self, transporte_id, origem, destino, valor_aproximado, prioridade, status_final, message_id=None):
        """Cria um log público de transporte"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO log_transportes 
            (transporte_id, origem, destino, valor_aproximado, prioridade, status_final, data_conclusao, message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (transporte_id, origem, destino, valor_aproximado, prioridade, status_final, datetime.now().isoformat(), message_id))
        
        conn.commit()
        log_id = cursor.lastrowid
        conn.close()
        
        return log_id
    
    def get_logs_transportes(self, limite=50):
        """Pega os últimos logs de transportes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM log_transportes ORDER BY data_conclusao DESC LIMIT ?", (limite,))
        logs = cursor.fetchall()
        conn.close()
        return logs
    
    # ===== AUDITORIAS =====
    def create_auditoria(self, staff_id, acao, transporte_id, detalhes=None):
        """Registra uma auditoria"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO auditorias (staff_id, acao, transporte_id, detalhes)
            VALUES (?, ?, ?, ?)
        """, (staff_id, acao, transporte_id, detalhes))
        
        conn.commit()
        conn.close()
    
    # ===== CONFIGURAÇÕES =====
    def get_config(self, chave):
        """Pega uma configuração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def set_config(self, chave, valor, tipo="string"):
        """Define uma configuração"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM configuracoes WHERE chave = ?", (chave,))
        existe = cursor.fetchone()
        
        if existe:
            cursor.execute("UPDATE configuracoes SET valor = ?, tipo = ? WHERE chave = ?", (valor, tipo, chave))
        else:
            cursor.execute("INSERT INTO configuracoes (chave, valor, tipo) VALUES (?, ?, ?)", (chave, valor, tipo))
        
        conn.commit()
        conn.close()

# Instância global
db = Database()
