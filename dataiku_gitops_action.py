import hashlib
import os
import random
import string
import subprocess
import sys
import traceback
from datetime import datetime
from time import sleep

import dataikuapi
import urllib3

# Disable warnings for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Access environment variables
DATAIKU_API_TOKEN_DEV = os.getenv('DATAIKU_API_TOKEN_DEV')
DATAIKU_API_TOKEN_STAGING = os.getenv('DATAIKU_API_TOKEN_STAGING')
DATAIKU_API_TOKEN_PROD = os.getenv('DATAIKU_API_TOKEN_PROD')
DATAIKU_INSTANCE_DEV_URL = os.getenv('DATAIKU_INSTANCE_DEV_URL')
DATAIKU_INSTANCE_STAGING_URL = os.getenv('DATAIKU_INSTANCE_STAGING_URL')
DATAIKU_INSTANCE_PROD_URL = os.getenv('DATAIKU_INSTANCE_PROD_URL')
DATAIKU_PROJECT_KEY = os.getenv('DATAIKU_PROJECT_KEY')
RUN_TESTS_ONLY = os.getenv('RUN_TESTS_ONLY', 'false').lower() == 'true'
PYTHON_SCRIPT = os.getenv('PYTHON_SCRIPT', 'tests.py')
CLIENT_CERTIFICATE = os.getenv('CLIENT_CERTIFICATE', None)

# Create Dataiku clients
client_dev = dataikuapi.DSSClient(DATAIKU_INSTANCE_DEV_URL, DATAIKU_API_TOKEN_DEV, no_check_certificate=True, client_certificate=CLIENT_CERTIFICATE)
client_staging = dataikuapi.DSSClient(DATAIKU_INSTANCE_STAGING_URL, DATAIKU_API_TOKEN_STAGING, no_check_certificate=True, client_certificate=CLIENT_CERTIFICATE)
client_prod = dataikuapi.DSSClient(DATAIKU_INSTANCE_PROD_URL, DATAIKU_API_TOKEN_PROD, no_check_certificate=True, client_certificate=CLIENT_CERTIFICATE)

def get_commit_id():
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
    return result.stdout.strip()

def generate_bundle_id(commit_id):
    return f"bundle_{commit_id[:8]}"

def export_bundle(client, project_key, bundle_id, release_notes=None):
    project = client.get_project(project_key)
    project.export_bundle(bundle_id, release_notes)
    return bundle_id

def download_export(client, project_key, bundle_id, path):
    project = client.get_project(project_key)
    project.download_exported_bundle_archive_to_file(bundle_id, path)

def import_bundle(client, bundle_id, project_key, fp):
    project = client.get_project(project_key)
    print(f"Importing bundle from {fp}")
    with open(fp, 'rb') as f:
        project.import_bundle_from_stream(f)
    project.preload_bundle(bundle_id)

def activate_bundle(client, project_key, bundle_id):
    project = client.get_project(project_key)
    project.activate_bundle(bundle_id)

def list_imported_bundles(client, project_key):
    project = client.get_project(project_key)
    return project.list_imported_bundles()

def run_tests(script_path, instance_url, api_key, project_key):
    """Run pytest with environment variables for Dataiku configuration."""
    env = os.environ.copy()
    env.update({
        'DATAIKU_INSTANCE_URL': instance_url,
        'DATAIKU_API_KEY': api_key,
        'DATAIKU_PROJECT_KEY': project_key
    })
    
    result = subprocess.run([
        'pytest',
        '-v',
        script_path,
        '--no-header',  # Minimize output noise
        '--tb=short'    # Shorter traceback format
    ], env=env, capture_output=True, text=True)
    
    # Print test output for visibility
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return result.returncode == 0

def get_dataiku_latest_commit(client, project_key):
    """Get the latest commit SHA from Dataiku project."""
    project = client.get_project(project_key)
    project_git = project.get_project_git()
    status = project_git.get_status()
    
    # Debug logging
    print(f"Git status type: {type(status)}")
    print(f"Git status content: {status}")
    
    # Handle both string and dict responses
    if isinstance(status, dict):
        return status['currentBranch']['commitId']
    elif isinstance(status, str):
        # If it's a string, it might be the commit ID directly
        return status.strip()
    else:
        raise ValueError(f"Unexpected git status type: {type(status)}")

