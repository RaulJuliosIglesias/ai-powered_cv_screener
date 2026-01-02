# Security Best Practices

## API Key Security

⚠️ **Never commit API keys or sensitive information** to version control. The `.env` file is included in `.gitignore` to prevent accidental commits.

### Setting Up Environment Variables

1. Copy the `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Replace the placeholder values in `.env` with your actual API keys.

3. **Never share your `.env` file** - it should only exist on your local machine.

### Verifying Security

To ensure no sensitive data is committed to Git, you can run:

```bash
# Check for any potential secrets in your repository
git secrets --scan

# Or check history for any accidental commits of secrets
git log -p | grep -i "api_key\|password\|secret\|token"
```

## Frontend Security

- The frontend should only have access to public environment variables (prefixed with `VITE_`)
- All API calls should be made to your backend, never directly to third-party services
- Never expose API keys in client-side code

## If You Accidentally Commit Sensitive Data

1. **Rotate** any exposed API keys immediately
2. **Remove** the sensitive data from Git history using `git filter-branch` or BFG Repo-Cleaner
3. **Force push** the changes
4. **Notify** any affected parties

## Reporting Security Issues

If you discover any security vulnerabilities, please report them privately to the repository maintainers.
