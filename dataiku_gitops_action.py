import os
import sys
import subprocess
import dataiku
import logging
import requests
import http.client
import urllib3
from packaging import version

# Enable debug logging for the requests library
#logging.getLogger("requests").setLevel(logging.DEBUG)
#logging.basicConfig(level=logging.DEBUG)
#http.client.HTTPConnection.debuglevel = 1
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Access environment variables
DATAIKU_API_TOKEN = os.getenv('DATAIKU_API_TOKEN')
DATAIKU_INSTANCE_A_URL = os.getenv('DATAIKU_INSTANCE_A_URL')
DATAIKU_INSTANCE_B_URL = os.getenv('DATAIKU_INSTANCE_B_URL')
DATAIKU_PROJECT_KEY = os.getenv('DATAIKU_PROJECT_KEY')

# Create Dataiku clients
client_a = dataiku.DSSClient(DATAIKU_INSTANCE_A_URL, api_key=DATAIKU_API_TOKEN)
client_b = dataiku.DSSClient(DATAIKU_INSTANCE_B_URL, api_key=DATAIKU_API_TOKEN)
client_a._session.verify = False
client_b._session.verify = False

def create_bundle(client, project_key):
    project = client.get_project(project_key)
    bundle = project.create_bundle()
    return bundle.id

def download_bundle(client, project_key, bundle_id):
    project = client.get_project(project_key)
    bundle = project.get_bundle(bundle_id)
    bundle.download('bundle.zip')

def upload_bundle(client, project_key):
    project = client.get_project(project_key)
    bundle = project.upload_bundle('bundle.zip')
    return bundle.id

def run_tests(script_path, instance_url, project_key):
    try:
        result = subprocess.run(['python', script_path, instance_url, project_key], check=True, capture_output=True, text=True)
        print(result.stdout)
        return 'success'
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        return 'failed'

def undeploy_bundle(client, project_key, bundle_id):
    project = client.get_project(project_key)
    bundle = project.get_bundle(bundle_id)
    bundle.undeploy()

def main():
    try:
        # Step 1: Create bundle on Instance A
        bundle_id = create_bundle(client_a, DATAIKU_PROJECT_KEY)

        # Step 2: Download the bundle from Instance A
        download_bundle(client_a, DATAIKU_PROJECT_KEY, bundle_id)

        # Step 3: Upload the bundle to Instance B
        upload_bundle(client_b, DATAIKU_PROJECT_KEY)

        # Step 4: Run tests on Instance B
        test_status = run_tests('tests.py', DATAIKU_INSTANCE_B_URL, DATAIKU_PROJECT_KEY)

        if test_status == 'success':
            # Step 5: Promote to production
            upload_bundle(client_a, DATAIKU_PROJECT_KEY)

            # Step 6: Re-run tests on Instance A
            final_test_status = run_tests('tests.py', DATAIKU_INSTANCE_A_URL, DATAIKU_PROJECT_KEY)

            if final_test_status == 'success':
                print("Deployment and tests successful in production.")
            else:
                print("Tests failed in production. Undeploying bundle.")
                undeploy_bundle(client_a, DATAIKU_PROJECT_KEY, bundle_id)
                sys.exit(1)
        else:
            print("Tests failed in staging. Undeploying bundle.")
            undeploy_bundle(client_b, DATAIKU_PROJECT_KEY, bundle_id)
            sys.exit(1)

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 