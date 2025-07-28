# Genshin_bot
## A genshin companion bot for Whatsapp 

### Environmental Variables

___(For local/vps deployment rename [.env.sample](.env.sample) to .env and edit with your variable)___.
The sample also contains a brief explanation of what each environmental variable does.


### Deployment:
**With Docker:**
- Install Docker
   - `apt install docker.io -y` _(Debian based systems)_
   - `dnf install docker -y` _(Fedora) (Replace with yum for Centos & other Red hat distros)_
- Clone repository to your preferred location 
- Ensure you are in the proper directory with Dockerfile and .env file present
- Run:
   - `docker build . -t gi_wa`
   - `docker run gi_wa --name qiqi`

**Without Docker:**
- Install required dependencies check the [Dockerfile](Dockerfile) for inspiration.
- python3.10, ffmpeg are required
- Install additional python dependencies with `pip3 install requirements.txt` (Possibly after setting up a venv)
- Run:
  - `bash run.sh` _To start bot normally_
  - `bash srun.sh` _To start bot silently_
  - 

### Commands:
```
start - Hi!
enka - Fetch enka cards
weapon - Fetch weapon details
artifact - Fetch artifact details
meme - Get a random meme
codes - Get lastest giftcodes
events - Get current and upcoming events
sanitize - Sanitize link or message
rchallenge - Get a random boss challenge card
ping - Check if bot is alive
bash - [Dev.] Run bash commands
eval - [Dev.] Evaluate python commands
ban - [Owner] prevent a user from using bot
unban - [Owner] unban a user
sudo - [Owner] Promote a user to sudoers
rss - [Owner | Sudo] Setup bot to auto post RSS feeds
update - [Owner | Sudo] Update & restarts bot
restart - [Owner | Sudo] Restarts bot
disable - [Owner | Sudo] Disable bot replies in a GC
enable - [Owner | Sudo] Enable bot replies in a GC
pause - [Owner] Pauses bot
```
### Features:
- Fetch Character builds from enka 
- Fetch weapon/artifacts info
- Get giftcodes automatically sent to chat
- View Recent & Upcoming events 
- Get recent genshin official posts from hoyolab through rss with [hoyolab-rss-feeds](https://github.com/c3kay/hoyolab-rss-feeds)

__(More Coming Soon)__
