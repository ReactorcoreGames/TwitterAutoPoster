import csv
import json
import os
import sys
import requests
import hmac
import hashlib
import base64
import urllib.parse
import time
import secrets
from datetime import datetime, timezone

# Constants
CSV_FILE = 'posts.csv'
STATE_FILE = 'state.json'
API_KEY = os.environ.get('TWITTER_API_KEY')
API_SECRET = os.environ.get('TWITTER_API_SECRET')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
REPO_ACTOR = os.environ.get('GITHUB_ACTOR', 'github-actions[bot]')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')


def create_oauth_signature(method, url, params, api_secret, token_secret):
    """Create OAuth 1.0a signature for Twitter API."""
    # Sort parameters
    sorted_params = sorted(params.items())
    
    # Create parameter string
    param_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
    
    # Create signature base string
    base_string = f"{method}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_string, safe='')}"
    
    # Create signing key
    signing_key = f"{urllib.parse.quote(api_secret, safe='')}&{urllib.parse.quote(token_secret, safe='')}"
    
    # Create signature
    signature = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()
    
    return signature

def create_oauth_header(method, url, params=None):
    """Create OAuth 1.0a authorization header for Twitter API."""
    if params is None:
        params = {}
    
    # OAuth parameters
    oauth_params = {
        'oauth_consumer_key': API_KEY,
        'oauth_nonce': secrets.token_urlsafe(32),
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(time.time())),
        'oauth_token': ACCESS_TOKEN,
        'oauth_version': '1.0'
    }
    
    # Combine OAuth params with request params for signature
    all_params = {**oauth_params, **params}
    
    # URL encode all parameters
    encoded_params = {k: urllib.parse.quote(str(v), safe='') for k, v in all_params.items()}
    
    # Create signature
    signature = create_oauth_signature(method, url, encoded_params, API_SECRET, ACCESS_TOKEN_SECRET)
    oauth_params['oauth_signature'] = signature
    
    # Create authorization header
    oauth_header = 'OAuth ' + ', '.join([f'{k}="{urllib.parse.quote(str(v), safe="")}"' for k, v in oauth_params.items()])
    
    return oauth_header

def main():
    # Validate environment variables
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        print("Error: Missing Twitter API credentials. Need:")
        print("- TWITTER_API_KEY")
        print("- TWITTER_API_SECRET") 
        print("- TWITTER_ACCESS_TOKEN")
        print("- TWITTER_ACCESS_TOKEN_SECRET")
        sys.exit(1)

    try:
        # Load CSV
        posts = load_posts()
        if not posts:
            print("No posts found in CSV.")
            sys.exit(0)

        # Load state
        state = load_state()
        last_index = state.get('last_row_index', -1)

        # Get next post
        next_index = (last_index + 1) % len(posts)
        post = posts[next_index]

        # Create post content
        content = create_post_content(post, next_index)

        # Post to Twitter
        post_to_twitter(content)

        # Update state
        update_state(next_index)

        # Commit changes back to repository
        commit_changes(next_index)

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def load_posts():
    """Load posts from CSV file."""
    try:
        with open(CSV_FILE, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        print(f"Error: {CSV_FILE} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        sys.exit(1)

def load_state():
    """Load state from JSON file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {STATE_FILE}. Starting from beginning.")
            return {}
        except Exception as e:
            print(f"Error reading state file: {str(e)}. Starting from beginning.")
            return {}
    return {}

def create_post_content(post, next_index):
    """Create formatted post content for Twitter."""
    try:
        title = post.get('title', '').strip()
        url = post.get('url', '').strip()
        hashtags = post.get('hashtags', '').strip()

        if not title or not url:
            print(f"Error: Missing title or URL in row {next_index + 2}")
            sys.exit(1)

        # Twitter has a 280 character limit
        content = f"{title}\n\n{url}\n\n{hashtags}"

        # Check for length constraints (Twitter's 280 char limit)
        if len(content) > 280:
            print(f"Warning: Post at row {next_index + 2} exceeds 280 chars. Trimming hashtags.")
            # Try to keep as many hashtags as possible
            max_hashtags_length = 280 - len(f"{title}\n\n{url}\n\n")
            if max_hashtags_length > 0:
                trimmed_hashtags = hashtags[:max_hashtags_length].strip()
                content = f"{title}\n\n{url}\n\n{trimmed_hashtags}"
            else:
                content = f"{title}\n\n{url}"

        print(f"Posting row {next_index + 2}: {content}")
        return content

    except Exception as e:
        print(f"Error creating post content: {str(e)}")
        sys.exit(1)

def post_to_twitter(content):
    """Post a text tweet using Twitter API v2 (free tier compatible)."""
    try:
        tweet_url = 'https://api.twitter.com/2/tweets'
        headers = {
            'Authorization': create_oauth_header('POST', tweet_url),
            'Content-Type': 'application/json'
        }

        print(f"Posting tweet: {content}")
        resp = requests.post(tweet_url, headers=headers, json={"text": content})
        resp.raise_for_status()

        tweet_id = resp.json().get('data', {}).get('id')
        print(f"Tweet posted successfully! Tweet ID: {tweet_id}")
        return True

    except requests.RequestException as e:
        print(f"Error posting to Twitter: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
            try:
                error_data = e.response.json()
                if 'errors' in error_data:
                    for error in error_data['errors']:
                        print(f"Twitter API Error: {error}")
            except Exception:
                pass
        sys.exit(1)

def update_state(next_index):
    """Update state file with last posted index."""
    try:
        new_state = {
            'last_row_index': next_index,
            'last_post_time': datetime.now(timezone.utc).isoformat()
        }
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_state, f, indent=2)
        print(f"State updated: {new_state}")
    except Exception as e:
        print(f"Error updating state file: {str(e)}")
        sys.exit(1)

def commit_changes(next_index):
    """Commit state changes back to repository."""
    try:
        commit_message = f'Update state.json after posting row {next_index + 2}'
        # Configure Git
        os.system(f'git config user.name "{REPO_ACTOR}"')
        os.system(f'git config user.email "{REPO_ACTOR}@users.noreply.github.com"')
        # Add, commit and push changes
        os.system(f'git add {STATE_FILE}')
        os.system(f'git commit -m "{commit_message}"')
        if GITHUB_TOKEN:
            # If token is available, use it for authentication
            origin_url = f'https://x-access-token:{GITHUB_TOKEN}@github.com/{os.environ.get("GITHUB_REPOSITORY")}.git'
            os.system(f'git remote set-url origin {origin_url}')
        # Push changes
        os.system('git push')
        print("Changes committed and pushed successfully")
    except Exception as e:
        print(f"Error committing changes: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()