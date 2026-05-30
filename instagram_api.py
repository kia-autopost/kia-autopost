import os, time, logging, requests
import cloudinary, cloudinary.uploader

log = logging.getLogger('KIA.instagram')
GRAPH = 'https://graph.facebook.com/v21.0'


def _upload_to_cloudinary(video_path, cloud, key, secret):
    cloudinary.config(cloud_name=cloud, api_key=key, api_secret=secret)
    log.info("Uploading video to Cloudinary...")
    result = cloudinary.uploader.upload_large(
        video_path,
        resource_type='video',
        folder='kia_reels',
        public_id='daily_reel',
        overwrite=True,
    )
    url = result['secure_url']
    log.info(f"Cloudinary URL: {url}")
    return url


def _create_container(ig_user_id, access_token, video_url, caption):
    log.info("Creating Instagram media container...")
    resp = requests.post(
        f'{GRAPH}/{ig_user_id}/media',
        params={
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'share_to_feed': 'true',
            'access_token': access_token,
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
    log.info("Waiting for video to process...")
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
    log.info("Publishing reel...")
    resp = requests.post(
        f'{GRAPH}/{ig_user_id}/media_publish',
        params={'creation_id': container_id, 'access_token': access_token},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if 'error' in data:
        raise RuntimeError(f"Instagram publish error: {data['error']}")
    media_id = data['id']
    log.info(f"Published! Media ID: {media_id}")
    return media_id


def _refresh_token(access_token):
    app_id = os.getenv('META_APP_ID', '')
    app_secret = os.getenv('META_APP_SECRET', '')
    if not app_id or not app_secret:
        log.warning("META_APP_ID/META_APP_SECRET not set - skipping token refresh")
        return access_token
    try:
        resp = requests.get(
            f'{GRAPH}/oauth/access_token',
            params={
                'grant_type': 'fb_exchange_token',
                'client_id': app_id,
                'client_secret': app_secret,
                'fb_exchange_token': access_token,
            },
            timeout=15,
        )
        data = resp.json()
        if 'access_token' in data:
            log.info("Instagram token refreshed successfully")
            return data['access_token']
        log.warning(f"Token refresh failed: {data}")
    except Exception as e:
        log.warning(f"Token refresh error (non-fatal): {e}")
    return access_token


def post_reel_to_instagram(video_path, caption, ig_user_id, access_token, cld_cloud, cld_key, cld_secret):
    access_token = _refresh_token(access_token)
    video_url = _upload_to_cloudinary(video_path, cld_cloud, cld_key, cld_secret)
    container_id = _create_container(ig_user_id, access_token, video_url, caption)
    _wait_for_ready(container_id, access_token)
    media_id = _publish(ig_user_id, access_token, container_id)
    try:
        os.remove(video_path)
    except Exception:
        pass
    return media_id
