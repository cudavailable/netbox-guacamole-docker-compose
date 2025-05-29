#!/bin/bash
# 等待数据库就绪（关键！）
until python3 /opt/netbox/netbox/manage.py migrate --check >/dev/null 2>&1; do
  echo "等待数据库准备完成..."
  sleep 5
done

# 检查是否已存在超级用户
if ! python3 /opt/netbox/netbox/manage.py shell --command="from django.contrib.auth import get_user_model; User = get_user_model(); print(User.objects.filter(is_superuser=True).exists())" | grep -q "True"; then
  echo "创建超级用户..."
  export DJANGO_SUPERUSER_USERNAME="admin"
  export DJANGO_SUPERUSER_EMAIL="admin@example.com"
  export DJANGO_SUPERUSER_PASSWORD="admin"
  python3 /opt/netbox/netbox/manage.py createsuperuser --noinput
fi

# 继续执行原始 Entrypoint
exec "$@"
