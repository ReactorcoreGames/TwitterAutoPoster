import csv
import json
import os
import sys
import requests
import re
import hmac
import hashlib
import base64
import urllib.parse
import time
import secrets
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from io import BytesIO
from PIL import Image

# Constants
CSV_FILE = 'posts.csv'
STATE_FILE = 'state.json'
API_KEY = os.environ.get('TWITTER_API_KEY')
API_SECRET = os.environ.get('TWITTER_API_SECRET')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
REPO_ACTOR = os.environ.get('GITHUB_ACTOR', 'github-actions[bot]')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

# Twitter image size limit (in bytes) - 5MB for images
MAX_IMAGE_SIZE = 4.5 * 1024 * 1024  # 4.5MB to be safe

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

def get_webpage_metadata(url):
    """Fetch webpage and extract metadata for Twitter card."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Initialize metadata with defaults
        metadata = {
            'title': soup.title.text.strip() if soup.title else url,
            'description': '',
            'image': None
        }
        
        # Try to get OpenGraph metadata (Twitter prefers these)
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            metadata['title'] = og_title['content']
        
        og_description = soup.find('meta', property='og:description')
        if og_description and og_description.get('content'):
            metadata['description'] = og_description['content']
        
        # Try different image meta tags
        image_url = None
        
        # 1. Twitter card image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            image_url = twitter_image['content']
        
        # 2. OpenGraph image
        if not image_url:
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                image_url = og_image['content']
        
        # 3. Regular image meta
        if not image_url:
            image_meta = soup.find('meta', attrs={'name': 'image'})
            if image_meta and image_meta.get('content'):
                image_url = image_meta['content']
        
        # Make sure image URL is absolute
        if image_url:
            metadata['image'] = urljoin(url, image_url)
        
        return metadata
        
    except Exception as e:
        print(f"Warning: Error fetching metadata for {url}: {str(e)}")
        return {
            'title': url,
            'description': '',
            'image': None
        }

def resize_image_if_needed(image_data, max_size=MAX_IMAGE_SIZE, quality=85):
    """Resize image if it exceeds the maximum size limit."""
    try:
        original_size = len(image_data)
        print(f"Original image size: {original_size} bytes")
        
        if original_size <= max_size:
            print("Image is within size limit, no resizing needed")
            return image_data
        
        print(f"Image exceeds {max_size} bytes, resizing...")
        
        # Open image with PIL
        img = Image.open(BytesIO(image_data))
        
        # Convert to RGB if necessary (for JPEG output)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create a white background for transparent images
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Try different strategies to reduce file size
        strategies = [
            # Strategy 1: Reduce quality
            {'resize_factor': 1.0, 'quality': 75},
            {'resize_factor': 1.0, 'quality': 65},
            {'resize_factor': 1.0, 'quality': 55},
            
            # Strategy 2: Resize image while maintaining quality
            {'resize_factor': 0.9, 'quality': 85},
            {'resize_factor': 0.8, 'quality': 85},
            {'resize_factor': 0.7, 'quality': 80},
            {'resize_factor': 0.6, 'quality': 80},
            {'resize_factor': 0.5, 'quality': 75},
            
            # Strategy 3: Aggressive resizing with lower quality
            {'resize_factor': 0.4, 'quality': 70},
            {'resize_factor': 0.3, 'quality': 65},
        ]
        
        for strategy in strategies:
            # Create a copy of the image for this attempt
            temp_img = img.copy()
            
            # Resize if needed
            if strategy['resize_factor'] < 1.0:
                new_width = int(temp_img.width * strategy['resize_factor'])
                new_height = int(temp_img.height * strategy['resize_factor'])
                temp_img = temp_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"Resized to {new_width}x{new_height} (factor: {strategy['resize_factor']})")
            
            # Save with specified quality
            output = BytesIO()
            temp_img.save(output, format='JPEG', quality=strategy['quality'], optimize=True)
            result_data = output.getvalue()
            result_size = len(result_data)
            
            print(f"Attempt with quality {strategy['quality']}, resize {strategy['resize_factor']}: {result_size} bytes")
            
            if result_size <= max_size:
                print(f"Successfully reduced image size from {original_size} to {result_size} bytes")
                return result_data
        
        # If all strategies failed, return the last attempt (smallest size)
        print(f"Warning: Could not reduce image below {max_size} bytes. Using smallest version ({result_size} bytes)")
        return result_data
        
    except Exception as e:
        print(f"Error resizing image: {str(e)}")
        # Return original data if resizing fails
        return image_data

def upload_media_to_twitter(image_url):
    """Upload an image to Twitter and return the media_id."""
    try:
        print(f"Downloading image from: {image_url}")
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        original_image_data = response.content
        original_content_type = response.headers.get('Content-Type', 'image/jpeg')
        
        print(f"Downloaded image (size: {len(original_image_data)} bytes, type: {original_content_type})")
        
        # Resize image if it's too large
        processed_image_data = resize_image_if_needed(original_image_data)
        
        print(f"Uploading image to Twitter (final size: {len(processed_image_data)} bytes)")
        
        # Create OAuth header for media upload
        upload_url = 'https://upload.twitter.com/1.1/media/upload.json'
        headers = {
            'Authorization': create_oauth_header('POST', upload_url),
        }
        
        files = {
            'media': ('image.jpg', processed_image_data, 'image/jpeg')
        }
        
        upload_response = requests.post(upload_url, headers=headers, files=files)
        upload_response.raise_for_status()
        
        media_data = upload_response.json()
        media_id = media_data.get('media_id_string')
        print(f"Image uploaded successfully, media_id: {media_id}")
        
        return media_id
        
    except Exception as e:
        print(f"Error uploading image to Twitter: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return None

def extract_first_url(content):
    """Extract the first URL from the content, or None if not found."""
    url_pattern = re.compile(r'https?://\S+')
    match = url_pattern.search(content)
    if match:
        return match.group(0)
    return None

def post_to_twitter(content):
    """Post content to Twitter with proper formatting."""
    try:
        # Prepare basic tweet data
        tweet_data = {
            "text": content
        }

        # Try to add media (image) from the first URL for better engagement
        main_url = extract_first_url(content)
        if main_url:
            print(f"Fetching metadata for {main_url}")
            metadata = get_webpage_metadata(main_url)
            
            # Try to upload an image if one is found
            if metadata['image']:
                print(f"Found image for tweet: {metadata['image']}")
                media_id = upload_media_to_twitter(metadata['image'])
                if media_id:
                    tweet_data["media"] = {
                        "media_ids": [media_id]
                    }
                else:
                    print("Failed to upload image, posting without media")
            else:
                print("No image found for this URL")

        # Post the tweet using OAuth 1.0a
        tweet_url = 'https://api.twitter.com/2/tweets'
        headers = {
            'Authorization': create_oauth_header('POST', tweet_url),
            'Content-Type': 'application/json'
        }

        print(f"Posting tweet: {content}")
        resp = requests.post(tweet_url, headers=headers, json=tweet_data)
        resp.raise_for_status()
        
        response_data = resp.json()
        tweet_id = response_data.get('data', {}).get('id')
        print(f"Tweet posted successfully! Tweet ID: {tweet_id}")
        return True

    except requests.RequestException as e:
        print(f"Error posting to Twitter: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
            
            # Check for specific Twitter API errors
            try:
                error_data = e.response.json()
                if 'errors' in error_data:
                    for error in error_data['errors']:
                        print(f"Twitter API Error: {error}")
            except:
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