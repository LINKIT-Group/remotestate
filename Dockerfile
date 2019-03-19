FROM alpine as base

RUN apk update \
    && apk add --no-cache \
        python3 \
        build-base \
        python3-dev \
    && pip3 install --upgrade pip \
    && python3 -m pip install \
        wheel \
        pylint \
        boto3 \
        jinja2 \
        twine \
    && apk del \
        python3-dev \
        build-base \
    && rm -rf /opt/build/* \
    && rm -rf /var/cache/apk/* \
    && rm -rf /root/.cache/*

FROM scratch as user
COPY --from=base . .

ARG HOST_UID=${HOST_UID:-4000}
ARG HOST_USER=${HOST_USER:-nodummy}

RUN [ "${HOST_USER}" == "root" ] || \
    (adduser -h /home/${HOST_USER} -D -u ${HOST_UID} ${HOST_USER} \
    && chown -R "${HOST_UID}:${HOST_UID}" /home/${HOST_USER})

USER ${HOST_USER}
WORKDIR /home/${HOST_USER}
