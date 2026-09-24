# Cricket News Auto-Poster (Instagram)

Automatically fetches the latest cricket news, drops it into a branded
template image, and posts it to your Instagram page — fully free, running
on GitHub Actions.

## How it works

```
RSS feeds (Cricinfo/Cricbuzz) → new story found → Pillow builds a
branded image → image pushed to GitHub → Instagram Graph API
publishes it → story ID logged so it's never posted twice
```

Runs automatically every 4 hours via GitHub Actions (`.github/workflows/post_cricket_news.yml`).
You can also trigger it manually any time from the "Actions" tab.

---

## One-time setup (you have to do these — takes ~30-40 minutes)

### 1. Convert your Instagram to a Business/Creator account
- Instagram app → Settings → Account type → switch to **Professional Account** → **Business**

### 2. Link it to a Facebook Page
- Instagram app → Settings → Linked accounts → connect to a Facebook Page
  (create a free Facebook Page for your cricket account if you don't have one)

### 3. Create a Meta Developer App
- Go to https://developers.facebook.com/apps → **Create App** → type: "Business"
- In the app dashboard, add the **Instagram Graph API** product

### 4. Get your Instagram Business Account ID + Access Token
- Use Graph API Explorer (https://developers.facebook.com/tools/explorer/)
- Select your app, get a **User Access Token** with these permissions:
  `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`
- Call `GET /me/accounts` to find your Facebook Page ID
- Call `GET /{page-id}?fields=instagram_business_account` to get your **IG_USER_ID**
- Exchange the short-lived token for a **long-lived token** (60 days) using:
  `GET /oauth/access_token?grant_type=fb_exchange_token&client_id={app-id}&client_secret={app-secret}&fb_exchange_token={short-lived-token}`
- ⚠️ Long-lived tokens expire every 60 days — you'll need to refresh it
  periodically and update the GitHub secret (Meta doesn't currently offer
  a free way around this for personal apps)

### 5. Create a GitHub repository
- Create a new **public** repo (needs to be public so raw.githubusercontent.com
  links work for free — private repos need extra auth Instagram can't use)
- Push all the files in this project to that repo

### 6. Add your secrets to GitHub
Repo → Settings → Secrets and variables → Actions → New repository secret:
- `IG_USER_ID` = your Instagram Business Account ID from step 4
- `IG_ACCESS_TOKEN` = your long-lived access token from step 4

### 7. Add your branding
Drop these into the `assets/` folder (see `assets/README.txt`):
- `logo.png` — your page logo
- `background.jpg` — optional background photo
- `fonts/DejaVuSans-Bold.ttf` and `fonts/DejaVuSans.ttf` (or any fonts you like)

Then edit `config.py`:
- `PAGE_HANDLE` → your actual @handle
- `RSS_FEEDS` → add/remove cricket news sources
- colors, image size, etc. if you want a different look

### 8. Enable the workflow
- Push everything to GitHub → go to the **Actions** tab → enable workflows
- It will now run automatically every 4 hours
- To test immediately: Actions tab → "Post Cricket News to Instagram" → **Run workflow**

---

## Running locally (optional, to test before deploying)

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in real values
python -m dotenv run -- python main.py generate   # builds images in generated/
python -m dotenv run -- python main.py publish     # posts them (needs images already public)
```

Note: `publish` only works locally if `PUBLIC_RAW_BASE_URL` already points to
images that are live on GitHub — so local testing is mainly useful for
checking the `generate` step (does the template look right?).

---

## File overview

| File | Purpose |
|---|---|
| `config.py` | All settings: feeds, colors, fonts, keys |
| `fetch_news.py` | Pulls RSS feeds, filters out already-posted stories |
| `generate_image.py` | Builds the branded template image (Pillow) |
| `post_instagram.py` | Talks to the Instagram Graph API |
| `main.py` | Orchestrates generate → publish |
| `.github/workflows/post_cricket_news.yml` | The automation schedule |
| `data/posted_log.json` | Tracks which stories are already posted |

## Customizing the template

All the drawing logic is in `generate_image.py` — change fonts, colors,
add a scoreboard graphic, change layout, etc. It's plain Pillow code so
any change you can imagine in a normal image editor can be scripted here.

## Limitations to know about

- Free tier RSS feeds sometimes go down or change format — check the
  Actions tab occasionally for failed runs
- Instagram access tokens expire every 60 days (Meta's rule, not ours) —
  you'll need to regenerate and update the secret periodically
- This posts **images**, not reels. Turning this into video reels needs
  FFmpeg added to `generate_image.py` — ask and I'll build that next.
