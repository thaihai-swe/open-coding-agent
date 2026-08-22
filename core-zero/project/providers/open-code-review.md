# Provider: open-code-review

repo: https://github.com/alibaba/open-code-review  
homepage: https://open-codereview.ai  
package: `@alibaba-group/open-code-review`

## Setup

```bash
npm install -g @alibaba-group/open-code-review
ocr config provider
ocr config model
```

Requirements:

- Git >= 2.41
- LLM provider configuration, unless using OCR delegation mode

After setup, set `providers.review.active: open-code-review` in `tool-providers.md`.

## Capability mapping

| Intent | Command |
| - | - |
| Diff review (workspace) | `ocr review` |
| Diff review (branch range) | `ocr review --from <base> --to <head>` |
| Diff review (commit) | `ocr review --commit <sha>` |
| Full-file scan | `ocr scan` or `ocr scan --path <path>` |
| Resume interrupted review | `ocr review ... --resume <session-id>` |
| Delegation preview | `ocr delegate preview` |
| Delegation rule resolution | `ocr delegate rule <files...>` |

## Integration contract

- CoreZero does not reimplement OCR judgment.
- `/harness-verify` invokes the configured review provider and normalizes findings into `review.md`.
- Empty OCR output without an explicit clean result is incomplete evidence.
- Missing binary, failed auth, or non-zero exit fails loudly when review mode is `required`.
- Security-sensitive path findings still escalate through CoreZero security policy checks.
