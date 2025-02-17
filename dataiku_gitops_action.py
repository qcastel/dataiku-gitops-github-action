import os
import sys
import subprocess
import dataikuapi
import urllib3

# Disable warnings for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Access environment variables
DATAIKU_API_TOKEN = os.getenv('DATAIKU_API_TOKEN')
DATAIKU_INSTANCE_A_URL = os.getenv('DATAIKU_INSTANCE_A_URL')
DATAIKU_INSTANCE_B_URL = os.getenv('DATAIKU_INSTANCE_B_URL')
DATAIKU_PROJECT_KEY = os.getenv('DATAIKU_PROJECT_KEY')

# Create Dataiku clients
client_a = dataikuapi.DSSClient(DATAIKU_INSTANCE_A_URL, DATAIKU_API_TOKEN)
client_b = dataikuapi.DSSClient(DATAIKU_INSTANCE_B_URL, DATAIKU_API_TOKEN)
client_a._session.verify = False
client_b._session.verify = False

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
        # Export bundle from instance A
        bundle_id = "my_bundle"  # Replace with your desired bundle ID
        release_notes = "Initial release"  # Optional release notes
        export_bundle(client_a, DATAIKU_PROJECT_KEY, bundle_id, release_notes)
        print(f"Bundle exported with ID: {bundle_id}")

        # Download the exported bundle
        download_path = 'bundle.zip'
        download_export(client_a, DATAIKU_PROJECT_KEY, bundle_id, download_path)
        print("Bundle downloaded.")

        # Import bundle into instance B
        import_bundle(client_b, DATAIKU_PROJECT_KEY, download_path)
        print(f"Bundle imported with ID: {bundle_id}")

        # Run tests on instance B
        if run_tests('dataiku-gitops-demo-project/tests.py', DATAIKU_INSTANCE_B_URL, DATAIKU_PROJECT_KEY):
            print("Tests passed in staging. Deploying to production.")
            # Run tests on instance A
            if run_tests('dataiku-gitops-demo-project/tests.py', DATAIKU_INSTANCE_A_URL, DATAIKU_PROJECT_KEY):
                print("Deployment and tests successful in production.")
            else:
                print("Tests failed in production. Undeploying project.")
                undeploy_project(client_a, DATAIKU_PROJECT_KEY, bundle_id)
                sys.exit(1)
        else:
            print("Tests failed in staging. Undeploying project.")
            undeploy_project(client_b, DATAIKU_PROJECT_KEY, bundle_id)
            sys.exit(1)

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 