# Claude Code Custom Commands

This directory contains custom slash commands for use with Claude Code CLI.

## Available Commands

### `/deploy`
Deploys the Stock Lambda Consumer application to AWS.

**Usage:**
```
/deploy
```

**What it does:**
- Runs `./scripts/deploy.sh`
- Builds and deploys the SAM application
- Configures all AWS resources

### `/test`
Runs the full test suite with coverage reporting.

**Usage:**
```
/test
```

**What it does:**
- Runs `./scripts/run_tests.sh`
- Executes pytest with coverage
- Generates HTML coverage report

## Adding New Commands

To add a new command:

1. Create a new `.md` file in this directory (e.g., `mycommand.md`)
2. Add a description of what the command should do
3. Use the command by typing `/mycommand` in Claude Code

## More Information

See [Claude Code Documentation](https://docs.claude.com/claude-code) for more details on custom commands.
