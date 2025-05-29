## Introduction
    Netbox 与 Guacamole 的集群 docker 部署项目
    可以根据 NetBox 登记的虚拟机，自动在 Guacamole 中创建对应的远程连接

## Quick Start
```bash
# 克隆仓库
git clone git@code.ykss.com.cn:dongxuexin/mynetbox.git

# 进入项目所在目录
cd ./mynetbox

# docker部署
docker compose up -d
```
- 注意：
    - NetBox用户默认`username` `email` `password`分别为 `admin` `admin@example.com` `admin`。可在`/env/netbox.env`修改配置 `SUPERUSER_*`。 
    - Guacamole登录时，默认用户名和密码均为`guacadmin`。因为脚本初始化时直接创建了该用户项。
    - `/env/netbox.env`中的`SUPERUSER_API_TOKEN`字段已填入默认值，仅当NetBox数据库还没有用户和Token记录时才会起作用。
        `netbox_guacamole_sync.py`文件中的`NETBOX_API_TOKEN`常量值应与之匹配。

## Reference
- https://github.com/netbox-community/netbox-docker 
- https://github.com/boschkundendienst/guacamole-docker-compose 
- https://github.com/netbox-community/netbox-docker/discussions/1408
- https://www.reddit.com/r/Netbox/comments/17uh68p/issue_with_superuser_api_token_after_database_load/