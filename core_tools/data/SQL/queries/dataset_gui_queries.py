from dataclasses import dataclass

from core_tools.data.SQL.SQL_common_commands import update_table
from core_tools.data.SQL.SQL_connection_mgr import SQL_database_manager


import datetime

class alter_dataset:
    @staticmethod
    def update_name(uuid, name):
        conn = SQL_database_manager().conn_local
        update_table(conn, 'global_measurement_overview', ('exp_name', 'table_synchronized'), (name, False), condition = ('uuid',uuid))
        conn.commit()

    @staticmethod
    def star_measurement(uuid, state):
        conn = SQL_database_manager().conn_local
        update_table(conn, 'global_measurement_overview', ('starred', 'table_synchronized'), (state, False), condition = ('uuid', uuid))
        conn.commit()

class query_for_samples():
    @staticmethod
    def get_projects(set_up = None, sample = None):
        # get all projects for a selected set-up/sample (None is no selection)
        return query_for_samples.__get_x_given_yz('project', ('set_up', set_up), ('sample', sample))

    @staticmethod
    def get_set_ups(project = None, sample = None):
        #get all set ups for a selected project/sample (None is no selection)
        return query_for_samples.__get_x_given_yz('set_up', ('project', project), ('sample', sample))

    @staticmethod
    def get_samples(set_up = None, project = None):
        # get all samples for a selected project/set-up (None is no selection)
        return query_for_samples.__get_x_given_yz('sample', ('project', project), ('set_up', set_up))

    @staticmethod
    def __get_x_given_yz(to_get, condition_x, condition_y):

        statement = "SELECT DISTINCT {} from sample_info_overview ".format(to_get)

        if condition_x[1] is not None and condition_y[1] is not None:
            statement += "WHERE {} = '{}' and {} = '{}';".format(*condition_x, *condition_y)
        elif condition_x[1] is not None:
            statement += "WHERE {} = '{}' ;".format(*condition_x)
        elif condition_y[1] is not None:
            statement += "WHERE {} = '{}' ;".format(*condition_y)
        else:
            statement += ";"

        cur = SQL_database_manager().conn_local.cursor()
        cur.execute(statement)
        res = cur.fetchall()
        result = set(sum(res, () ))
        cur.close()

        cur = SQL_database_manager().conn_remote.cursor()
        cur.execute(statement)
        res = cur.fetchall()
        result |= set(sum(res, () ))
        cur.close()
        return sorted(list(result))


@dataclass
class measurement_results:
    my_id : int
    uuid : int
    name : str
    start_time : datetime
    project :str
    set_up : str
    sample : str
    starred : str
    _keywords : list = None

class query_for_measurement_results:
    @staticmethod
    def get_results_for_date(date, sample, set_up, project, remote=False):
        if date is None:
            return []
        statement = "SELECT id, uuid, exp_name, start_time, project, set_up, sample, starred, keywords FROM global_measurement_overview "
        statement += "WHERE start_time >= '{}' and start_time < '{} '".format(date, date+ datetime.timedelta(1))
        if sample is not None:
            statement += " and sample =  '{}' ".format(sample)
        if set_up is not None:
            statement += " and set_up = '{}' ".format(set_up)
        if project is not None:
            statement += " and project = '{}' ".format(project)
        statement += " ;"

        res = query_for_measurement_results._execute(statement, remote)
        return query_for_measurement_results._to_measurement_results(res)

    @staticmethod
    def get_all_dates_with_meaurements(project, set_up, sample, remote=False):
        statement = "SELECT DISTINCT date(start_time) FROM global_measurement_overview "
        statement += "where 1=1 "
        if sample is not None:
            statement += " and sample =  '{}' ".format(sample)
        if set_up is not None:
            statement += " and set_up = '{}' ".format(set_up)
        if project is not None:
            statement += " and project = '{}' ".format(project)
        statement += ';'

        res = query_for_measurement_results._execute(statement, remote)

        res = list(sum(res, ()))
        res.sort(reverse=True)

        return res

    @staticmethod
    def search_query(exp_id=None, uuid=None, name=None,
                     date=None,
                     start_time=None, end_time=None,
                     project=None, set_up=None, sample=None,
                     remote=False):
        statement = "SELECT id, uuid, exp_name, start_time, project, set_up, sample, keywords FROM global_measurement_overview "
        statement += "WHERE 1=1 "

        if exp_id is not None:
            statement += f" and id = '{exp_id}' "
        if uuid is not None:
            statement += f" and uuid = '{uuid}' "
        if date is not None:
            statement += f" and date(start_time) = '{date}' "
        if start_time is not None:
            statement += f" and start_time >= '{start_time}' "
        if end_time is not None:
            statement += f" and start_time < '{end_time}' "
        if sample is not None:
            statement += f" and sample =  '{sample}' "
        if set_up is not None:
            statement += f" and set_up = '{set_up}' "
        if project is not None:
            statement += f" and project = '{project}' "
        if name:
            statement += f" and exp_name like '%{name}%' "
        statement += " ;"

        res = query_for_measurement_results._execute(statement, remote)

        return query_for_measurement_results._to_measurement_results(res)

    @staticmethod
    def detect_new_meaurements(max_measurement_id=0, remote=False,
                               project=None, set_up=None, sample=None):
        statement = "SELECT max(id) from global_measurement_overview"
        where = []
        where.append(f"id >= {max_measurement_id}")
        if sample is not None:
            where.append(f"sample =  '{sample}'")
        if set_up is not None:
            where.append(f"set_up = '{set_up}'")
        if project is not None:
            where.append(f"project = '{project}'")
        if len(where) > 0:
            statement += " WHERE " + ' AND '.join(where)
        statement += " ;"

        res = query_for_measurement_results._execute(statement, remote)

        update = False
        if res[0][0] != max_measurement_id:
            update =True
            max_measurement_id = res[0][0]

        return update, max_measurement_id

    @staticmethod
    def _execute(statement, remote):
        connection = SQL_database_manager().conn_remote if remote else SQL_database_manager().conn_local
        cur = connection.cursor()
        cur.execute(statement)
        res = cur.fetchall()
        cur.close()
        return res

    @staticmethod
    def _to_measurement_results(res):
        data = []
        for entry in res:
            data.append(measurement_results(*entry))
        return data

