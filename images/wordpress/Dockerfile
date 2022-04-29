FROM php:8.1-apache

RUN apt-get update \
    && apt-get upgrade -yy \
    && apt-get install -yy --no-install-recommends apt-utils gnupg libjpeg-dev \
        libpng-dev libwebp-dev libzip-dev zlib1g-dev libfreetype6-dev lsb-release \
        software-properties-common supervisor tini unzip zip \
    && echo "deb http://packages.cloud.google.com/apt gcsfuse-jessie main" | tee /etc/apt/sources.list.d/gcsfuse.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update \
    && apt-get install -y gcsfuse \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN docker-php-ext-install zip \
    && docker-php-ext-install mysqli pdo pdo_mysql \
    && docker-php-ext-install exif \
    && docker-php-ext-configure gd --with-freetype --with-jpeg --with-webp \
    && docker-php-ext-install -j "$(nproc)" gd \
    && a2enmod rewrite

COPY app /app
COPY wordpress/ /var/www/html/

WORKDIR /var/www/html

# Use tini to manage zombie processes and signal forwarding
# https://github.com/krallin/tini
ENTRYPOINT ["/usr/bin/tini", "--"]

# Pass the startup script as arguments to Tini
CMD ["/app/entrypoint.sh"]
