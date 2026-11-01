# Repository identity and requested rename

The project architecture is **WE THE PEOPLE Ω — Layers A–E**. The repository still uses the GitHub slug `we-the-people-omega-layer-a`; its requested settings rename has not been applied.

## Requested GitHub settings

- Repository name: `we-the-people-omega-layer-a-e`
- Description: WE THE PEOPLE Ω — Layers A–E: Constitutional Legitimacy, Government Operations, Human and Community Outcomes, Intelligence and Evidence, and Transformation and Institutional Learning. Includes a 50-slot portfolio, controllable synthetic workflows and Capacity Atlas.

An owner or administrator can apply the repository name in GitHub **Settings → General → Repository name**, and edit the **About** description on the repository home page. Apply these settings with a GitHub account that has repository administration rights.

The requested name describes the complete architecture and current synthetic prototypes, not completed institutional implementations or permission to operate public services. Repository links in the source continue to use the actual current location until the settings rename is verified.

## Local checkouts after the rename

After the new GitHub name is applied and verified, update existing checkouts from their repository root:

```sh
git remote set-url origin https://github.com/tltmgnt/we-the-people-omega-layer-a-e.git
git remote -v
```

Update maintained external bookmarks and integrations to the verified current URL. Renaming the repository does not require moving the `layer-b/` application or `capacity-atlas/` source directories.

## Layer names and provenance

Layer A remains **Constitutional Legitimacy**. Its schema, A1–A7 prompts, validator, statuses and legal-review holds retain that name. The `layer-b/` subtree remains the shared application's implementation location.

Historical import and release records keep the original Layer A context where it describes the actual history. The vendored Layer A provenance retains its source name, pinned commit and unchanged schema bytes. The separately hosted Capacity Atlas Site retains its own access and deployment settings.

[Full architecture](README.md) · [Repository overview](../../README.md)
