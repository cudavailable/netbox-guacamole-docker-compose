# ---------------------------
# 这是一个根据NetBox虚机信息自动创建Guacamole远程连接的Python脚本
# ---------------------------


import requests
import psycopg2
from psycopg2 import sql
import copy



# 配置参数
# NetBox 配置
NETBOX_URL = "http://host.docker.internal:9999"
# NetBox 默认初始用户名和密码，需与/env/netbox.env中的配置匹配
# NETBOX_USER = "admin"
# NETBOX_PASSWORD = "admin"
# NETBOX_API_TOKEN_PATH = "/app/netbox_token.txt"
NETBOX_API_TOKEN = "518af729789c73ecfc898a08ac4b99dd61b34f51" # 与 netbox.env 中的 SUPERUSER_API_TOKEN 匹配

# 全局 Headers
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# # ---------------------------
# # 步骤1: 获取 NetBox API Token
# # ---------------------------
# def get_netbox_token():
#     netbox_token = None # 定义 NetBox Token

#     try:
#         # # 先读取指定路径，看看有没有对应的 NetBox Token 记录
#         # with open(NETBOX_API_TOKEN_PATH, "r") as f:
#         #     netbox_token = f.read().strip()
#         # 尝试读取现有 Token
#         try:
#             with open(NETBOX_API_TOKEN_PATH, "r") as f:
#                 netbox_token = f.read().strip()
#         except FileNotFoundError:
#             print("记录 NetBox Token 的文件不存在，将生成新 NetBox Token")
#         except IOError as ie:
#             print(f"警告: 读取 NetBox Token 文件失败 - {ie}")

#         # 判断是否已经有的 NetBox Token 记录
#         if not netbox_token:
#             # 没有 NetBox Token 记录，用POST请求获取
#             print("正在生成 NetBox Token...")

#             headers = {
#                 "Content-Type": "application/json",
#                 "Accept": "application/json; indent=4"
#             }
#             response = requests.post(
#                 f"{NETBOX_URL}/api/users/tokens/provision/",
#                 # data={"username": NETBOX_USER, "password": NETBOX_PASSWORD},
#                 headers=headers,
#                 auth=(NETBOX_USER, NETBOX_PASSWORD),
#                 json={
#                     "user": {"username": NETBOX_USER},
#                     "description": "Initial NetBox API Token"
#                 }
#             )

#             print(response.status_code)
#             response.raise_for_status()
#             netbox_token = response.json()["key"] # 拿到 NetBox Token

#             # 将 NetBox Token 记录到指定路径
#             with open(NETBOX_API_TOKEN_PATH, "w") as f:
#                 f.write(netbox_token)
            
#             print("NetBox Token 已保存至指定路径")
        
#     except Exception as e:
#         print(f"生成 NetBox Token 失败: {str(e)}")
#     finally:
#         return netbox_token

