import os
import requests
import sys
import time
import subprocess

# Environment variables
DATAIKU_API_TOKEN = os.getenv('DATAIKU_API_TOKEN')
DATAIKU_INSTANCE_A_URL = os.getenv('DATAIKU_INSTANCE_A_URL')
DATAIKU_INSTANCE_B_URL = os.getenv('DATAIKU_INSTANCE_B_URL')
DATAIKU_PROJECT_KEY = os.getenv('DATAIKU_PROJECT_KEY')

# Headers for API requests
headers = {
    'Authorization': f'Bearer {DATAIKU_API_TOKEN}',
    'Content-Type': 'application/json'
}

def create_bundle(instance_url, project_key):
    url = f'{instance_url}/public/api/projects/{project_key}/bundles'
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json()['id']

def download_bundle(instance_url, project_key, bundle_id):
    url = f'{instance_url}/public/api/projects/{project_key}/bundles/{bundle_id}/download'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    with open('bundle.zip', 'wb') as f:
        f.write(response.content)

def upload_bundle(instance_url, project_key):
    url = f'{instance_url}/public/api/projects/{project_key}/bundles/upload'
    with open('bundle.zip', 'rb') as f:
        files = {'file': f}
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
    return response.json()['id']

def run_tests(script_path, instance_url, project_key):
    try:
        result = subprocess.run(['python', script_path, instance_url, project_key], check=True, capture_output=True, text=True)
        print(result.stdout)
        return 'success'
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        return 'failed'

def undeploy_bundle(instance_url, project_key, bundle_id):
    url = f'{instance_url}/public/api/projects/{project_key}/bundles/{bundle_id}/undeploy'
    response = requests.post(url, headers=headers)
    response.raise_for_status()

def main():
    try:
        # Step 1: Create bundle on Instance A
        bundle_id = create_bundle(DATAIKU_INSTANCE_A_URL, DATAIKU_PROJECT_KEY)

        # Step 2: Download the bundle from Instance A
        download_bundle(DATAIKU_INSTANCE_A_URL, DATAIKU_PROJECT_KEY, bundle_id)

        # Step 3: Upload the bundle to Instance B
        upload_bundle(DATAIKU_INSTANCE_B_URL, DATAIKU_PROJECT_KEY)

        # Step 4: Run tests on Instance B
        test_status = run_tests('tests.py', DATAIKU_INSTANCE_B_URL, DATAIKU_PROJECT_KEY)

        if test_status == 'success':
            # Step 5: Promote to production
            upload_bundle(DATAIKU_INSTANCE_A_URL, DATAIKU_PROJECT_KEY)

            # Step 6: Re-run tests on Instance A
            final_test_status = run_tests('tests.py', DATAIKU_INSTANCE_A_URL, DATAIKU_PROJECT_KEY)

            if final_test_status == 'success':
                print("Deployment and tests successful in production.")
            else:
                print("Tests failed in production. Undeploying bundle.")
                undeploy_bundle(DATAIKU_INSTANCE_A_URL, DATAIKU_PROJECT_KEY, bundle_id)
                sys.exit(1)
        else:
            print("Tests failed in staging. Undeploying bundle.")
            undeploy_bundle(DATAIKU_INSTANCE_B_URL, DATAIKU_PROJECT_KEY, bundle_id)
            sys.exit(1)

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 