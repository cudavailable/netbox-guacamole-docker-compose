# 使用 Debian Bookworm 作为基础镜像（与你的 .deb 包兼容）
FROM debian:bookworm

# 安装基础工具和依赖
RUN apt-get update && apt-get install -y \
    wget \
    apache2 \
    libssl3 \          
    openssl \          
    libcjose0 \
    libhiredis0.14 \
    ca-certificates \
    dpkg \
 && rm -rf /var/lib/apt/lists/*

# 下载并安装 mod_auth_openidc
RUN wget https://github.com/OpenIDC/mod_auth_openidc/releases/download/v2.4.17/libapache2-mod-auth-openidc_2.4.17-1.bookworm_amd64.deb \
 && dpkg -i libapache2-mod-auth-openidc_2.4.17-1.bookworm_amd64.deb \
 && rm libapache2-mod-auth-openidc_2.4.17-1.bookworm_amd64.deb

# 启用 Apache 模块
RUN a2enmod proxy proxy_http proxy_wstunnel headers rewrite auth_openidc

# 禁用默认站点
RUN a2dissite 000-default

# 复制自定义配置文件（需提前准备好）
COPY conf/httpd.conf /etc/apache2/sites-available/
RUN a2ensite httpd

# # 检查配置语法
# RUN apache2ctl configtest

# 暴露端口
EXPOSE 80

# 启动 Apache（使用前台模式）
CMD ["apache2ctl", "-D", "FOREGROUND"]