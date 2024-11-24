# Scribe

Scribe is a WhatsApp chatbot that allows users to transcribe voice messages. When a voice message is received, users can forward it to the bot, which will respond with a message containing the transcribed text. The bot does not initiate conversations—it only responds to messages sent by users.

**Try out the Beta version [here](https://wa.me/message/TGOE4TP4HTX6H1).**

**Currently in development. This app is for personal use only and not for commercial purposes.**

## Overview

- When messages are received by the WhatsApp Business API account phone number, a webhook event is sent to a specified URL.
- This URL is created using AWS API Gateway, which forwards the webhook to AWS Lambda.
- AWS Lambda is triggered, fetching the received message and transcribing it if it is an audio file.
- The transcribed message is then sent back to the user.
- Performance info is saved to a DynamoDB database, containing the user ID, audio file size, and the time taken for the lambda function to run.

## Prerequisites

- WhatsApp Business Account and API access
- AssemblyAI, OpenAI, and WhatsApp API access tokens
- Python 3.x
- `requests` library for making HTTP requests

## Setup

### 1. Create WhatsApp Business API Webhook

Ensure that your WhatsApp Business API webhook is set up to send incoming messages to your AWS API Gateway URL. Below is an example JSON structure for an incoming message:

```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "123456789",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "15551234567",
              "phone_number_id": "987654321"
            },
            "contacts": [
              {
                "profile": {
                  "name": "name"
                },
                "wa_id": "15551234567"
              }
            ],
            "messages": [
              {
                "from": "15551234567",
                "id": "wamid.abc",
                "timestamp": "1731520390",
                "type": "audio",
                "audio": {
                  "mime_type": "audio/ogg; codecs=opus",
                  "sha256": "abc",
                  "id": "123456789",
                  "voice": true
                }
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```

### 2. Set up Lambda Environment
AWS Lambda cannot install all libraries, so the required libraries must be added as Layers to the lambda environment. I installed my required python libraries to a local folder Python, which I saved as .zip. On AWS Lambda, I then created a Layer that I uploaded the .zip file to, which I finally attached to my Lambda function.

### 3. Set up DynamoDB Database:
Create a table in AWS DynamoDB with a name that can be referenced in the log_event function.

### 4. Other Items to Configure
- Upload the scribe.py code to your Lambda function.
- Ensure that your webhook endpoint is publicly accessible.
- Configure the webhook URL in the WhatsApp Business API settings.
- Add your API tokens as system variables in AWS Lambda.

## How It Works:
1. A user sends a WhatsApp voice message to the phone number associated with the bot.
2. The WhatsApp API sends a webhook event to the AWS API Gateway URL.
3. The Lambda function lambda_handler is triggered.

`lambda_handler`:
1. Checks that the received event is a voice message. If it isn't, it sends a message to the user asking for a voice message.
2. Fetches key information about the voice message and user.
3. Accesses the Facebook Graph API to fetch the audio download URL.
4. Runs download_audio to save the audio temporarily in memory, returning the file path.
5. Runs transcribe_audio to transcribe the audio file, returning the transcribed text.
6. If the text was successfully transcribed, it runs send_message to send this text back to the user.
7. Returns a JSON response with status code 200, indicating whether the operation was successful or where it failed.

`transcribe_audio`:
1. Accesses the AssemblyAI API token from system variables.
2. Loads the audio file path.
3. Creates an AssemblyAI transcriber and runs it with the audio file path.
4. Returns the transcribed text.
