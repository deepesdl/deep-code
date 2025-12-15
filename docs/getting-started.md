# Getting Started

When working with cloud platforms like DeepESDL, workflow outputs typically live in S3 object storage. Before the project ends or once datasets and workflows are finalized, move the datasets into the ESA Project Results Repository (PRR) and publish the workflows (Jupyter notebooks) to a publicly accessible GitHub repository. The notebook path becomes an input in the dataset config file.

Use the EarthCODE Project Results Repository to publish and preserve outputs from ESA-funded Earth observation projects. It is professionally maintained, FAIR-aligned, and keeps your results findable, reusable, and citable for the long term—no storage, operations, or access headaches.

To transfer datasets into the ESA PRR, contact the DeepESDL platform team at [esdl-support@brockmann-consult.de](mailto:esdl-support@brockmann-consult.de).

In the near future, `deep-code` will include built-in support for uploading your results to the ESA PRR as part of the publishing workflow, making it seamless to share your scientific contributions with the community.

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


