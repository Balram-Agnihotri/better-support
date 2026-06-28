# BetterSupport - Agentic Codebase Q&A with Slack Integration

BetterSupport is an intelligent code Q&A agent that uses LLMs with repository tools to answer questions about your codebase. It integrates with Slack for seamless team collaboration.

## Features

- 🔍 **Smart Code Search**: Combines ripgrep text search with symbol indexing for accurate results
- 📖 **Safe File Reading**: Read code with line numbers and access controls
- 🔣 **Symbol Navigation**: Find classes, functions, types, and references across the codebase
- 🧭 **Subagent Delegation**: Complex investigations can be delegated to specialized explore agents
- 💬 **Slack Integration**: Ask questions directly in Slack channels
  - Automatic Markdown to Slack formatting for better readability
  - Thread-based responses
  - Interim "investigating" messages
- 📦 **Multi-Project Support**: Manage multiple repositories with different configurations
- 🔄 **Git Submodules**: Automatic handling of git submodules
- 🔒 **Security**: Built-in access controls and path validation
- ⚡ **Performance Optimizations**:
  - In-memory event deduplication to prevent duplicate processing
  - Cached repository indexing (rebuilds only on first run)
  - Smart git pull (skips pull if repo already initialized in session)
- 📊 **Budget Tracking**: Track token usage, tool calls, and model information in responses

## Architecture

```
better-support/
├── config.yaml              # Configuration file
├── local-server.py          # Local development server
├── requirements.txt         # Python dependencies
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── git_manager.py      # Git repository management
│   ├── indexer.py          # File and symbol indexing
│   ├── tools.py            # Tool implementations
│   ├── agent.py            # LLM agent orchestration
│   └── slack/              # Slack integration
│       ├── __init__.py
│       ├── handler.py      # Event handler
│       ├── verify.py       # Signature verification
│       └── responder.py    # Message posting
└── projects/               # Cloned repositories (auto-created)
```

## Prerequisites

- Python 3.10+
- Git
- ripgrep (for code search)
- OpenAI API key
- Slack bot token and signing secret (for Slack integration)

### Install ripgrep

**macOS:**
```bash
brew install ripgrep
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ripgrep
```

**Windows:**
```bash
choco install ripgrep
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Balram-Agnihotri/better-support.git
   cd better-support
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your projects:**
   Edit `config.yaml` to add your repositories and Slack channels.

## Configuration

Edit `config.yaml` to configure:

- **Slack credentials**: Signing secret and bot token
- **LLM settings**: Provider, API key, model
- **Projects**: Repositories to index
- **Channels**: Slack channel mappings to projects
- **Access controls**: Denied paths and file patterns

Example configuration:

```yaml
projects:
  my-repo:
    repoUrl: https://github.com/username/my-repo.git
    branch: main
    submodules: true
    githubTokenEnv: GITHUB_TOKEN

channels:
  C0123456789:  # Slack channel ID
    project: my-repo
    agent: ProductLens
```

## Usage

### Local Development Server

Run the local server for testing:

```bash
SLACK_SIGNING_SECRET=1234 \
BETTERCODE_SLACK_BOT_TOKEN=xoxb1234 \
BETTERCODE_LLM_OPENAI_API_KEY=1234 \
python local-server.py
```

### Setup with ngrok

1. **Start the local server** (see above)

2. **In another terminal, start ngrok:**
   ```bash
   ngrok http 3000
   ```

3. **Configure Slack:**
   - Go to your Slack App Settings → Event Subscriptions
   - Set Request URL to: `https://abc123.ngrok.io/slack/events`
   - Subscribe to bot events: `app_mention`, `message.channels`
   - Reinstall the app in your workspace

4. **Test in Slack:**
   ```
   @BetterCode how does the authentication work?
   ```

## Tools Available to the Agent

The agent has access to these tools:

