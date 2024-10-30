import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql

from core_tools.data.SQL.SQL_utility import (
    sql_name_formatter,
    sql_value_formatter,
    name_value_formatter,
)


class sqlite_helper:
    @staticmethod
    def quote_ident(identifier):
        for character in identifier:
            if character == "\0" or character > "\x7f":
                raise ValueError(
                    "SQLite identifier cannot contain NUL or non-ASCII character."
                )

        return '"' + identifier.replace('"', '""') + '"'

    @classmethod
    def ident_as_string(cls, ident: sql.Identifier) -> str:
        return ".".join(cls.quote_ident(s) for s in ident._wrapped)

    @classmethod
    def literal_as_string(cls, literal: sql.Literal) -> str:
        val = literal._wrapped
        if isinstance(val, int | float):
            return str(val)
        if isinstance(val, str):
            return cls.quote_ident(val)

        return literal.as_string(None)

    @classmethod
    def composed_as_string(cls, composed: sql.Composed) -> str:
        rv = []
        for item in composed._wrapped:
            match item:
                case sql.Composed():
                    rv.append(cls.composed_as_string(item))
                case sql.Identifier():
                    rv.append(cls.ident_as_string(item))
                case sql.Literal():
                    rv.append(cls.literal_as_string(item))
                case _:
                    rv.append(item.as_string(None))
        return "".join(rv)

    @classmethod
    def is_active(cls, cursor):
        return isinstance(cursor, sqlite3.Cursor)

    @classmethod
    def convert_to_string(cls, statement):
        if isinstance(statement, sql.Composed):
            return cls.composed_as_string(statement)
        return statement

    @classmethod
    def convert_placeholders(cls, placeholders):
        # return placeholders
        return [cls.convert_one_placeholder(p) for p in placeholders]

    @classmethod
    def convert_one_placeholder(cls, placeholder):
        if isinstance(placeholder, psycopg2.Binary):
            return bytes(placeholder.adapted)
        return placeholder

    @classmethod
    def split_multiple_statements(cls, statement, placeholders):
        s = statement.replace("%s", "?")
        ls: list[str] = [ss for ss in s.split(";") if ss.strip()]
        if len(ls) == 0:
            yield "", cls.convert_placeholders(placeholders)
        elif len(ls) == 1:
            yield ls[0], cls.convert_placeholders(placeholders)
        else:
            placeholders = placeholders[:]
            for s in ls:
                n = s.count("?")
                yield s, cls.convert_placeholders(placeholders[:n])
                placeholders = placeholders[n:]


def execute_statement(conn, statement, placeholders=[], close_on_error=True):
    try:
        cursor = conn.cursor()
        if sqlite_helper.is_active(cursor):
            _orig_statement = statement
            statement = sqlite_helper.convert_to_string(statement)
            for statement, placeholders in sqlite_helper.split_multiple_statements(
                statement, placeholders
            ):
                cursor.execute(statement, placeholders)
        else:
            cursor.execute(statement, placeholders)
            cursor.close()
        return ((),)
    except:
        if not close_on_error:
            return
        print(f"{statement}")
        # After exception the connection cannot be used anymore.
        # A new connection will automatically be opened for the next command.
        conn.close()
        raise


def execute_query(conn, query, dict_cursor=False, placeholders=[]):
    try:
        restore_orig_row_factory = False

        if dict_cursor is False:
            cursor = conn.cursor()
        else:
            if not isinstance(conn, sqlite3.Connection):
                cursor = conn.cursor(cursor_factory=RealDictCursor)
            else:
                if dict_cursor is not False:
                    def dict_factory(cursor, row):
                        d = {}
                        for idx, col in enumerate(cursor.description):
                            d[col[0]] = row[idx]
                        return d

                    restore_orig_row_factory = True
                    orig_row_factory = conn.row_factory
                    conn.row_factory = dict_factory

                cursor = conn.cursor()

        if sqlite_helper.is_active(cursor):
            query = sqlite_helper.convert_to_string(query)

        try:
            cursor.execute(query, placeholders)
            return_values = cursor.fetchall()
        finally:
            if restore_orig_row_factory:
                conn.row_factory = orig_row_factory

        cursor.close()
        return return_values
    except:
        # After exception the connection cannot be used anymore.
        # A new connection will automatically be opened for the next command.
        conn.close()
        raise


