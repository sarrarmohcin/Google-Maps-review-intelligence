FROM postgres:16

# install pg_cron
RUN apt-get update && apt-get install -y postgresql-16-cron

# enable extension at startup
RUN echo "shared_preload_libraries = 'pg_cron'" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "cron.database_name = 'app_db'" >> /usr/share/postgresql/postgresql.conf.sample