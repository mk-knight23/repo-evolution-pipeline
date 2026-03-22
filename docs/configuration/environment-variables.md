# Environment Variables

This file documents variables referenced in .env.example and runtime config.

## LLM

- ANTHROPIC_API_KEY: API key for model calls
- ANTHROPIC_BASE_URL: optional custom Anthropic-compatible endpoint

## DashScope

- DASHSCOPE_API_KEYS: comma-separated key list for model routing and fallback
- DASHSCOPE_OPENAI_URL: OpenAI-compatible DashScope endpoint
- DASHSCOPE_ANTHROPIC_URL: Anthropic-compatible DashScope endpoint

## GitHub

- GITHUB_TOKEN: token for GitHub API fallback fetches
- GITHUB_ORG: source organization default

## GitLab

- GITLAB_TOKEN: token used by push stage
- GITLAB_URL: GitLab host URL
- GITLAB_GROUP: destination group namespace

## Supabase

- SUPABASE_URL: optional URL for external state integration
- SUPABASE_KEY: optional key for external state integration

## Redis

- REDIS_URL: optional queue or distributed workload backing

## Pipeline Controls

- PIPELINE_VERIFY: enable verification stage execution policy
- PIPELINE_VERIFY_STRICT: fail pipeline hard on verification failure
- PIPELINE_VERIFY_WEB_EXPORT: include Expo web export check
- PIPELINE_BLOCK_PUSH_ON_VERIFY_FAIL: block push when verification fails
- PIPELINE_REPAIR: enable repair loop after failed verification
- PIPELINE_REPAIR_ATTEMPTS: number of repair retries

## Circuit Breaker

- CIRCUIT_BREAKER_THRESHOLD: failure count before breaker opens
- CIRCUIT_BREAKER_RESET_SECONDS: cooldown before retrying provider

## Recommendations

- Keep .env local and never commit real secrets.
- Use least privilege scopes for all tokens.
- Validate required values during deployment startup.
