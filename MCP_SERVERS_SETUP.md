# MCP Servers Configuration

This document describes the Model Context Protocol (MCP) servers configured for this marketing intelligence system and how to set them up.

## Overview

MCP (Model Context Protocol) is an open standard that enables AI assistants to securely connect to external data sources and tools. This project has been configured with 6 beneficial MCP servers that enhance development workflows, monitoring, design integration, and team collaboration.

## Configured MCP Servers

### 1. GitHub MCP Server
**Package:** `@github/github-mcp-server`
**Purpose:** Complete GitHub integration for repository management, CI/CD workflows, and collaboration

**Capabilities:**
- Read repositories and code files
- Manage issues and pull requests
- Analyze code and workflow runs
- Monitor GitHub Actions for CI/CD pipeline visibility
- Inspect workflow runs, fetch logs, and re-run failed jobs
- Manage releases and artifacts

**Setup:**
1. Generate a GitHub Personal Access Token at https://github.com/settings/tokens
2. Set the environment variable:
   ```bash
   export GITHUB_TOKEN="your_github_token_here"
   ```
3. Add to `.env` file:
   ```
   GITHUB_TOKEN=your_github_token_here
   ```

**Use Cases:**
- "Show me the CI/CD status for the latest commit"
- "Why did the release.yml job fail last night?"
- "Create an issue for the bug we just found"
- "What are the open PRs that need review?"

