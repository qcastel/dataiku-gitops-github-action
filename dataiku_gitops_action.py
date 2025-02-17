import os
import sys
import subprocess
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

# Create Dataiku clients
client_dev = dataikuapi.DSSClient(DATAIKU_INSTANCE_DEV_URL, DATAIKU_API_TOKEN_DEV, no_check_certificate=True)
client_staging = dataikuapi.DSSClient(DATAIKU_INSTANCE_STAGING_URL, DATAIKU_API_TOKEN_STAGING, no_check_certificate=True)
client_prod = dataikuapi.DSSClient(DATAIKU_INSTANCE_PROD_URL, DATAIKU_API_TOKEN_PROD, no_check_certificate=True)

def export_bundle(client, project_key, bundle_id, release_notes=None):
    project = client.get_project(project_key)
    project.export_bundle(bundle_id, release_notes)
    return bundle_id

def download_export(client, project_key, bundle_id, path):
    project = client.get_project(project_key)
    project.download_exported_bundle_archive_to_file(bundle_id, path)

def import_bundle(client, project_key, archive_path):
    project = client.get_project(project_key)
    project.import_bundle_from_archive(archive_path)

def undeploy_project(client, project_key, bundle_id):
    project = client.get_project(project_key)
    project.delete_exported_bundle(bundle_id)

def run_tests(script_path, instance_url, project_key):
    result = subprocess.run([sys.executable, script_path, instance_url, project_key], capture_output=True, text=True)
    return result.returncode == 0

def main():
    try:
        # Export bundle from DEV instance
        bundle_id = "my_bundle"  # Replace with your desired bundle ID
        release_notes = "Initial release"  # Optional release notes
        export_bundle(client_dev, DATAIKU_PROJECT_KEY, bundle_id, release_notes)
        print(f"Bundle exported with ID: {bundle_id}")

        # Download the exported bundle
        download_path = 'bundle.zip'
        download_export(client_dev, DATAIKU_PROJECT_KEY, bundle_id, download_path)
        print("Bundle downloaded.")

        # Import bundle into Staging instance
        import_bundle(client_staging, DATAIKU_PROJECT_KEY, download_path)
        print(f"Bundle imported with ID: {bundle_id}")

        # Run tests on Staging instance
        if run_tests('dataiku-gitops-demo-project/tests.py', DATAIKU_INSTANCE_STAGING_URL, DATAIKU_PROJECT_KEY):
            print("Tests passed in staging. Deploying to production.")
            # Import bundle into Prod instance
            import_bundle(client_prod, DATAIKU_PROJECT_KEY, download_path)
            print(f"Bundle imported with ID: {bundle_id}")

            # Run tests on Prod instance
            if run_tests('dataiku-gitops-demo-project/tests.py', DATAIKU_INSTANCE_PROD_URL, DATAIKU_PROJECT_KEY):
                print("Deployment and tests successful in production.")
            else:
                print("Tests failed in production. Undeploying project.")
                undeploy_project(client_prod, DATAIKU_PROJECT_KEY, bundle_id)
                sys.exit(1)
        else:
            print("Tests failed in staging. Undeploying project.")
            undeploy_project(client_staging, DATAIKU_PROJECT_KEY, bundle_id)
            sys.exit(1)

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 