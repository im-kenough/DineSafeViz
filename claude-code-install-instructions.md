# Claude Code installation and reinstall guide for Linux Mint

This guide provides step-by-step instructions to uninstall and reinstall Claude Code on Linux Mint, along with optional cleanup steps for a completely fresh installation.

## Prerequisites

Before you begin, verify that you have the following installed:

- **Node.js 18+**: Run `node --version` to check
- **npm 9+**: Run `npm --version` to check
- An **Anthropic API key**: Obtain one at https://console.anthropic.com

If you don't have Node.js or npm, install them using your package manager:

```bash
sudo apt update
sudo apt install nodejs npm
```

## Uninstall Claude Code

Follow these steps to remove Claude Code from your system.

1. Uninstall from npm:

```bash
npm uninstall -g @anthropic-ai/claude-code
```

2. Remove configuration directories:

```bash
rm -rf ~/.claude
rm -rf ~/.config/Claude\ Code
```

3. If you cloned Claude Code from a Git repository, navigate to that directory and remove it:

```bash
rm -rf /path/to/cloned/claude-code
```

## Optional: Complete cleanup

If you want to start completely fresh and remove all cached data and project-specific settings, also run:

```bash
# Remove cache directories
rm -rf ~/.cache/Claude\ Code
rm -rf ~/.local/share/Claude\ Code

# Remove project-specific settings (run this in each project directory)
rm -rf ./.claude/settings.json
```

## Reinstall Claude Code

Follow these steps to install a fresh copy of Claude Code.

1. Install Claude Code globally from npm:

```bash
npm install -g @anthropic-ai/claude-code
```

2. Verify the installation:

```bash
claude code --version
```

3. Set up authentication with your API key:

```bash
claude code auth
```

You'll be prompted to enter your Anthropic API key. Paste it when requested.

## After installation

Once you've completed the reinstallation, verify everything is working:

1. Navigate to a project directory (or create a test directory)
2. Run `claude code` to start the Claude Code CLI
3. Test basic functionality to ensure the installation is complete

If you encounter any issues, verify that Node.js and npm are installed correctly and that your API key is valid.
