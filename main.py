"""
Kingdom In Action — Fully Automated Instagram Reel Poster
Runs 24/7 on Railway/Render. Posts one reel at 8am and one at 7pm daily.
"""
import os, logging, time, traceback
from datetime import datetime
import pytz, schedule

from content_generator import generate_post
from video_generator   import generate_reel
from instagram_api     import post_reel_to_instagram

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger('KIA')

# ── Config from environment ────────────────────────────────────────────────────
TZ             = os.getenv('TIMEZONE', 'America/Los_Angeles')
TIME_MORNING   = os.getenv('POST_TIME_MORNING', '08:00')
TIME_EVENING   = os.getenv('POST_TIME_EVENING', '19:00')
ANTHROPIC_KEY  = os.getenv('ANTHROPIC_API_KEY', '')
IG_USER_ID     = os.getenv('INSTAGRAM_USER_ID', '')
IG_TOKEN       = os.getenv('INSTAGRAM_ACCESS_TOKEN', '')
CLD_CLOUD      = os.getenv('CLOUDINARY_CLOUD_NAME', '')
CLD_KEY        = os.getenv('CLOUDINARY_API_KEY', '')
CLD_SECRET     = os.getenv('CLOUDINARY_API_SECRET', '')

def validate_config():
    missing = []
    for name, val in [
        ('ANTHROPIC_API_KEY', ANTHROPIC_KEY),
        ('INSTAGRAM_USER_ID', IG_USER_ID),
        ('INSTAGRAM_ACCESS_TOKEN', IG_TOKEN),
        ('CLOUDINARY_CLOUD_NAME', CLD_CLOUD),
        ('CLOUDINARY_API_KEY', CLD_KEY),
        ('CLOUDINARY_API_SECRET', CLD_SECRET),
    ]:
        if not val:
            missing.append(name)
    if missing:
        raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")
    log.info("Config OK — all environment variables present")

# ── Post job ──────────────────────────────────────────────────────────────────
def post_job(slot: str):
    """Generate content + video and post to Instagram."""
    tz   = pytz.timezone(TZ)
    now  = datetime.now(tz)
    log.info(f"Starting {slot} post job — {now.strftime('%A %B %d %Y')}")

    try:
        # 1. Generate content via Claude API
        log.info("Generating content…")
        content = generate_post(slot=slot, api_key=ANTHROPIC_KEY)
        log.info(f"  Scripture: {content['verse_ref']}")
        log.info(f"  Theme: {content['theme']}")

        # 2. Generate the MP4 reel
        log.info("Generating video…")
        video_path = generate_reel(
            reference  = content['verse_ref'],
            verse_text = content['verse_text'],
        )
        log.info(f"  Video: {video_path}")

        # 3. Post to Instagram
        log.info("Posting to Instagram…")
        result = post_reel_to_instagram(
            video_path   = video_path,
            caption      = content['caption'],
            ig_user_id   = IG_USER_ID,
            access_token = IG_TOKEN,
            cld_cloud    = CLD_CLOUD,
            cld_key      = CLD_KEY,
            cld_secret   = CLD_SECRET,
        )
        log.info(f"Posted! Instagram media ID: {result}")

    except Exception as e:
        log.error(f"{slot} post FAILED: {e}")
        log.error(traceback.format_exc())

# ── Scheduler ─────────────────────────────────────────────────────────────────
def run():
    validate_config()

    log.info(f"Kingdom In Action Auto-Poster starting")
    log.info(f"Timezone : {TZ}")
    log.info(f"Morning  : {TIME_MORNING}")
    log.info(f"Evening  : {TIME_EVENING}")

    # Schedule in local timezone using schedule library
    schedule.every().day.at(TIME_MORNING).do(post_job, slot='Morning')
    schedule.every().day.at(TIME_EVENING).do(post_job, slot='Evening')

    log.info("Scheduler running — waiting for post times…")

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == '__main__':
    run()
