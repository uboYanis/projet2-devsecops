# Dependency Scan Demo

Use these examples to demonstrate that the CI/CD pipeline blocks vulnerable dependencies during the container image scan.

The pipeline currently runs Trivy with:

```yaml
--severity CRITICAL
--exit-code 1
```

So the build should fail when a dependency has a known **CRITICAL** vulnerability.

## Test Candidates

Add one of these lines temporarily to `services/api/requirements.txt`:

```txt
PyYAML==5.3
```

Reason: affected by a critical arbitrary code execution issue fixed in `5.3.1`.
Reference: https://osv.dev/vulnerability/GHSA-6757-jp84-gxfx

```txt
PyYAML==5.1.2
```

Reason: affected by a critical unsafe deserialization issue fixed in `5.2`.
Reference: https://osv.dev/vulnerability/GHSA-3pqx-4fqf-j49f

```txt
PyYAML==3.13
```

Reason: affected by a critical unsafe `yaml.load()` issue fixed in `4.1`.
Reference: https://osv.dev/vulnerability/GHSA-rprw-h62v-c2w7

## Demo Flow

1. Add one vulnerable dependency to `services/api/requirements.txt`.
2. Commit and push the change.
3. Wait for Cloud Build to run.
4. Show the Trivy step failing on a CRITICAL vulnerability.
5. Remove the vulnerable dependency.
6. Commit and push the fix.
7. Show the pipeline passing again.

## Notes

Deprecated packages do not always fail the pipeline by themselves. The scanner blocks when the package version maps to a known vulnerability at the configured severity level.
