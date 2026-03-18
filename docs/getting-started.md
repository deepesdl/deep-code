# Getting Started

## Requirements
- Python 3.10+
- GitHub token with access to the target EarthCODE metadata repo.
- Input configuration files.
- Datasets which needs to be published is uploaded to S3 like object storage and made publicly accessible.

## Install
```bash
pip install deep-code
```

## Authentication
The CLI or the Python API reads GitHub credentials from a `.gitaccess` file in the directory where you run the command:

1. **Generate a GitHub Personal Access Token (PAT)**

    1. Navigate to GitHub → Settings → Developer settings → Personal access tokens.
    2. Click “Generate new token”.
    3. Choose the following scopes to ensure full access:
        - repo (Full control of repositories — includes fork, pull, push, and read)
    4. Generate the token and copy it immediately — GitHub won’t show it again.

2. **Create the .gitaccess File**

    Create a plain text file named .gitaccess in your project directory or home folder:

    ```
    github-username: your-git-user
    github-token: your-personal-access-token
    ```
    Replace your-git-user and your-personal-access-token with your actual GitHub username and token.
