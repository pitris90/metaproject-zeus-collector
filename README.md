
# MetaProject Zeus Collector

This application provides data collection service for MetaProject Zeus.

MetaProject Zeus is project implemented as part of a master thesis for FI MUNI. It is a system used for managing projects related to HPC, their workflows and entities related to projects. Part of this system is integration with Perun, OpenStack and OIDC.


## Authors

- [Petr Balnar (@pitris90)](https://www.github.com/pitris90)


## Prerequisites
- Python 3.13
- Poetry ≥ 1.8


## Run Locally

1. Clone project and navigate to the project directory.
1. Copy variables from `.env.example` to `.env`
1. Change variables accordingly (see section `Environment Variables`)
1. Prepare environment with use of commands similarly how dockerfile prepares container + setup Kerberos ticket according to https://docs.metacentrum.cz/en/docs/access/security/kerberos
1. Install dependencies

```bash
poetry install
```

Then start the collector:

```bash
poetry run python -m collector.main
```

Or run with Docker (highly recommended, have changed env. variables):

```bash
docker compose up --build
```


## Environment Variables

If you want to test this project, you need to copy variables from `.env.example` to `.env` and fill some variables with your values.

Most values are self-explanatory, are fine for local testing and don't have to be changed, but some values are confidential and should be configured correctly.

This is list of variables that should be changed for local development:

```
ZEUS_ENDPOINT=http://nest-js-api:3000
ZEUS_API_KEY=replace-me
```
Endpoint and API key for connecting to the main MetaProject Zeus API. Generated on Zeus side, so just copy from main Zeus module COLLECTOR_API_KEY

```
PBS_USER=replace-me
PBS_PASSWORD=replace-me
PBS_KRB_CONF_HOST=skirit.ics.muni.cz
PBS_CONF_HOST=tarkil.grid.cesnet.cz
PBS_HOST=pbs-m1.metacentrum.cz
```
Credentials and hosts for PBS/MetaCentrum integration. Used for valid Kerberos credentials. User and password are those used when sign-up to e-infra.cz on https://signup.e-infra.cz/

```
ACCOUNTING_DB_HOST=database.example.org
ACCOUNTING_DB_PORT=5432
ACCOUNTING_DB_NAME=accounting
ACCOUNTING_DB_USER=collector
ACCOUNTING_DB_PASSWORD=replace-me
```
Configuration for the accounting database connection. Must be gotten from accounting database administrator in Metacentrum

```
OPENSTACK_THANOS_ENDPOINT=https://direct-thanos-query.example.org
OPENSTACK_THANOS_USERNAME=replace-me
OPENSTACK_THANOS_PASSWORD=replace-me
```
Credentials for OpenStack metrics collection via Thanos. Must be gotten from OpenStack administrator in Metacentrum


## License

[MIT](https://choosealicense.com/licenses/mit/)

