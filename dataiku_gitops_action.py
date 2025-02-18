import hashlib
import os
import random
import string
import subprocess
import sys
from datetime import datetime

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

# Create Dataiku clients
client_dev = dataikuapi.DSSClient(DATAIKU_INSTANCE_DEV_URL, DATAIKU_API_TOKEN_DEV, no_check_certificate=True)
client_staging = dataikuapi.DSSClient(DATAIKU_INSTANCE_STAGING_URL, DATAIKU_API_TOKEN_STAGING, no_check_certificate=True)
client_prod = dataikuapi.DSSClient(DATAIKU_INSTANCE_PROD_URL, DATAIKU_API_TOKEN_PROD, no_check_certificate=True)

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

def import_bundle(client, project_key, fp):
    project = client.get_project(project_key)
    with open(fp, 'rb') as f:
        project.import_bundle_from_stream(f)

def activate_bundle(client, project_key, bundle_id):
    project = client.get_project(project_key)
    project.activate_bundle(bundle_id)

def list_imported_bundles(client, project_key):
    project = client.get_project(project_key)
    return project.list_imported_bundles()

def run_tests(script_path, instance_url, api_key, project_key):
    result = subprocess.run([sys.executable, script_path, instance_url, api_key, project_key], capture_output=True, text=True)
    return result.returncode == 0

def main():
    try:
        if RUN_TESTS_ONLY:
            print("Running tests only on staging.")
            # Run tests on Staging instance
            if run_tests('dataiku-gitops-demo-project/tests.py', DATAIKU_INSTANCE_STAGING_URL, DATAIKU_API_TOKEN_STAGING, DATAIKU_PROJECT_KEY):
                print("Tests passed in staging.")
            else:
                print("Tests failed in staging.")
                sys.exit(1)
        else:
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

            # Import bundle into Staging instance
            import_bundle(client_staging, DATAIKU_PROJECT_KEY, download_path)
            print(f"Bundle imported with ID: {bundle_id}")

            # List imported bundles in Staging instance before activation
            imported_bundles_staging = list_imported_bundles(client_staging, DATAIKU_PROJECT_KEY)
            previous_bundle_id_staging = max(imported_bundles_staging['bundles'], key=lambda bundle: datetime.strptime(bundle['importState']['importedOn'], '%Y-%m-%dT%H:%M:%S.%f%z'))['bundleId']

            # Run tests on Staging instance
            if run_tests('dataiku-gitops-demo-project/tests.py', DATAIKU_INSTANCE_STAGING_URL, DATAIKU_API_TOKEN_STAGING, DATAIKU_PROJECT_KEY):
                print("Tests passed in staging. Deploying to production.")
                # Import bundle into Prod instance
                import_bundle(client_prod, DATAIKU_PROJECT_KEY, download_path)
                print(f"Bundle imported with ID: {bundle_id}")

                # List imported bundles in Prod instance before activation
                imported_bundles_prod = list_imported_bundles(client_prod, DATAIKU_PROJECT_KEY)
                previous_bundle_id_prod = max(imported_bundles_prod['bundles'], key=lambda bundle: datetime.strptime(bundle['importState']['importedOn'], '%Y-%m-%dT%H:%M:%S.%f%z'))['bundleId']

                # Activate bundle in Prod instance
                activate_bundle(client_prod, DATAIKU_PROJECT_KEY, bundle_id)
                print(f"Bundle activated with ID: {bundle_id}")

                # Run tests on Prod instance
                if run_tests('dataiku-gitops-demo-project/tests.py', DATAIKU_INSTANCE_PROD_URL, DATAIKU_API_TOKEN_PROD, DATAIKU_PROJECT_KEY):
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
        sys.exit(1)

if __name__ == '__main__':
    main() 