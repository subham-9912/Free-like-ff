import requests
import json
import base64
import time


GITHUB_TOKEN = ""
REPO = ""

TOKENS_FILE = "tokens.json"
IND_FILE = "token_ind.json"
BR_FILE = "token_br.json"
AG_FILE = "token_ag.json"


TOKENS_URL = f"https://raw.githubusercontent.com/{REPO}/{TOKENS_FILE}"
JWT_API_URL = "https://wotaxxdev-api.vercel.app/access-jwt?access_token={}"



def get_github_file_sha(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("sha")
    return None

def update_github_file(path, content, message):
    sha = get_github_file_sha(path)
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    data = {
        "message": message,
        "content": content_base64
    }
    if sha:
        data["sha"] = sha
        
    response = requests.put(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        print(f"Successfully updated {path} (Content starts with: {content[:50]}...)")
    else:
        print(f"Failed to update {path}: {response.status_code} - {response.text}")

def categorize_region(region):
    region = region.upper()
    if region == "INDIA":
        return "IND"
    if region in ["BRAZIL", "US", "NORTHAMERICA", "SAC", "BR", "NA"]:
        return "BR"
    return "AG"


def update_tokens():
    cache_buster = f"?t={int(time.time())}"
    fetch_url = TOKENS_URL + cache_buster
    print(f"Fetching tokens from {fetch_url}...")
    try:
        response = requests.get(fetch_url)
        if response.status_code != 200:
            print(f"Failed to fetch tokens.json: {response.status_code}")
            return
        
        access_tokens = response.json()
        if not isinstance(access_tokens, list):
            print("tokens.json is not a list")
            return
    except Exception as e:
        print(f"Error fetching/parsing tokens.json: {e}")
        return

    ind_tokens = []
    br_tokens = []
    ag_tokens = []

    print(f"Processing {len(access_tokens)} tokens...")
    for acc_token in access_tokens:
        try:
            jwt_url = JWT_API_URL.format(acc_token)
            resp = requests.get(jwt_url)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    token_jwt = data.get("token")
                    region = data.get("region", "UNKNOWN")
                    
                    token_entry = {"token": token_jwt}
                    
                    cat = categorize_region(region)
                    if cat == "IND":
                        ind_tokens.append(token_entry)
                    elif cat == "BR":
                        br_tokens.append(token_entry)
                    else:
                        ag_tokens.append(token_entry)
                    
                    print(f"Success: {region} -> {cat}")
                else:
                    print(f"API Error for token {acc_token[:10]}...: {data.get('message') or data.get('status')}")
            else:
                print(f"HTTP Error for token {acc_token[:10]}...: {resp.status_code}")
        except Exception as e:
            print(f"Exception processing token: {e}")
            
    if ind_tokens or br_tokens or ag_tokens:
        print(f"Update summary: IND={len(ind_tokens)}, BR={len(br_tokens)}, AG={len(ag_tokens)}")
        update_github_file(IND_FILE, json.dumps(ind_tokens, indent=4), "Update IND tokens")
        update_github_file(BR_FILE, json.dumps(br_tokens, indent=4), "Update BR tokens")
        update_github_file(AG_FILE, json.dumps(ag_tokens, indent=4), "Update AG tokens")
    else:
        print("No valid tokens were retrieved from the API. Skipping GitHub update to prevent clearing existing tokens.")

if __name__ == "__main__":
    while True:
        try:
            update_tokens()
            print("Next update in 5 hours...")
            time.sleep(5 * 60 * 60)
        except KeyboardInterrupt:
            print("Exiting...")
            break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(60) 
