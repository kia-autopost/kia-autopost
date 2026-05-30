"""
Kingdom In Action — Fully Automated Instagram Reel Poster
Runs 24/7 on Railway. Posts one reel at 8am and one at 7pm daily (LA time).
"""
import os, logging, time, traceback
from datetime import datetime
import pytz

from content_generator import generate_post
from video_generator   import generate_reel
from instagram_api     import post_reel_to_instagram

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger('KIA')

TZ           = os.getenv('TIMEZONE', 'America/Los_Angeles')
TIME_MORNING = os.getenv('POST_TIME_MORNING', '08:00')
TIME_EVENING = os.getenv('POST_TIME_EVENING', '19:00')
ANTHROPIC_KEY = os.getenv('ANTHROPIC_API_KEY', '')
IG_USER_ID    = os.getenv('INSTAGRAM_USER_ID', '')
IG_TOKEN      = os.getenv('INSTAGRAM_ACCESS_TOKEN', '')
CLD_CLOUD     = os.getenv('CLOUDINARY_CLOUD_NAME', '')
CLD_KEY       = os.getenv('CLOUDINARY_API_KEY', '')
CLD_SECRET    = os.getenv('CLOUDINARY_API_SECRET', '')

def validate_config():
        missing = [n for n,v in [('ANTHROPIC_API_KEY',ANTHROPIC_KEY),('INSTAGRAM_USER_ID',IG_USER_ID),('INSTAGRAM_ACCESS_TOKEN',IG_TOKEN),('CLOUDINARY_CLOUD_NAME',CLD_CLOUD),('CLOUDINARY_API_KEY',CLD_KEY),('CLOUDINARY_API_SECRET',CLD_SECRET)] if not v]
        if missing: raise EnvironmentError(f"Missing env vars: {', '.join(missing)}")
                log.info("Config OK — all environment variables present")

def post_job(slot: str):
        tz = pytz.timezone(TZ)
    now = datetime.now(tz)
    log.info(f"Starting {slot} post job — {now.strftime('%A %B %d %Y')}")
    try:
                log.info("Generating content…")
                content = generate_post(slot=slot, api_key=ANTHROPIC_KEY)
                log.info(f"  Scripture: {content['verse_ref']}")
                log.info("Generating video…")
                video_path = generate_reel(reference=content['verse_ref'], verse_text=content['verse_text'])
                log.info("Posting to Instagram…")
                result = post_reel_to_instagram(video_path=video_path, caption=content['caption'], ig_user_id=IG_USER_ID, access_token=IG_TOKEN, cld_cloud=CLD_CLOUD, cld_key=CLD_KEY, cld_secret=CLD_SECRET)
                log.info(f"Posted! Instagram media ID: {result}")
except Exception as e:
        log.error(f"{slot} post FAILED: {e}")
        log.error(traceback.format_exc())

def _matches(t):
        now = datetime.now(pytz.timezone(TZ))
    h, m = map(int, t.split(':'))
    return now.hour == h and now.minute == m

def run():
        validate_config()
    log.info("Kingdom In Action Auto-Poster starting")
    log.info(f"Timezone : {TZ}")
    log.info(f"Morning  : {TIME_MORNING}")
    log.info(f"Evening  : {TIME_EVENING}")
    log.info("Scheduler running — checking every 30s in LA time…")
    posted_m = posted_e = False
    while True:
                now = datetime.now(pytz.timezone(TZ))
                if now.hour == 0 and now.minute == 0: posted_m = posted_e = False
                            if not posted_m and _matches(TIME_MORNING): posted_m = True; post_job('Morning')
                                        if not posted_e and _matches(TIME_EVENING): posted_e = True; post_job('Evening')
                                                    time.sleep(30)

if __name__ == '__main__':
        run()
