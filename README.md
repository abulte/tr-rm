# tr-rm

_WIP_

Génère une liste des trains supprimés depuis [l'API "ouverte" de la SNCF](https://numerique.sncf.com/startup/api).

## TODO

- [ ] handle multiple journeys for a disruption
- [ ] test pagination
- [x] automate
    - [x] handle `429`
    - [x] upload to [data.gouv.fr](https://www.data.gouv.fr/fr/datasets/liste-des-trains-sncf-supprimes/)
- [ ] quick viz: bar chart by day stacked by type
- [ ] plug Sentry

## Snippets

```sql
select count(*) from disruptions where application_periods->'0'->>'begin' LIKE "20230323%";
```

```console
$ poetry run tr_rm tomorrow
$ poetrun run tr_rm export_csv 20230323
```
