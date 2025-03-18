# Spotify to YouTube Music Downloader

This application allows you to connect to your Spotify account, browse your saved playlists, and download the tracks from YouTube Music.

## Prerequisites

- Python 3.7 or newer
- A Spotify Developer account and API credentials
- FFmpeg installed on your system (for audio conversion)

## Setup Instructions

### 1. Install FFmpeg

#### macOS (using Homebrew):
```bash
brew install ffmpeg
```

### 2. Set Up a Spotify Developer Application

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Log in with your Spotify account
3. Click "Create an App"
4. Fill in the app name and description
5. Once created, note your Client ID and Client Secret
6. Click "Edit Settings" and add `http://localhost:8888/callback` as a Redirect URI
7. Save your changes

### 3. Set Up Python Environment

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

## Usage

1. Ensure your virtual environment is activated:
```bash
source venv/bin/activate
```

2. Run the application with your Spotify credentials:
```bash
python spotify_youtube_downloader.py --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
```

3. A web browser will open asking you to authorize the application with your Spotify account. Log in and approve.

4. Once authenticated, you'll see a list of your Spotify playlists in the terminal.

5. Enter the number(s) of the playlist(s) you want to download, separated by commas, or type 'all' to download all playlists.

6. The application will search for each track on YouTube Music and download them in MP3 format.

7. Downloaded tracks will be organized by artist in the specified download directory (default: ~/Music/SpotifyDownloads).

## Additional Options

- Change the download directory:
```bash
python spotify_youtube_downloader.py --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET --download-dir "/custom/path"
```

## Troubleshooting

- **Authentication Issues**: Make sure your Client ID, Client Secret, and Redirect URI are configured correctly in the Spotify Developer Dashboard.
- **Download Failures**: Some tracks might not be found on YouTube Music. These will be noted in the console output.
- **FFmpeg Errors**: Ensure FFmpeg is installed and in your system PATH.

## Legal Considerations

This tool is for personal use only. Please respect copyright laws and terms of service for both Spotify and YouTube Music. This application should only be used to download content you have the right to access.
