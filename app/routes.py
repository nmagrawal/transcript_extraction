# app/routes.py

import logging
from flask import Blueprint, request, jsonify, Response

# Import all our processing functions
from .scraper import fetch_transcript_for_url, fetch_youtube_transcript
from .utils import extract_youtube_video_id
from .subscription.email_validation import validate_email_address

logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
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
            logging.info(f"Detected YouTube video ID: {video_id}. Calling external API.")
            transcript_text = await fetch_youtube_transcript(video_id)
        else:
            # It's not YouTube, use the Playwright scraper
            logging.info("Non-YouTube URL detected. Starting Playwright scraper.")
            transcript_text = await fetch_transcript_for_url(url)

        return Response(transcript_text, mimetype='text/plain', status=200)

    except Exception as e:
        logging.error(f"An error occurred while processing {url}: {e}")
        return jsonify({'error': 'Failed to process the transcript.', 'details': str(e)}), 500


@api_bp.route('/subscribe', methods=['POST'])
def subscribe():
    """A simple endpoint to handle newsletter subscriptions."""
    if not request.json or 'email' not in request.json:
        return jsonify({'error': 'Email is required in JSON body'}), 400

    email = request.json['email']
    # Here you would add logic to save the email to your database or mailing list
    logging.info(f"Received subscription request for email: {email}")

    validated_email = validate_email_address(email)


    if validated_email == email:
        return jsonify({'message': f'Successfully subscribed {validated_email} to the newsletter!'}), 200
    else:
        return jsonify({'error': f'Invalid email address: {validated_email}'}), 400
    
    


@api_bp.route('/health', methods=['GET'])
def health_check():
    """A simple health check endpoint for cloud services."""
    return jsonify({"status": "healthy"}), 200