# Dataiku GitOps GitHub Action

This GitHub Action is designed to facilitate a GitOps workflow for Dataiku projects. It automates the process of creating and managing bundles in Dataiku, ensuring a seamless transition from development to production. This action is part of the Proof of Concept (POC) described in the blog article "Implementing GitOps for Dataiku: A Hands-On Guide."

## Overview

The Dataiku GitOps GitHub Action is a wrapper around the `dataiku_gitops_action.py` script. It automates the CI/CD pipeline by creating bundles from the development environment, pushing them to staging, and optionally deploying them to production after successful testing.

## Usage

To use this GitHub Action, include it in your workflow YAML file. Below are examples of how to configure the action for different stages of the GitOps workflow.

### Example: Pull Request Workflow

This example demonstrates how to use the action in a pull request workflow to test changes in the staging environment.

```yaml
name: Dataiku GitOps PR

on:
  pull_request:
    branches:
      - prod

jobs:
  run-tests:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v2

      - name: Run Dataiku GitOps Action
        uses: qcastel/dataiku-gitops-github-action@master
        with:
          python-script: "tests.py"
          dataiku_api_token_dev: ${{ secrets.DATAIKU_INSTANCE_DEV_CI_API_TOKEN }}
          dataiku_api_token_staging: ${{ secrets.DATAIKU_INSTANCE_STAGING_CI_API_TOKEN }}
          dataiku_api_token_prod: ${{ secrets.DATAIKU_INSTANCE_PROD_CI_API_TOKEN }}
          dataiku_instance_dev_url: ${{ vars.DATAIKU_INSTANCE_DEV_URL }}
          dataiku_instance_staging_url: ${{ vars.DATAIKU_INSTANCE_STAGING_URL }}
          dataiku_instance_prod_url: ${{ vars.DATAIKU_INSTANCE_PROD_URL }}
          dataiku_project_key: ${{ vars.DATAIKU_PROJECT_KEY }}
          run_tests_only: "true"
```

### Example: Release Workflow

This example shows how to use the action in a release workflow to deploy changes to the production environment.

```yaml
name: Dataiku GitOps Release

on:
  push:
    branches:
      - prod

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v2

      - name: Run Dataiku GitOps Action
        uses: qcastel/dataiku-gitops-github-action@master
        with:
          python-script: "tests.py"
          dataiku_api_token_dev: ${{ secrets.DATAIKU_INSTANCE_DEV_CI_API_TOKEN }}
          dataiku_api_token_staging: ${{ secrets.DATAIKU_INSTANCE_STAGING_CI_API_TOKEN }}
          dataiku_api_token_prod: ${{ secrets.DATAIKU_INSTANCE_PROD_CI_API_TOKEN }}
          dataiku_instance_dev_url: ${{ vars.DATAIKU_INSTANCE_DEV_URL }}
          dataiku_instance_staging_url: ${{ vars.DATAIKU_INSTANCE_STAGING_URL }}
          dataiku_instance_prod_url: ${{ vars.DATAIKU_INSTANCE_PROD_URL }}
          dataiku_project_key: ${{ vars.DATAIKU_PROJECT_KEY }}
          run_tests_only: "false"
```

## Inputs

The action requires the following inputs:

- **`python-script`**: The path to the Python script to run. This script should define the tests to be executed in the staging and production environments.

- **`dataiku_api_token_dev`**: The Dataiku API token for the development instance. This token is used to authenticate API requests.

- **`dataiku_api_token_staging`**: The Dataiku API token for the staging instance. This token is used to authenticate API requests.

- **`dataiku_api_token_prod`**: The Dataiku API token for the production instance. This token is used to authenticate API requests.

- **`dataiku_instance_dev_url`**: The URL of the development Dataiku instance.

- **`dataiku_instance_staging_url`**: The URL of the staging Dataiku instance.

- **`dataiku_instance_prod_url`**: The URL of the production Dataiku instance.

- **`dataiku_project_key`**: The key of the Dataiku project to be managed by the GitOps workflow.

- **`run_tests_only`**: A boolean flag indicating whether to run tests only on the staging environment. Set to `"true"` to skip deployment to production.

## Conclusion

This GitHub Action provides a robust framework for implementing GitOps with Dataiku. By automating the CI/CD pipeline, it ensures that your Dataiku projects are consistently tested and deployed across environments. For more details on how to set up and use this action, refer to the accompanying [blog article](https://github.com/qcastel/dataiku-gitops-blog-article).
