# Amica AI Core

Prototype AI modules for Amica safety features.

## Areas

- Number plate OCR support for Scan Before You Ride
- Stealth Voice SOS phrase detection
- Decision engine for SOS trigger routing
- Integration contracts shared with mobile and backend teams

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the Amica branch strategy, issue workflow, commit expectations, pull request process, and CI/CD guidance.

## Deployment Strategy

- `dev` branch is used for development integration.
- Backend `dev` branch deploys to Firebase development project only.
- `main` branch is reserved for final demo/production-ready code.
- Production deployment is not automatic yet.
- Mobile app produces APK artifacts through GitHub Actions.
- AI repo produces test/artifact outputs only.

AI deployment will be considered later if the AI module becomes a server-side API.

The code is intentionally lightweight and mock-friendly until model selection, datasets, and runtime architecture are finalized.
