# Overview

`deep-code` is a lightweight Python CLI and API that publishes DeepESDL datasets and workflows as EarthCODE Open Science Catalog metadata. It can generate starter configs, build STAC collections and OGC API records, and open pull requests to the target EarthCODE metadata repository (production, staging, or testing).

## Features
- Generate starter dataset and workflow YAML templates.
- Publish dataset collections, workflows, and experiments via a single command.
- Build STAC collections and catalogs for Datasets and their corresponding variables automatically from the dataset metadata.
- Build OGC API records for Workflows and Experiments from your configs.
- Flexible publishling targets i.e production/staging/testing EarthCODE metadata repositories with GitHub automation.

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 110, 'rankSpacing': 160}, 'themeVariables': {'fontSize': '28px', 'lineHeight': '1.6em'}}}%%
flowchart LR
    subgraph User
        A["Config files<br/>(dataset.yaml, workflow.yaml)"]
        B["deep-code CLI<br/>(generate-config, publish)"]
    end

    subgraph App["deep-code internals"]
        C["Publisher<br/>(mode: dataset/workflow/all)"]
        D["STAC builder<br/>OscDatasetStacGenerator"]
        E["OGC record builder<br/>OSCWorkflowOGCApiRecordGenerator"]
        F["GitHubAutomation<br/>(fork, clone, branch, PR)"]
    end

    subgraph Output
        G["Generated JSON<br/>collections, variables,<br/>workflows, experiments"]
        H["GitHub PR<br/>(prod/staging/testing repo)"]
        I["EarthCODE Open Science Catalog"]
    end

    A --> B --> C
    C --> D
    C --> E
    D --> G
    E --> G
    G --> F --> H --> I
```
