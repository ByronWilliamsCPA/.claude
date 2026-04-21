---
schema_type: common
title: Context7 MCP Server Setup
status: published
owner: engineering
tags: [documentation]
purpose: Provides setup instructions for the Context7 MCP server, including available transports and Redis-powered knowledge base configuration.
---

Context7 provides intelligent documentation and library search capabilities through Redis-powered knowledge bases.

## Available Transports

Context7 offers multiple transport options for different use cases:

### 1. Standard stdio (via npm)

Best for local development with Redis credentials:

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"],
      "env": {
        "UPSTASH_REDIS_REST_URL": "${UPSTASH_REDIS_REST_URL}",
        "UPSTASH_REDIS_REST_TOKEN": "${UPSTASH_REDIS_REST_TOKEN}"
      }
    }
  }
}
```

### 2. HTTP Transport

Direct HTTP connection to Context7 cloud service:

```json
{
  "mcpServers": {
    "context7-http": {
      "transport": {
        "type": "http",
        "url": "https://mcp.context7.com/mcp"
      }
    }
  }
}
```

### 3. SSE Transport (Server-Sent Events)

Real-time streaming connection:

```json
{
  "mcpServers": {
    "context7-sse": {
      "transport": {
        "type": "sse",
        "url": "https://mcp.context7.com/sse"
      }
    }
  }
}
```

## Usage

Context7 provides access to library documentation and code examples. Use it for:

- **Library Documentation**: Get up-to-date docs for popular libraries
- **Code Examples**: Find working code snippets and patterns
- **API References**: Access complete API documentation
- **Best Practices**: Discover recommended usage patterns

## Commands

Add Context7 to your project using Claude Code CLI:

```bash
# Add HTTP transport (no credentials required)
claude mcp add --transport http context7 https://mcp.context7.com/mcp

# Add SSE transport (no credentials required)
claude mcp add --transport sse context7 https://mcp.context7.com/sse

# Add stdio transport (requires Redis credentials)
claude mcp add context7 npx -y @upstash/context7-mcp
```

## Environment Variables

For the stdio transport, add to your `~/.claude/.env`:

```bash
# Context7 with Upstash Redis (stdio transport only)
UPSTASH_REDIS_REST_URL=https://your-redis-url.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_redis_token_here
```

**Note**: HTTP and SSE transports don't require credentials.

## Choosing a Transport

- **HTTP**: Best for general use, reliable, no setup required
- **SSE**: Best for real-time applications, streaming responses
- **stdio**: Best when you have your own Redis instance with custom data

## Troubleshooting

### HTTP/SSE Connection Issues

```bash
# Test connectivity
curl -s https://mcp.context7.com/mcp
```

### stdio Transport Issues

```bash
# Verify npm package installation
npx @upstash/context7-mcp --help

# Test Redis connection
curl -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
     "$UPSTASH_REDIS_REST_URL/ping"
```

### Claude Code Integration

```bash
# List active MCP servers
claude mcp list

# Check if Context7 is connected
claude mcp status context7
```
