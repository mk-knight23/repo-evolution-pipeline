# FAQ

## Is this production-ready out of the box?

The core pipeline is operational, but production deployment infrastructure is not bundled in this repository.

## Which mobile frameworks are generated today?

Current active generation targets are Expo and React Native.

## Does verification run real commands?

Yes. Verification materializes generated files and executes install and build-related checks.

## What happens after a failed verification?

When repair is enabled, the pipeline attempts targeted edits and then re-runs verification.

## Can I skip stages?

Yes. Enabled stages can be passed in API requests and orchestrator supports selective stage execution.

## Does this repository create GitHub repos automatically?

No. It processes source repositories and can push generated output to GitLab when configured.
