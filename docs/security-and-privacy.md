# Security and Privacy

## Data policy

Use only synthetic, public, or personally owned data. Do not import employer email, documents,
meeting transcripts, credentials, private datasets, internal prompts, or unpublished configurations.

## Secrets

- Keep `.env` out of source control.
- Add secret scanning before public release.
- Never place access tokens in experiment configurations or reports.

## API considerations

The Milestone 1 API is a local development surface, not a production service. Before external
exposure, add authentication, authorization, request logging controls, rate limits, secure headers,
input/output size limits, and a reviewed deployment threat model.

## Future multi-user design

Later milestones must introduce explicit execution context, document-level authorization, strict
user isolation, adversarial leakage tests, and trace redaction before using non-synthetic data.