- **search**: Search code, text, symbols, or list directories
- **read**: Read file contents with line numbers
- **workspaceSymbols**: Fuzzy search for symbols by name
- **findSymbol**: Find specific symbol definitions
- **documentSymbols**: List all symbols in a file
- **findReferences**: Find usages of a symbol
- **recordFinding**: Record discoveries with evidence
- **updateHypothesis**: Track investigation hypothesis
- **getWorkspaceSummary**: Review investigation progress
- **agent**: Delegate to subagent for complex tasks

## Agent Prompts

Custom agent prompts can be stored in your repository at:
```
.github/agents/ProductLens.agent.md
.github/agents/explore.agent.md
```

These prompts define the agent's behavior and expertise.

## Security

BetterCode includes several security features:

- **Path validation**: Prevents directory traversal attacks
- **Access controls**: Configurable deny lists for sensitive files
- **Signature verification**: Validates Slack requests
- **Read-only**: Agent cannot modify files or run arbitrary commands

## Budget Tracking

Every investigation includes detailed statistics appended as a footer to the response:

- **Duration**: Time taken to investigate
- **Model**: LLM model used (e.g., gpt-4-turbo)
- **API Calls**: Number of LLM API calls made
- **Tokens**: Total tokens used (prompt + completion)
- **Tools Used**: List of tools called with counts

Example footer:
```
⏱️ 12.3s | 🤖 gpt-4-turbo | 🎫 15,234 tokens | 🔧 3 API calls | 🛠️ search:4, read:3, workspaceSymbols:1
```

This helps you:
- Monitor costs and performance
- Understand investigation depth
- Debug issues
- Optimize configurations

## Performance Optimizations

### Event Deduplication

Slack events are deduplicated in-memory to prevent:
- Multiple API calls for the same event
- Duplicate responses in channels
- Wasted tokens and costs

Events are tracked for 1 hour and automatically cleaned up.

### Repository Caching

Repositories are cached in memory after first initialization:
- **First run**: Clone repo, init submodules, build index (~30-60s)
- **Subsequent runs**: Use cached repo and index (~1-2s)

This dramatically improves response times for repeated questions.

To force a rebuild:
- Restart the server
- Or manually delete the `projects/` directory

## Development

### Project Structure

- `src/config.py`: Configuration loading and management
- `src/git_manager.py`: Git operations with submodule support
- `src/indexer.py`: File and symbol indexing
- `src/tools.py`: Tool implementations for the agent
- `src/agent.py`: LLM orchestration and tool loop
- `src/slack/`: Slack integration modules

### Adding New Tools

1. Add tool implementation to `src/tools.py`
2. Add tool schema to `TOOLS_SCHEMA` in `src/agent.py`
3. Wire up tool execution in `Agent._execute_tool()`

### Testing

Run the local server and test with ngrok or directly via HTTP:

```bash
curl -X POST http://localhost:3000/health
```

## Troubleshooting

### Repository not cloning

- Check that `GITHUB_TOKEN` is set if the repository is private
- Verify the repository URL in `config.yaml`
- Check git credentials and network connectivity

### Submodules not initializing

- Ensure `submodules: true` in project config
- Check that `GITHUB_TOKEN` has access to submodule repositories
- Verify `.gitmodules` file exists in the repository

### Slack signature verification failing

- Verify `SLACK_SIGNING_SECRET` is correct
- Check that the request is coming from Slack
- Ensure system clock is synchronized (signature includes timestamp)

### Agent not responding

- Check OpenAI API key is valid
- Verify model name in config (e.g., `gpt-4-turbo`)
- Check logs for errors: `tail -f local-server.log`

## Environment Variables

Required:
- `SLACK_SIGNING_SECRET`: Slack app signing secret
- `BETTERSUPPORT_SLACK_BOT_TOKEN`: Slack bot OAuth token
- `BETTERSUPPORT_LLM_OPENAI_API_KEY`: OpenAI API key

Optional:
- `GITHUB_TOKEN`: GitHub personal access token for private repos

## License

MIT

## Credits

Based on the BetterCode/BetterAnswer Colab POC notebook with enhancements for production use.
