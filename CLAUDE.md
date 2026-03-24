# Lab authoring conventions

See [`contributing/conventions/agents/authoring.md`](contributing/conventions/agents/authoring.md) for full instructions on editing tasks, wiki, code, and conventions.

## Docker

Always use the env file flag when running docker compose:

```sh
docker compose --env-file .env.docker.secret <command>
```
