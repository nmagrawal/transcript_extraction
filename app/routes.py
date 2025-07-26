# app/routes.py
from flask import Blueprint, request, jsonify, Response

# Import all our processing functions
from .scraper import fetch_transcript_for_url, fetch_youtube_transcript
from .utils import extract_youtube_video_id

api_bp = Blueprint('api', __name__)

# Make the route asynchronous to use `await` directly
@api_bp.route('/transcript', methods=['POST'])
async def get_transcript():
    """
    Accepts a URL and returns the transcript.
    It dispatches to the correct handler based on the URL type.
    """
    if not request.json or 'url' not in request.json:
        return jsonify({'error': 'URL is required in JSON body'}), 400

    url = request.json['url']
    
    try:
        # --- THE NEW DISPATCHER LOGIC ---
        video_id = extract_youtube_video_id(url)

        if video_id:
            # It's a YouTube URL, call the API
            print(f"Detected YouTube video ID: {video_id}. Calling external API.")
            transcript_text = await fetch_youtube_transcript(video_id)
        else:
            # It's not YouTube, use the Playwright scraper
            print("Non-YouTube URL detected. Starting Playwright scraper.")
            transcript_text = await fetch_transcript_for_url(url)

        return Response(transcript_text, mimetype='text/plain', status=200)

    except Exception as e:
        print(f"An error occurred while processing {url}: {e}")
        return jsonify({'error': 'Failed to process the transcript.', 'details': str(e)}), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """A simple health check endpoint for cloud services."""
    return jsonify({"status": "healthy"}), 200