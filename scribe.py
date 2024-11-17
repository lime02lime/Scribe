import json
import requests
import os
import openai
import assemblyai as aai

# Define audio download and transcription functions:

def download_audio(media_url, headers):
    try:
        # Get the media metadata
        response = requests.get(media_url, headers=headers)
        if response.status_code == 200:
            # Extract the download URL from the response (e.g., the actual media file URL)
            download_url = response.json().get('url')
            
            # Download the audio file from the download URL
            audio_download = requests.get(download_url, headers=headers)
            if audio_download.status_code == 200:
                # Specify a temporary path in Lambda's /tmp directory
                temp_audio_path = '/tmp/audio_file.mp3'

                # Write the audio content (binary) to the file and return
                with open(temp_audio_path, 'wb') as temp_file:
                    temp_file.write(audio_download.content)  # Write binary content
                #print(f'Audio saved to: {temp_audio_path}')
                return temp_audio_path
                
            else:
                print(f'Failed to download audio file. Error code: {audio_download.status_code}')
        else:
            print(f'Failed to access media. Error code: {response.status_code}')
            # Error 401 here might indicate that my whatsapp access token is expired (this has happened)

    except Exception as e:
        print(f'Error: {e}')
    
    return None  # Return None in case of failure


# Transcription with assemblyAi api:
def transcribe_audio(temp_audio_path):

    # ensure that a file was found
    if not temp_audio_path:
        return 'Audio not sent to transcription, failed at download stage'
    
    # attempt transcription using assemblyAi api
    try:
        aai.settings.api_key = os.getenv('ASSEMBLY_TOKEN')
        with open(temp_audio_path, "rb") as audio_file:
            config = aai.TranscriptionConfig(language_detection=True) # aai defaults to English, must indicate language detection
            transcriber = aai.Transcriber(config = config)
            transcript = transcriber.transcribe(audio_file)
            print(f"AssemblyAI transcript: {transcript.text}")
        
        return transcript.text

    # if this fails, print error and return None
    except Exception as e:
        print(f'failed to transcribe, error: {e}')
        return None

# Transcription with OpenAI Whisper API:
""" 
def transcribe_audio(temp_audio_path):
    # ensure that a file was found
    if not temp_audio_path:
        return 'Audio not sent to transcription, failed at download stage'
    
    # attempt transcription using openai api
    try:
        openai.api_key = os.getenv('OPENAI_TOKEN')
        with open(temp_audio_path, "rb") as audio_file:
            transcription = openai.Audio.transcribe(
                model = "whisper-1",
                file = audio_file,
                prompt="Tbh though, nem me incomoda assim tanto. Gosto da situação que temos agora and I just don't really want that to change. Tipo, life's pretty good rn! I'm happy!"
            )
        
        # extract text part from json, print and return
        text = transcription.get('text', 'transcription unavailable')
        print(f'transcribed text: {text}')
        return text

    # if this fails, print error and return None
    except Exception as e:
        print(f'failed to transcribe, error: {e}')
        return None
"""

def send_message(target_number, scribe_number, text, preview_url=False):
    url = f"https://graph.facebook.com/v21.0/{scribe_number}/messages"
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": target_number, "type": "text",
        "text": {
            "preview_url": preview_url,
            "body": text } 
    }

    # send the transcription back to the user, with the data above
    response = requests.post(url, headers=headers, json=payload)
    return response.json()


def lambda_handler(event, context):

    print(json.dumps(event))
    body = json.loads(event['body'])

    # if there's no 'messages' then its just a message status update, exit:
    if not 'messages' in body['entry'][0]['changes'][0]['value']:
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Not relevant event"})
        }

    # if type is not audio then its a text message or other message type, not audio, exit:
    messages = body['entry'][0]['changes'][0]['value']['messages'][0]
    if messages['type'] != 'audio' or 'audio' not in messages:
        target_number, scribe_number = messages['from'], body['entry'][0]['changes'][0]['value']['metadata']['phone_number_id']
        send_message(target_number, scribe_number, 'Please send a voice message for me to transcribe', preview_url=False)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Not audio message"})
        }

    print('event: message received from user')
    
    # fetch the key data about the audio message
    audio_info = messages['audio']
    audio_id = audio_info['id']
    target_number = messages['from']

    # fetch the whatsapp number ID - this is used when sending the transcribed text back to the user
    scribe_number = body['entry'][0]['changes'][0]['value']['metadata']['phone_number_id']
    
    # access the audio file:
    access_token = os.getenv('WHATSAPP_TOKEN')
    media_url = f'https://graph.facebook.com/v21.0/{audio_id}/'
    headers = {
        'Authorization': f'Bearer {access_token}' #currently this token resets once in a while, will need a fix
    }

    # download the audio based on the media_id value:
    temp_audio_path = download_audio(media_url, headers)
    
    # transcribe the audio
    transcription_text = transcribe_audio(temp_audio_path)

    # respond to the user with the transcribed text
    if transcription_text:
        send_message(target_number, scribe_number, transcription_text, preview_url=False)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "All steps complete"})
        }
    
    else:
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Transcription failed"})
        }