**References:**
- [GitHub MCP Server Guide](https://github.blog/ai-and-ml/generative-ai/a-practical-guide-on-how-to-use-the-github-mcp-server/)
- [Official Repository](https://github.com/github/github-mcp-server)

---

### 2. Puppeteer MCP Server
**Package:** `@modelcontextprotocol/server-puppeteer`
**Purpose:** Browser automation, web scraping, and screenshot capture

**Capabilities:**
- Interact with web pages programmatically
- Take full-page or element-specific screenshots
- Execute JavaScript in browser context
- Monitor console logs and network requests
- Automated testing of frontend applications
- Web content extraction for research

**Setup:**
No environment variables required - works out of the box with npx.

**Use Cases:**
- "Take a screenshot of our production app at /dashboard"
- "Check if the marketing page loads correctly"
- "Extract the trending topics from this news site"
- "Verify that the ad creative renders properly in browser"

**Security Features:**
- SSRF prevention
- Configurable resource limits
- Headless browser isolation

**References:**
- [NPM Package](https://www.npmjs.com/package/@modelcontextprotocol/server-puppeteer)
- [MCP Puppeteer Documentation](https://glama.ai/mcp/servers/@jwaldor/mcp-scrape-copilot)

---

### 3. Memory MCP Server
**Package:** `@modelcontextprotocol/server-memory`
**Purpose:** Persistent knowledge graph for maintaining context across sessions

**Capabilities:**
- Store and retrieve information in a knowledge graph
- Maintain long-term memory of project decisions
- Track relationships between entities (campaigns, products, trends)
- Semantic search across stored knowledge
- Context preservation across development sessions

**Setup:**
No environment variables required - works out of the box with npx.

**Use Cases:**
- "Remember that we decided to target Gen Z for the Pixel campaign"
- "What were the key insights from last month's trend analysis?"
- "Recall the brand voice guidelines we established"
- "What creative directions did we reject for this campaign?"

**Benefits for Marketing Intelligence:**
- Maintains campaign metadata across sessions
- Tracks trend analysis history
- Remembers creative decisions and rationale
- Links research insights to generated content

**References:**
- [NPM Package](https://www.npmjs.com/package/@modelcontextprotocol/server-memory)
- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)

---

### 4. Sentry MCP Server
**Package:** `@getsentry/sentry-mcp`
**Purpose:** Error tracking, monitoring, and performance analysis

**Capabilities:**
- Query Sentry issues and errors with full context
- Track and debug MCP server performance
- Monitor tool executions and error rates
- Full-stack error context with logs and traces
- Real-time alerting for production issues
- Performance monitoring for the ADK agent system

**Setup:**
1. Create a Sentry account at https://sentry.io
2. Create an Auth Token in Sentry settings
3. Set environment variables:
   ```bash
   export SENTRY_AUTH_TOKEN="your_sentry_auth_token"
   export SENTRY_ORG="your_org_name"
   export SENTRY_PROJECT="your_project_name"
   ```
4. Add to `.env` file:
   ```
   SENTRY_AUTH_TOKEN=your_sentry_auth_token
   SENTRY_ORG=your_org_name
   SENTRY_PROJECT=your_project_name
   ```

**Use Cases:**
- "Show me errors from the last deployment"
- "What's the error rate for the ad generation pipeline?"
- "Which clients are experiencing the most issues?"
- "Debug the stack trace for issue #12345"

**Integration with ADK:**
Can monitor the multi-agent system for errors in:
- Trend discovery skill
- Market research pipeline
- Ad creative generation
- AV production workflows

**References:**
- [Sentry MCP Documentation](https://docs.sentry.io/product/sentry-mcp/)
- [Monitoring MCP Servers Blog](https://blog.sentry.io/monitoring-mcp-server-sentry/)
- [GitHub Repository](https://github.com/getsentry/sentry-mcp)

---

### 5. Slack MCP Server
**Package:** `@slack/mcp-server`
**Purpose:** Team communication, notifications, and collaboration workflows

**Capabilities:**
- Search through Slack messages and files
- Send messages to channels and DMs
- Retrieve conversation history and context
- Automate notifications for pipeline completions
- Create AI-powered internal support bots
- Context-aware agentic workflows

**Setup:**
1. Create a Slack App at https://api.slack.com/apps
2. Enable Bot Token Scopes: `channels:history`, `channels:read`, `chat:write`, `files:read`, `search:read`, `users:read`
3. Install app to workspace and get tokens
4. Set environment variables:
   ```bash
   export SLACK_BOT_TOKEN="xoxb-your-bot-token"
   export SLACK_APP_TOKEN="xapp-your-app-token"
   ```
5. Add to `.env` file:
   ```
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_APP_TOKEN=xapp-your-app-token
   ```

**Use Cases:**
- "Send a summary of today's campaign analysis to #marketing"
- "Find discussions about the Pixel 9 launch"
- "Notify the team when the ad generation pipeline completes"
- "Search for previous decisions about brand guidelines"

**Benefits for Marketing Teams:**
- Automated campaign status updates
- Collaborative review of generated content
- Real-time notifications for trend discoveries
- Team-wide knowledge sharing

**References:**
- [Slack MCP Integration Guide](https://www.workato.com/the-connector/slack-mcp/)
- [Official Slack MCP Documentation](https://docs.slack.dev/ai/slack-mcp-server/)
- [Slack Platform Blog](https://slack.com/blog/news/powering-agentic-collaboration)

---

### 6. Figma MCP Server
**Package:** `figma-developer-mcp`
**Purpose:** Design system integration and design-to-code workflows

**Capabilities:**
- Access Figma files, frames, and components
- Extract design tokens (colors, typography, spacing)
- Retrieve component specifications
- Bridge designs with AI coding assistants
- Design-informed code generation
- Automated design system documentation

**Setup:**
1. Generate a Figma Personal Access Token at https://www.figma.com/developers/api#access-tokens
2. Set environment variable:
   ```bash
   export FIGMA_TOKEN="your_figma_token"
   ```
3. Add to `.env` file:
   ```
   FIGMA_TOKEN=your_figma_token
   ```

**Use Cases:**
- "Extract the color palette from the Pixel 9 campaign designs"
- "What are the specs for the hero image component?"
- "Generate React components matching the Figma mockups"
- "Get spacing values from the design system"

**Benefits for Creative Team:**
- Ensures pixel-perfect implementation of designs
- Maintains design system consistency
- Accelerates design-to-code workflow
- Provides design context to AI assistants

**References:**
- [Figma MCP Server Guide](https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Figma-MCP-server)
- [Figma Blog Announcement](https://www.figma.com/blog/introducing-figma-mcp-server/)
- [NPM Package](https://www.npmjs.com/package/figma-developer-mcp)

---

## Additional MCP Servers to Consider

Based on the project's Google Cloud Platform integration, here are additional servers that could be valuable but require more setup:

### Google Cloud Platform MCP Server
**Repository:** `github.com/LokiMCPUniverse/gcp-mcp-server`
**Purpose:** Direct GCP service integration (BigQuery, GCS, Vertex AI)

**Note:** This is a community-maintained server that requires manual installation:
```bash
git clone https://github.com/LokiMCPUniverse/gcp-mcp-server.git
cd gcp-mcp-server
npm install && npm run build
```

**Why Not Included Yet:**
- Requires Google Cloud SDK authentication
- Not available as simple npx package
- Needs project-specific GCP configuration

**Official Google MCP Support:**
Google announced official MCP support for BigQuery, Cloud Storage, and other services in early 2026. These will be fully managed remote MCP servers automatically enabled when you enable BigQuery (available after March 17, 2026).

**References:**
- [BigQuery MCP Documentation](https://cloud.google.com/bigquery/docs/use-bigquery-mcp)
- [Google Cloud MCP Blog](https://cloud.google.com/blog/products/ai-machine-learning/announcing-official-mcp-support-for-google-services)

### Kubernetes MCP Server
**Relevant for:** Cloud Run and container deployments

If deploying to Kubernetes/GKE:
```bash
npx -y @containers/kubernetes-mcp-server
```

**References:**
- [Kubernetes MCP Repository](https://github.com/containers/kubernetes-mcp-server)

---

## Environment Variables Summary

Create or update your `.env` file with the following (only add services you're using):

```bash
# GitHub Integration
GITHUB_TOKEN=your_github_personal_access_token

# Sentry Monitoring (Optional)
SENTRY_AUTH_TOKEN=your_sentry_auth_token
SENTRY_ORG=your_organization_name
SENTRY_PROJECT=your_project_name

# Slack Integration (Optional)
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# Figma Design Integration (Optional)
FIGMA_TOKEN=your_figma_personal_access_token

# Existing GCP Variables (Already Configured)
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your_gcp_project_id
GOOGLE_CLOUD_PROJECT_NUMBER=your_gcp_project_number
GOOGLE_CLOUD_LOCATION=us-central1
BUCKET=your_gcs_bucket_name
YT_SECRET_MNGR_NAME=your_youtube_api_secret_name
```

---

## Activating MCP Servers

After adding environment variables:

1. **Restart Claude Code** to pick up the new `.mcp.json` configuration

2. **Approve MCP Servers** when prompted, or enable all project servers:
   ```bash
   # Add to .claude/settings.local.json (optional)
   "enableAllProjectMcpServers": true
   ```

3. **Verify Configuration:**
   - Type `/mcp` in Claude Code to see available servers
   - Check that servers show as "connected"

4. **Test a Server:**
   Try a simple query like:
   - "List my GitHub repositories" (tests GitHub server)
   - "Take a screenshot of google.com" (tests Puppeteer server)
   - "Remember that our target audience is Gen Z" (tests Memory server)

---

## Benefits for This Marketing Intelligence System

### Development Workflow
- **GitHub:** Manage code reviews, CI/CD, and releases
- **Sentry:** Monitor production errors and performance
- **Puppeteer:** Test frontend and capture visual assets

### Marketing & Creative
- **Figma:** Bridge designs with implementation
- **Slack:** Collaborate on campaigns and share results
- **Memory:** Maintain campaign context and creative decisions

### Research & Analytics
- **Puppeteer:** Web scraping for competitive analysis
- **GitHub:** Access trend data from public repositories
- **Memory:** Track insights across research sessions

### Team Collaboration
- **Slack:** Real-time updates on pipeline completions
- **GitHub:** Issue tracking and PR reviews
- **Sentry:** Error alerts for production issues

---

## Security Best Practices

1. **Never commit tokens to git:**
   - Ensure `.env` is in `.gitignore`
   - Use environment variables, not hardcoded values

2. **Use minimal token scopes:**
   - GitHub: Only grant necessary repository permissions
   - Slack: Limit bot scopes to required channels
   - Figma: Use read-only tokens if possible

3. **Rotate tokens regularly:**
   - Set expiration dates where possible
   - Update tokens quarterly

4. **Use Secret Manager for production:**
   - Store tokens in GCP Secret Manager
   - Reference them in Cloud Run deployment

---

## Troubleshooting

### Server Won't Connect
- Check environment variables are set correctly
- Verify token has required permissions
- Check network connectivity
- Review Claude Code logs

### Permission Errors
- Update token scopes in service settings
- Regenerate token with correct permissions
- Verify organization/workspace access

### Rate Limiting
- Most MCP servers respect API rate limits
- Sentry: Monitor quota usage
- GitHub: Use authenticated requests for higher limits
- Slack: Be mindful of message frequency

---

## Additional Resources

### Official MCP Documentation
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [Official MCP Registry](https://registry.modelcontextprotocol.io/)
- [Anthropic MCP Announcement](https://www.anthropic.com/news/model-context-protocol)

### Community Resources
- [MCP Servers Directory](https://apitracker.io/mcp-servers)
- [Awesome MCP Servers](https://mcpservers.org/)
- [GitHub MCP Repository](https://github.com/modelcontextprotocol/servers)

### Google Cloud MCP Integration
- [BigQuery MCP Server](https://cloud.google.com/blog/products/data-analytics/using-the-fully-managed-remote-bigquery-mcp-server-to-build-data-ai-agents)
- [MCP Toolbox for Databases](https://codelabs.developers.google.com/mcp-toolbox-bigquery-dataset)
- [Google ADK & MCP Integration](https://cloud.google.com/blog/products/ai-machine-learning/bigquery-meets-google-adk-and-mcp)

---

## Next Steps

1. **Prioritize Setup:** Start with GitHub and Memory servers (no credentials needed for Memory)
2. **Add Monitoring:** Set up Sentry for production error tracking
3. **Enable Collaboration:** Configure Slack for team notifications
4. **Design Integration:** Add Figma if working with design team
5. **Web Automation:** Use Puppeteer for testing and research

For questions or issues, refer to the individual server documentation linked above.
