# MCP Servers Quick Reference

Quick reference for the 6 MCP servers configured in this project.

## Active MCP Servers

| Server | Package | Setup Required | Purpose |
|--------|---------|----------------|---------|
| **GitHub** | `@github/github-mcp-server` | Yes - Token | Repo management, CI/CD, PRs, issues |
| **Puppeteer** | `@modelcontextprotocol/server-puppeteer` | No | Browser automation, screenshots |
| **Memory** | `@modelcontextprotocol/server-memory` | No | Persistent knowledge graph |
| **Sentry** | `@getsentry/sentry-mcp` | Yes - Token | Error tracking, monitoring |
| **Slack** | `@slack/mcp-server` | Yes - Bot tokens | Team communication |
| **Figma** | `figma-developer-mcp` | Yes - Token | Design system integration |

## Quick Setup Commands

### 1. GitHub (Required)
```bash
# Get token: https://github.com/settings/tokens
export GITHUB_TOKEN="your_token"
echo "GITHUB_TOKEN=your_token" >> .env
```

### 2. Sentry (Optional - Recommended for Production)
```bash
# Get token: https://sentry.io/settings/account/api/auth-tokens/
export SENTRY_AUTH_TOKEN="your_token"
export SENTRY_ORG="your_org"
export SENTRY_PROJECT="your_project"
```

### 3. Slack (Optional - For Team Notifications)
```bash
# Create app: https://api.slack.com/apps
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_APP_TOKEN="xapp-..."
```

### 4. Figma (Optional - For Design Team)
```bash
# Get token: https://www.figma.com/developers/api#access-tokens
export FIGMA_TOKEN="your_token"
```

## Example Queries

### GitHub MCP
```
- "Show me open PRs that need review"
- "Why did the CI pipeline fail?"
- "Create an issue for X bug"
- "List recent commits on main branch"
- "Show GitHub Actions workflow status"
```

### Puppeteer MCP
```
- "Take a screenshot of https://example.com"
- "Extract the main heading from our landing page"
- "Check if the dashboard loads correctly"
- "Get trending topics from news site X"
```

### Memory MCP
```
- "Remember that our target audience is Gen Z"
- "What were the key insights from last week?"
- "Recall the brand voice guidelines"
- "What creative directions did we try?"
```

### Sentry MCP
```
- "Show errors from the last deployment"
- "What's the error rate for the ad pipeline?"
- "Debug issue #12345"
- "Which components have the most errors?"
```

### Slack MCP
```
- "Send a summary to #marketing channel"
- "Find discussions about Pixel 9 launch"
- "Search for previous brand decisions"
- "Notify team when pipeline completes"
```

### Figma MCP
```
- "Get color palette from design file X"
- "Extract component specs for hero section"
- "What are the spacing values in design system?"
- "Get typography styles from mockups"
```

## Activation Checklist

- [ ] Created `.mcp.json` configuration file
- [ ] Added environment variables to `.env`
- [ ] Restarted Claude Code
- [ ] Approved MCP servers when prompted
- [ ] Tested GitHub integration
- [ ] (Optional) Set up Sentry monitoring
- [ ] (Optional) Configured Slack notifications
- [ ] (Optional) Connected Figma designs

## Troubleshooting

**Server won't connect:**
- Check `.env` has correct tokens
- Verify token permissions/scopes
- Restart Claude Code

**Permission errors:**
- Regenerate token with correct scopes
- Check workspace/org access

**Rate limiting:**
- Use authenticated requests (GitHub)
- Monitor quota usage (Sentry)
- Reduce request frequency

## Files Created

- `.mcp.json` - MCP server configuration
- `MCP_SERVERS_SETUP.md` - Detailed setup guide
- `MCP_QUICK_REFERENCE.md` - This file
- `.env.example` - Updated with MCP variables

## Next Steps

1. **Minimum Setup:** Add `GITHUB_TOKEN` to `.env`
2. **Restart:** Restart Claude Code to load MCP servers
3. **Test:** Try "List my GitHub repositories"
4. **Expand:** Add other servers as needed

For detailed setup instructions, see `MCP_SERVERS_SETUP.md`.