def select_elements_in_table(
    conn, table_name, var_names, where=None, order_by=None, limit=None, dict_cursor=True
):
    """
    execute a query on a table

    Args:
        conn (psycopg2.connect) : connection object from psycopg2 librabry
        table_name (str) : name of the table to update
        var_names (tuple<str>) : variable names of the table
        where (str) : selection critere (e.g. 'id = 5')
        order_by (tuple, str) : order results (e.g. ('uuid',  'DESC')
        limit (int) : limit the amount of results
        dict_cursor (bool) : return result as an ordered dict
    """
    var_names_SQL = sql_name_formatter(var_names)

    query = sql.SQL("select {0} from {1} ").format(
        sql.SQL(", ").join(var_names_SQL), sql.SQL(table_name)
    )
    # SQL.Identifier does not work with underscore names for tables?

    if where is not None:
        query += sql.SQL("WHERE {0} = {1} ").format(
            sql.Identifier(where[0]), sql.Literal(where[1])
        )
    if order_by is not None:
        query += sql.SQL("ORDER BY {0} {1} ").format(
            sql.Identifier(order_by[0]), sql.SQL(order_by[1])
        )
    if limit is not None:
        query += sql.SQL("LIMIT {0} ").format(sql.SQL(str(int(limit))))

    return execute_query(conn, query, dict_cursor)


def insert_row_in_table(
    conn, table_name, var_names, var_values, returning=None, custom_statement=""
):
    """
    insert a row in a table

    Args:
        conn (psycopg2.connect) : connection object from psycopg2 librabry
        table_name (str) : name of the table to update
        var_names (tuple<str>) : variable names of the table
        var_values (tuple<str>) : values corresponding to the variable names
        returning (tuple<str>) : name of a variables you want returned
    """
    var_values_SQL, placeholders = sql_value_formatter(var_values)
    var_names_SQL = sql_name_formatter(var_names)

    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ").format(
        sql.SQL(table_name),
        sql.SQL(", ").join(var_names_SQL),
        sql.SQL(", ").join(var_values_SQL),
    )

    if returning is None:
        return execute_statement(
            conn, statement + sql.SQL(custom_statement), placeholders
        )
    else:
        statement += sql.SQL(" RETURNING {} ").format(
            sql.SQL(", ").join([sql.Identifier(i) for i in returning])
        )
        return execute_query(
            conn, statement + sql.SQL(custom_statement), placeholders=placeholders
        )


def update_table(
    conn, table_name, var_names, var_values, condition=None, conditions=None
):
    """
    generate statement for updating an existing stable

    Args:
        conn (psycopg2.connect) : connection object from psycopg2 librabry
        table_name (str) : name of the table to update
        var_names (tuple<str>) : variable names of the table
        var_values (tuple<str>) : values corresponding to the variable names
        condition (tuple<str, any>) : condition for the update (e.g. ('id', 5))
        conditions (list(tuple<str, any>)) : conditiosn for the update (e.g. [('id', 5), ('version', 10)] )
    """

    statement = sql.SQL("UPDATE {} SET ").format(sql.SQL(table_name))

    names_values = name_value_formatter(var_names, var_values)
    if len(names_values) == 0:
        return ""

    statement += sql.SQL(", ").join(
        sql.SQL("{} = {} ").format(i, j) for i, j in names_values.var_name_pairs
    )

    if condition is not None:
        statement += sql.SQL("WHERE {0} = {1} ").format(
            sql.Identifier(condition[0]), sql.Literal(condition[1])
        )

    if conditions is not None and len(conditions) > 0:
        condition = conditions[0]
        statement += sql.SQL("WHERE {0} = {1} ").format(
            sql.Identifier(condition[0]), sql.Literal(condition[1])
        )
        for condition in conditions[1:]:
            statement += sql.SQL("AND {0} = {1} ").format(
                sql.Identifier(condition[0]), sql.Literal(condition[1])
            )

    return execute_statement(conn, statement, placeholders=names_values.placeholders)


def alter_table(conn, table_name, colums, dtypes):
    """
    add columns to a table

    Args:
        conn (psycopg2.connect) : connection object from psycopg2 librabry
        table_name (str) : name of the table to update
        colums (tuple<str>) : names of the columns
        dtypes (tuple<str>) : type of the column's
    """
    statement = sql.SQL("ALTER TABLE {} ADD COLUMN ").format(sql.SQL(table_name))
    statement += sql.SQL(" , ADD COLUMN ").join(
        sql.SQL(" {0} {1} ").format(sql.Identifier(i), sql.SQL(j))
        for i, j in zip(colums, dtypes)
    )

    return execute_statement(conn, statement)