def get_git_sha():
    """Get the current Git SHA."""
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
    return result.stdout.strip()

def sync_dataiku_to_git(client, project_key):
    """Push Dataiku changes to Git."""
    project = client.get_project(project_key).get_project_git()
    return project.push()

def main():
    try:
        dataiku_sha = get_dataiku_latest_commit(client_dev, DATAIKU_PROJECT_KEY)
        git_sha = get_git_sha()
        if dataiku_sha != git_sha:
            print(f"Dataiku commit SHA ({dataiku_sha}) doesn't match Git SHA ({git_sha})")
            sync_dataiku_to_git(client_dev, DATAIKU_PROJECT_KEY)
            print("Pushed Dataiku changes to Git. Restarting process.")
            sys.exit(0)  # Exit cleanly to allow the process to restart

        # Get the current commit ID
        commit_id = get_commit_id()
        bundle_id = generate_bundle_id(commit_id)
        release_notes = "Initial release"  # Optional release notes

        # Export bundle from DEV instance
        export_bundle(client_dev, DATAIKU_PROJECT_KEY, bundle_id, release_notes)
        print(f"Bundle exported with ID: {bundle_id}")

        # Download the exported bundle
        download_path = 'bundle.zip'
        download_export(client_dev, DATAIKU_PROJECT_KEY, bundle_id, download_path)
        print("Bundle downloaded.")

        # List imported bundles in Staging instance before activation
        imported_bundles_staging = list_imported_bundles(client_staging, DATAIKU_PROJECT_KEY)
        previous_bundle_id_staging = max(imported_bundles_staging['bundles'], key=lambda bundle: datetime.strptime(bundle['importState']['importedOn'], '%Y-%m-%dT%H:%M:%S.%f%z'))['bundleId']

        # Import bundle into Staging instance
        import_bundle(client_staging, bundle_id, DATAIKU_PROJECT_KEY, download_path)
        print(f"Bundle imported with ID: {bundle_id}")

        activate_bundle(client_staging, DATAIKU_PROJECT_KEY, bundle_id)
        print(f"Bundle activated with ID: {bundle_id}")

        # Run tests on Staging instance
        if run_tests(PYTHON_SCRIPT, DATAIKU_INSTANCE_STAGING_URL, DATAIKU_API_TOKEN_STAGING, DATAIKU_PROJECT_KEY):

            if RUN_TESTS_ONLY:
                print("Tests passed in staging. Skipping deployment to production.")
            else:
                print("Tests passed in staging. Deploying to production.")

                # List imported bundles in Prod instance before activation
                imported_bundles_prod = list_imported_bundles(client_prod, DATAIKU_PROJECT_KEY)
                previous_bundle_id_prod = max(imported_bundles_prod['bundles'], key=lambda bundle: datetime.strptime(bundle['importState']['importedOn'], '%Y-%m-%dT%H:%M:%S.%f%z'))['bundleId']

                # Import bundle into Prod instance
                import_bundle(client_prod, bundle_id, DATAIKU_PROJECT_KEY, download_path)
                print(f"Bundle imported with ID: {bundle_id}")

                # Activate bundle in Prod instance
                activate_bundle(client_prod, DATAIKU_PROJECT_KEY, bundle_id)
                print(f"Bundle activated with ID: {bundle_id}")

                # Run tests on Prod instance
                if run_tests(PYTHON_SCRIPT, DATAIKU_INSTANCE_PROD_URL, DATAIKU_API_TOKEN_PROD, DATAIKU_PROJECT_KEY):
                    print("Deployment and tests successful in production.")
                else:
                    print("Tests failed in production. Activating previous bundle.")
                    activate_bundle(client_prod, DATAIKU_PROJECT_KEY, previous_bundle_id_prod)
                    print(f"Previous bundle activated with ID: {previous_bundle_id_prod}")
                    sys.exit(1)
        else:
            print("Tests failed in staging. Activating previous bundle.")
            activate_bundle(client_staging, DATAIKU_PROJECT_KEY, previous_bundle_id_staging)
            print(f"Previous bundle activated with ID: {previous_bundle_id_staging}")
            sys.exit(1)

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()  # Print the stack trace
        sys.exit(1)

if __name__ == '__main__':
    main() 