# About

## Changelog
See `CHANGES.md`.

## Reporting issues
Open an issue at https://github.com/deepesdl/deep-code/issues.

## Contributions
PRs are welcome. Please follow the code style (black/ruff) and add tests where relevant.

## Development install
```bash
pip install -e .[dev]
pytest
pytest --cov=deep-code
black .
ruff check .
```

## Documentation commands (MkDocs)
```bash
pip install -e .[docs]      # install mkdocs + theme
mkdocs serve                # live preview at http://127.0.0.1:8000
mkdocs build                # build site into site/
mkdocs gh-deploy --clean    # publish to GitHub Pages
```

## License
MIT License. See `LICENSE`.