# -------------------------------
# 步骤2: 克隆模板连接配置 (PostgreSQL 直接操作版)
# -------------------------------
def clone_template_connection(db_params, template_conn_name="T"):
    """
    :param db_params: 数据库连接参数字典
    :param template_conn_name: 模板连接名称（默认为T）
    :return: 模板配置信息，字典形式（包含connection和parameters结构）
    """
    conn = None
    config = {} # 最后返回的模板连接的配置信息
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # 动态获取所有字段名
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'guacamole_connection'
            ORDER BY ordinal_position
        """)
        columns = [row[0] for row in cursor.fetchall()]
        select_fields = ", ".join(columns)

        # 查询模板连接的所有字段
        cursor.execute(f"""
            SELECT {select_fields}
            FROM guacamole_connection
            WHERE connection_name = %s
        """, (template_conn_name,))
        
        template_conn = cursor.fetchone()
        if not template_conn or len(template_conn) == 0:
            raise ValueError(f"模板连接 '{template_conn_name}' 不存在")

        # 自动映射字段名和值
        field_names = [desc[0] for desc in cursor.description]
        config_conn = dict(zip(field_names, template_conn))

        # 获取连接参数
        config_param = get_connection_parameters(cursor, config_conn["connection_id"])

        # 去掉模板连接自身的id
        config_conn = {k: v for k, v in config_conn.items() if k != "connection_id"} 
        
        # 构造返回配置信息
        config["connection"] = config_conn
        config["parameters"] = config_param

    except psycopg2.Error as e:
        raise Exception(f"数据库操作失败: {str(e)}")
    finally:
        if conn: conn.close()
        return config

# 辅助函数：获取连接参数
def get_connection_parameters(cursor, connection_id):
    """
    :param cursor: 数据库连接的cursor
    :param connection_id: 模板连接的id
    :return: 模板配置的参数信息，字典形式
    """
    cursor.execute("""
        SELECT parameter_name, parameter_value
        FROM guacamole_connection_parameter
        WHERE connection_id = %s
        """, (connection_id,))
    return {row[0]: row[1] for row in cursor.fetchall()}

# -------------------------------
# 步骤3: 从 NetBox 获取虚拟机数据
# -------------------------------
def fetch_netbox_vms(netbox_token):
    """
    :return: 虚拟机列表
    """
    try:
        # # 计算时间范围（检查过去1分钟内的新增虚拟机）
        # check_window = 1  # 单位：分钟
        # time_threshold = datetime.now(timezone.utc) - timedelta(minutes=check_window)

        # 条件筛选
        # params = {
        #     # "created__gte": time_threshold.isoformat(),
        #     "status": "active"
        #     # "id": 4
        # }
        # headers = {**HEADERS, "Authorization": f"Token {NETBOX_API_TOKEN}"}
        headers = {**HEADERS, "Authorization": f"Token {netbox_token}"}
        response = requests.get(
            f"{NETBOX_URL}/api/virtualization/virtual-machines/",
            headers=headers,
            # params=params,
        )
        response.raise_for_status()
        return response.json()["results"]  # 返回虚拟机列表
    except Exception as e:
        raise Exception(f"获取 NetBox 虚拟机失败: {str(e)}")

# -------------------------------
# 步骤4: 动态修改连接配置并批量创建
# -------------------------------
def create_dynamic_connections(db_params, base_config, netbox_vms, template_conn_name='T'):
    """
    :param db_params: 数据库连接参数字典
    :param base_config: 模板配置字典（包含connection和parameters结构）
    :param netbox_vms: 从Netbox获取的虚拟机信息列表
    :return: 成功创建的连接名称列表
    """
    created_connections = []
    conn = None

    try:
        # 建立数据库连接
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # 预编译判断是否存在同名连接SQL语句
        check_existing_sql = """
            SELECT EXISTS(
                SELECT 1 
                FROM guacamole_connection 
                WHERE connection_name = %s
            )
        """
        # 检查模板连接是否存在，这是继续的前提
        cursor.execute(check_existing_sql, (template_conn_name,))
        exists = cursor.fetchone()[0]
        if not exists:
            raise ValueError(f"连接 '{template_conn_name}' 不存在！请先创建该连接")

        # 预编译基础SQL语句
        insert_connection_query = sql.SQL("""
            INSERT INTO guacamole_connection 
            ({connection_fields}) 
            VALUES ({connection_values})
            RETURNING connection_id
        """).format(
            connection_fields=sql.SQL(', ').join(
                map(sql.Identifier, base_config["connection"].keys())
            ),
            connection_values=sql.SQL(', ').join(
                [sql.Placeholder()] * len(base_config["connection"])
            )
        )

        for vm in netbox_vms:
            current_config = None
            try:
                # 深拷贝配置模板
                current_config = copy.deepcopy(base_config)
                
                # 动态注入参数
                vm_hostname = vm["custom_fields"].get("hostname")
                if not vm_hostname or str(vm_hostname).strip() == "":
                    print("需要创建并填写 hostname 字段才能同步信息")
                    continue

                # 检查是否已存在同名连接
                cursor.execute(check_existing_sql, (vm_hostname,))
                if cursor.fetchone()[0]:
                    # 已经存在同名连接
                    print(f"连接已存在，跳过: {vm_hostname}") # test
                    continue

                # 更新连接配置
                current_config["connection"]["connection_name"] = vm_hostname  # 注意字段名是connection_name
                current_config["parameters"]["hostname"] = vm.get("primary_ip") or current_config["parameters"]["hostname"]

                # 插入主连接记录
                cursor.execute(
                    insert_connection_query,
                    list(current_config["connection"].values())
                )
                new_conn_id = cursor.fetchone()[0]

                # 构建参数插入语句
                parameters = [
                    (new_conn_id, k, str(v))
                    for k, v in current_config["parameters"].items()
                ]
                
                insert_params_query = sql.SQL("""
                    INSERT INTO guacamole_connection_parameter
                    (connection_id, parameter_name, parameter_value)
                    VALUES {}
                """).format(
                    sql.SQL(', ').join([sql.SQL("(%s, %s, %s)")] * len(parameters))
                )

                # 平铺参数列表
                flat_params = [item for param in parameters for item in param]
                cursor.execute(insert_params_query, flat_params)

                created_connections.append(vm_hostname)
                conn.commit()  # 为每个虚拟机单独提交

            except psycopg2.IntegrityError as e:
                conn.rollback()
                raise Exception(f"连接已存在或违反唯一约束 [{vm_hostname}]: {str(e)}")
            except Exception as e:
                if conn: conn.rollback()
                
                if current_config:
                    raise Exception(f"失败配置: {current_config}")
                raise Exception(f"创建连接失败 [{vm_hostname}]: {str(e)}")

    except psycopg2.Error as e:
        print(f"数据库连接错误: {str(e)}")
    except ValueError as ve:
        print(ve)
    except Exception as e:
        print(f"错误: {e}")
    finally:
        if conn: conn.close()

    return created_connections


# -------------------------------
# 主流程
# -------------------------------
if __name__ == "__main__":
    try:
        # # 宿主机内测试使用的配置
        # db_params = {
        #     "host": "localhost",        # 通过宿主机回环地址访问
        #     "port": 5432,               # 映射的宿主机端口
        #     "dbname": "guacamole_db",
        #     "user": "guacamole_user",
        #     "password": "ChooseYourOwnPasswordHere1234"  # 必须与 POSTGRES_PASSWORD 一致
        # }

        # # Docker 容器内使用的配置
        db_params = {
            "host": "host.docker.internal",  # 使用 Docker 服务名称作为主机名
            "port": 5432,                  # 容器内部默认端口（无需映射）
            "dbname": "guacamole_db",
            "user": "guacamole_user",
            "password": "ChooseYourOwnPasswordHere1234"  # 与 compose 中一致
        }

        # # 1. 获取 NetBox API Token
        # netbox_token = get_netbox_token()
        # print(netbox_token)
        # if not netbox_token:
        #     raise Exception("NetBox Token 为 None")

        # 2. 克隆模板连接（假设模板连接名为 "T"）
        template_conn_name = "T"
        base_config = clone_template_connection(db_params, template_conn_name)
        """ base_config是一个模板配置字典（包含connection和parameters结构）
        {
            'connection': {k: v}, 
            'parameters': {k: v}
        }
        """
        print(f"模板连接配置：{base_config}") # test
        
        netbox_token = NETBOX_API_TOKEN
        # 3. 获取 NetBox 虚拟机数据
        netbox_vms = fetch_netbox_vms(netbox_token)
        if not netbox_vms:
            raise Exception("NetBox 中未找到符合条件的虚拟机")
        
        # 4. 批量创建连接
        created = create_dynamic_connections(db_params, base_config, netbox_vms, template_conn_name)
        
        if len(created) > 0:
            print(f"成功创建连接: {', '.join(created)}")
        else:
            print("没有新建连接")

    except Exception as e:
        print(f"流程执行失败: {str(e)}")
