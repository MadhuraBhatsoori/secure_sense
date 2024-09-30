import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.cloud import speech
from werkzeug.utils import secure_filename
import io
from google.oauth2 import service_account



# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load credentials and configure generative AI

from load_creds import load_creds
creds = load_creds()
genai.configure(api_key='AIzaSyD6BHIlJEkxzHhUOlaVHuYBOKJzcmTk4BA')
     

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google_secret_key.json'
# Create speech client instance
speech_client = speech.SpeechClient()

# Tuned and flash model configurations
tuned_model_name_1 = "tunedModels/emails-tsko9gc7g2qk"
tuned_model_name_2 = "tunedModels/calls-6pmcy3jt5z2r"
flash_model_name = "gemini-1.5-flash"

generation_config = {
    "temperature": 0,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# Initialize generative models with safety settings
try:
    tuned_model_1 = genai.GenerativeModel(
        model_name=tuned_model_name_1,
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    tuned_model_2 = genai.GenerativeModel(
        model_name=tuned_model_name_2,
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    flash_model = genai.GenerativeModel(
        model_name=flash_model_name,
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    logger.debug("Gemini models initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing Gemini models: {e}")


def gemini_response(question, model):
    question = question.lower().strip()
    response = model.generate_content(question)
    if response.candidates[0].finish_reason == 3:
        return "Please refrain from asking irrelevant questions"
    else:
        return response.text


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests from the frontend."""
    data = request.json
    user_message = data.get('message', '').strip()
    selected_topic = data.get('topic', '').strip()

    logger.debug(f"Received chat request with message: {user_message} and topic: {selected_topic}")

    if not user_message:
        logger.error("No message provided in the request.")
        return jsonify({'error': 'No message provided'}), 400

    # Combine the selected topic and user message for context
    full_message = f"Topic: {selected_topic}. User message: {user_message}"

    try:
        if selected_topic == 'phishing email':
            tuned_response = gemini_response(full_message, tuned_model_1)
            formatted_response = f"The email you pasted in chat is {tuned_response}."

            reasoning_prompt = f"""
            Analyze the following email and the assessment: Only provide reasoning do not change the assessment answer. 

            Email content: {user_message}

            Assessment: {formatted_response}

            Please provide:
            1. A detailed explanation of why this email is considered {tuned_response}. List specific elements or characteristics of the email that support this classification.
            2. Suggestions for further actions or considerations based on this analysis. Include both immediate steps and general best practices for dealing with such emails.

            Format your response in a clear section: "Reasoning". Give in one sentence.
            """
            
            flash_reasoning = gemini_response(reasoning_prompt, flash_model)
            clean_reasoning = flash_reasoning.replace('#', '').replace('*', '')
        
        elif selected_topic == 'spam calls':
            tuned_response = gemini_response(full_message, tuned_model_2)
            formatted_response = f"The call record you attached indicates {tuned_response}."

            reasoning_prompt = f"""
            Analyze the following call record and the assessment: Only provide reasoning do not change the assessment answer. 

            Call content: {user_message}

            Assessment: {formatted_response}

            Please provide:
            1. A detailed explanation of why this call record is considered {tuned_response}. List specific elements or characteristics of the call record that support this classification.
            2. Suggestions for further actions or considerations based on this analysis. Include both immediate steps and general best practices for handling such calls.

            Format your response in a clear section: "Reasoning". Give in one sentence.
            """
            
            flash_reasoning = gemini_response(reasoning_prompt, flash_model)
            clean_reasoning = flash_reasoning.replace('#', '').replace('*', '')

        elif selected_topic == 'general security advice':
            prompt = f"Provide a brief and concise response to the following request: {full_message}"
            tuned_response = gemini_response(prompt, flash_model)
            formatted_response = tuned_response.replace('#', '').replace('*', '')
            clean_reasoning = None

        else:
            formatted_response = gemini_response(full_message, tuned_model)
            clean_reasoning = None

        logger.debug("Successfully generated response for chat request.")
        return jsonify({
            "tuned_response": formatted_response,
            "flash_reasoning": clean_reasoning,
        })

    except Exception as e:
        logger.error(f"Error handling chat request: {e}")
        return jsonify({'error': 'An error occurred while processing the request'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads for audio transcription."""
    try:
        if 'file' not in request.files:
            logger.error("No file part in the request.")
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            logger.error("No selected file.")
            return jsonify({'error': 'No selected file'}), 400
        
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            logger.debug(f"File saved to {file_path}. Beginning transcription.")
            transcription = transcribe_audio(file_path)
            os.remove(file_path)  # Clean up the file after transcription
            logger.debug("Transcription completed and file cleaned up.")
            
            return jsonify({'transcription': transcription}), 200

    except Exception as e:
        logger.error(f"Error uploading and transcribing file: {e}")
        return jsonify({'error': 'An error occurred while processing the file'}), 500

def transcribe_audio(file_path):
    """Transcribe an audio file using Google Speech-to-Text."""
    try:
        with open(file_path, 'rb') as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.MP3,  # Change this to MP3
    sample_rate_hertz=16000,
    language_code="en-US",
)


        response = speech_client.recognize(config=config, audio=audio)
        
        transcription = " ".join([result.alternatives[0].transcript for result in response.results])
        logger.debug("Transcription successful.")
        return transcription.strip()
    
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return "Error transcribing audio"

if __name__ == '__main__':
    logger.debug("Starting Flask app...")
    app.run(host='0.0.0.0', port=5000, debug=True)