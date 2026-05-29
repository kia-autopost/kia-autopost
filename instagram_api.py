"""
Instagram API — uploads the reel video to Cloudinary (for a public URL),
then posts it to Instagram as a Reel via the Graph API.
"""
import os, time, logging, requests
import cloudinary, cloudinary.uploader

log = logging.getLogger('KIA.instagram')

GRAPH = 'https://graph.facebook.com/v21.0'

def _upload_to_cloudinary(video_path, cloud, key, secret):
    """Upload video to Cloudinary and return a public URL."""
    cloudinary.config(cloud_name=cloud, api_key=key, api_secret=secret)
    log.info("Uploading video to Cloudinary…")
    result = cloudinary.uploader.upload_large(
        video_path,
        resource_type = 'video',
        folder        = 'kia_reels',
        overwrite     = True,
    )
    url = result['secure_url']
    log.info(f"Cloudinary URL: {url}")
    return url

def _create_container(ig_user_id, access_token, video_url, caption):
    """Create an Instagram media container for the Reel."""
    log.info("Creating Instagram media container…")
    resp = requests.post(
        f'{GRAPH}/{ig_user_id}/media',
        params={
            'media_type'    : 'REELS',
            'video_url'     : video_url,
            'caption'       : caption,
            'share_to_feed' : 'true',
            'access_token'  : access_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if 'error' in data:
        raise RuntimeError(f"Instagram container error: {data['error']}")
    container_id = data['id']
    log.info(f"Container ID: {container_id}")
    return container_id

def _wait_for_ready(container_id, access_token, max_wait=300):
    """Poll until the video container is ready to publish."""
    log.info("Waiting for video to process…")
    start = time.time()
    while time.time() - start < max_wait:
        resp = requests.get(
            f'{GRAPH}/{container_id}',
            params={'fields': 'status_code', 'access_token': access_token},
            timeout=15,
        )
        resp.raise_for_status()
        status = resp.json().get('status_code', '')
        log.info(f"  Status: {status}")
        if status == 'FINISHED':
            return
        if status == 'ERROR':
            raise RuntimeError("Instagram video processing failed")
        time.sleep(10)
    raise TimeoutError("Instagram video processing timed out")

def _publish(ig_user_id, access_token, container_id):
    """Publish the container as a Reel."""
    log.info("Publishing reel…")
    resp = requests.post(
        f'{GRAPH}/{ig_user_id}/media_publish',
        params={
            'creation_id'  : container_id,
            'access_token' : access_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if 'error' in data:
        raise RuntimeError(f"Instagram publish error: {data['error']}")
    media_id = data['id']
    log.info(f"Published! Media ID: {media_id}")
    return media_id

def _refresh_token_if_needed(access_token):
    """
    Instagram long-lived tokens last 60 days.
    This refreshes the token and returns the new one.
    Call this periodically — we do it on every post to keep it fresh.
    """
    try:
        resp = requests.get(
            'https://graph.instagram.com/refresh_access_token',
            params={
                'grant_type'   : 'ig_refresh_token',
                'access_token' : access_token,
            },
            timeout=15,
        )
        data = resp.json()
        if 'access_token' in data:
            log.info("Instagram token refreshed successfully")
            return data['access_token']
    except Exception as e:
        log.warning(f"Token refresh failed (non-fatal): {e}")
    return access_token

# ── Public function ────────────────────────────────────────────────────────────
def post_reel_to_instagram(
    video_path   : str,
    caption      : str,
    ig_user_id   : str,
    access_token : str,
    cld_cloud    : str,
    cld_key      : str,
    cld_secret   : str,
) -> str:
    """
    Full pipeline: upload video → create container → wait → publish.
    Returns the published Instagram media ID.
    """
    # Keep token fresh
    access_token = _refresh_token_if_needed(access_token)

    # Upload video to get public URL
    video_url = _upload_to_cloudinary(video_path, cld_cloud, cld_key, cld_secret)

    # Create container
    container_id = _create_container(ig_user_id, access_token, video_url, caption)

    # Wait for processing
    _wait_for_ready(container_id, access_token)

    # Publish
    media_id = _publish(ig_user_id, access_token, container_id)

    # Clean up local video file
    try:
        os.remove(video_path)
    except Exception:
        pass

    return media_id
