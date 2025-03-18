#!/usr/bin/env python3

import os
import json
import webbrowser
from urllib.parse import urlparse, parse_qs
import base64
import time
from typing import List, Dict, Any, Optional
import argparse
import re
import sys
import threading

# Third-party imports - you'll need to install these in your venv
import requests
from ytmusicapi import YTMusic
from yt_dlp import YoutubeDL
from flask import Flask, request
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

# Initialize rich console for better terminal output
console = Console()

# Flask app for handling Spotify OAuth callback
app = Flask(__name__)
authorization_code = None
redirect_uri = "http://localhost:8888/callback"

class SpotifyYouTubeDownloader:
    def __init__(self, client_id: str, client_secret: str, download_dir: str = "./downloads"):
        """
        Initialize the Spotify to YouTube Music downloader.
        
        Args:
            client_id: Spotify API client ID
            client_secret: Spotify API client secret
            download_dir: Directory to save downloaded tracks to
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.download_dir = os.path.expanduser(download_dir)
        self.sp = None
        self.ytmusic = YTMusic()
        
        # Create download directory if it doesn't exist
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def authenticate_spotify(self):
        """Authenticate with Spotify API"""
        auth_manager = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-read-private playlist-read-collaborative user-library-read"
        )
        
        # Start Flask server to handle callback
        threading.Thread(target=self._run_server, daemon=True).start()
        
        # Get authorization URL and open it in browser
        auth_url = auth_manager.get_authorize_url()
        webbrowser.open(auth_url)
        
        console.print("\n[yellow]Opening browser for Spotify authentication...")
        console.print("[yellow]Please log in and authorize the application.")
        
        # Wait for the authorization code from the callback
        while authorization_code is None:
            time.sleep(1)
        
        # Exchange authorization code for access token
        token_info = auth_manager.get_access_token(authorization_code)
        
        # Initialize Spotify client
        self.sp = spotipy.Spotify(auth=token_info['access_token'])
        console.print("[green]Successfully authenticated with Spotify!")

    def _run_server(self):
        """Run Flask server to handle OAuth callback"""
        app.run(port=8888)

    def get_playlists(self) -> List[Dict[str, Any]]:
        """
        Get a list of the user's saved playlists.
        
        Returns:
            List of playlists with id, name, and track count
        """
        if not self.sp:
            raise Exception("Not authenticated with Spotify. Call authenticate_spotify() first.")
        
        results = self.sp.current_user_playlists()
        playlists = []
        
        for item in results['items']:
            playlists.append({
                'id': item['id'],
                'name': item['name'],
                'tracks': item['tracks']['total']
            })
        
        return playlists

    def get_saved_tracks(self) -> List[Dict[str, Any]]:
        """
        Get a list of the user's saved tracks.
        
        Returns:
            List of saved tracks
        """
        if not self.sp:
            raise Exception("Not authenticated with Spotify. Call authenticate_spotify() first.")
        
        results = self.sp.current_user_saved_tracks()
        tracks = results['items']
        
        while results['next']:
            results = self.sp.next(results)
            tracks.extend(results['items'])
        
        return tracks

    def get_playlist_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        """
        Get all tracks from a specific playlist.
        
        Args:
            playlist_id: Spotify playlist ID
            
        Returns:
            List of tracks in the playlist
        """
        if not self.sp:
            raise Exception("Not authenticated with Spotify. Call authenticate_spotify() first.")
        
        results = self.sp.playlist_tracks(playlist_id)
        tracks = results['items']
        
        while results['next']:
            results = self.sp.next(results)
            tracks.extend(results['items'])
        
        return tracks

    def search_youtube_music(self, track_name: str, artist_name: str) -> Optional[str]:
        """
        Search for a track on YouTube Music.
        
        Args:
            track_name: Name of the track
            artist_name: Name of the artist
            
        Returns:
            YouTube Music video ID, or None if no match found
        """
        query = f"{track_name} {artist_name}"
        search_results = self.ytmusic.search(query, filter="songs", limit=1)
        
        if not search_results:
            return None
        
        return search_results[0]['videoId']

    def download_track(self, video_id: str, track_info: Dict[str, Any]) -> bool:
        """
        Download a track from YouTube Music.
        
        Args:
            video_id: YouTube video ID
            track_info: Dictionary with track metadata
            
        Returns:
            True if download was successful, False otherwise
        """
        artist = track_info['artists'][0]['name']
        title = track_info['name']
        album = track_info.get('album', {}).get('name', 'Unknown Album')
        
        # Remove characters that aren't allowed in filenames
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        safe_artist = re.sub(r'[\\/*?:"<>|]', "", artist)
        
        # Create output directory structure
        artist_dir = os.path.join(self.download_dir, safe_artist)
        if not os.path.exists(artist_dir):
            os.makedirs(artist_dir)
        
        # Set up yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(artist_dir, f"{safe_title}.%(ext)s"),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }, {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            }],
            'quiet': True,
            'no_warnings': True
        }
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            return True
        except Exception as e:
            console.print(f"[red]Error downloading {title}: {str(e)}")
            return False

    def process_playlist(self, playlist_id: str, playlist_name: str):
        """
        Process a playlist: get all tracks and download them from YouTube Music.
        
        Args:
            playlist_id: Spotify playlist ID
            playlist_name: Name of the playlist for display purposes
        """
        tracks = self.get_playlist_tracks(playlist_id)
        total = len(tracks)
        
        console.print(f"\n[bold blue]Processing playlist: {playlist_name} ({total} tracks)")
        
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn()
        ) as progress:
            task = progress.add_task(f"Downloading", total=total)
            
            for i, item in enumerate(tracks):
                track = item['track']
                artist = track['artists'][0]['name']
                title = track['name']
                
                progress.update(task, description=f"[{i+1}/{total}] {title} - {artist}", advance=0)
                
                # Search for the track on YouTube Music
                video_id = self.search_youtube_music(title, artist)
                
                if not video_id:
                    console.print(f"[yellow]Could not find: {title} - {artist}")
                    progress.update(task, advance=1)
                    continue
                
                # Download the track
                success = self.download_track(video_id, track)
                progress.update(task, advance=1)

    def download_saved_playlists(self):
        """Get all user's playlists and offer to download them"""
        playlists = self.get_playlists()
        
        if not playlists:
            console.print("[yellow]No playlists found.")
            return
        
        console.print("\n[bold]Your Spotify Playlists:")
        for i, playlist in enumerate(playlists):
            console.print(f"[{i+1}] {playlist['name']} ({playlist['tracks']} tracks)")
        
        try:
            selection = input("\nEnter playlist numbers to download (comma-separated) or 'all': ")
            
            if selection.lower() == 'all':
                selected_indices = range(len(playlists))
            else:
                selected_indices = [int(idx.strip()) - 1 for idx in selection.split(',')]
            
            for idx in selected_indices:
                if 0 <= idx < len(playlists):
                    playlist = playlists[idx]
                    self.process_playlist(playlist['id'], playlist['name'])
                else:
                    console.print(f"[red]Invalid playlist number: {idx+1}")
                    
        except ValueError:
            console.print("[red]Invalid input. Please enter numbers separated by commas.")
        except KeyboardInterrupt:
            console.print("\n[yellow]Download canceled.")

# Flask route to handle the OAuth callback
@app.route('/callback')
def callback():
    global authorization_code
    authorization_code = request.args.get('code')
    return "Authentication successful! You can close this window and return to the terminal."

def main():
    parser = argparse.ArgumentParser(description='Download Spotify playlists from YouTube Music')
    parser.add_argument('--client-id', required=True, help='Spotify API Client ID')
    parser.add_argument('--client-secret', required=True, help='Spotify API Client Secret')
    parser.add_argument('--download-dir', default='~/Music/SpotifyDownloads', help='Directory to save downloaded tracks')
    
    args = parser.parse_args()
    
    try:
        downloader = SpotifyYouTubeDownloader(args.client_id, args.client_secret, args.download_dir)
        downloader.authenticate_spotify()
        downloader.download_saved_playlists()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Program interrupted by user. Exiting...")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
