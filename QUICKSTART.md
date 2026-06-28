# Quick Start Guide

Get BetterSupport running in 5 minutes!

## Prerequisites

Install these first:

```bash
# macOS
brew install python3 ripgrep

# Ubuntu/Debian
sudo apt-get install python3 python3-pip ripgrep

# Windows
choco install python ripgrep
```

## Step 1: Install Dependencies

```bash
git clone https://github.com/Balram-Agnihotri/better-support.git
cd better-support
pip install -r requirements.txt
```

Or use the setup script:

```bash
./setup.sh
```

## Step 2: Configure Environment

Set your API keys:

```bash
export BETTERSUPPORT_LLM_OPENAI_API_KEY=sk-your-openai-key-here
export SLACK_SIGNING_SECRET=your-slack-signing-secret
export BETTERSUPPORT_SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
```

For private GitHub repos, also set:

```bash
export GITHUB_TOKEN=ghp_your-github-token
```

## Step 3: Configure Your Project

Edit `config.yaml`:

```yaml
projects:
  my-project:
    repoUrl: https://github.com/username/my-repo.git
    branch: main
    submodules: false

channels:
  C0123456789:  # Your Slack channel ID
    project: my-project
    agent: ProductLens
```

## Step 4: Test Without Slack

Run the standalone test:

```bash
python test_agent.py
```

Enter a question like:
- "What is the main purpose of this repository?"
- "How does authentication work?"
- "Find all database queries"

**Note**: First run will take 30-60s (cloning + indexing). Subsequent runs will be much faster (~1-2s) thanks to caching!

The output will show a detailed budget summary with:
- Investigation duration
- Model used
- Token usage
- API calls made
- Tools used with counts

## Step 5: Run with Slack (Optional)

### Start Local Server

```bash
python local-server.py
```

### Setup ngrok

In another terminal:

```bash
ngrok http 3000
```

Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)

### Configure Slack App

1. Go to https://api.slack.com/apps
2. Select your app
3. Go to **Event Subscriptions**
4. Enable Events
5. Set Request URL: `https://abc123.ngrok.io/slack/events`
6. Subscribe to bot events:
   - `app_mention`
   - `message.channels`
7. Save changes
8. Reinstall app to workspace

### Test in Slack

In a configured Slack channel:

```
@BetterSupport how does the authentication work?
```

## Troubleshooting

### "No module named 'src'"

Make sure you're in the project directory:

```bash
cd /Users/balramagnihotri/Documents/Repos/BetterAnswer
```

### "ripgrep not found"

Install ripgrep:

```bash
# macOS
brew install ripgrep

# Ubuntu/Debian
sudo apt-get install ripgrep
```

### "Failed to load config"

Make sure `config.yaml` exists and environment variables are set:

```bash
echo $BETTERSUPPORT_LLM_OPENAI_API_KEY
echo $SLACK_SIGNING_SECRET
echo $BETTERSUPPORT_SLACK_BOT_TOKEN
```

### "Repository not cloning"

For private repos, set `GITHUB_TOKEN`:

```bash
export GITHUB_TOKEN=ghp_your-token
```

### Slack signature verification failing

- Check that `SLACK_SIGNING_SECRET` is correct
- Verify ngrok is running and URL is correct in Slack settings
- Check that your system clock is synchronized

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Customize agent prompts in your repo's `.github/agents/` directory
- Add more projects to `config.yaml`
- Configure access controls and budgets

## Example Questions

Try asking these in Slack or the test script:

- "What database is used in this project?"
- "How does the user authentication flow work?"
- "Find all API endpoints"
- "What testing framework is used?"
- "Show me the configuration loading logic"
- "How are database migrations handled?"

## Support

Check the logs for errors:

```bash
# In the terminal running local-server.py
# Logs appear in real-time
```

For more help, see [README.md](README.md) or check the code in `src/`.
