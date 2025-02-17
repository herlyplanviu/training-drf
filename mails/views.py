import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.conf import settings
from django.shortcuts import redirect, render
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from users.models import GoogleAuth
from rest_framework.decorators import permission_classes, authentication_classes

from users.serializers import GoogleAuthSerializer

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

def gmail_login(request):
    return render(request, 'gmail_login.html')

# Helper function to get credentials from DB
def get_credentials(user):
    try:
        google_auth = GoogleAuth.objects.get(user=user)
        # creds_data = json.loads(google_auth.token)
        creds_data = GoogleAuthSerializer(google_auth).data
        return Credentials.from_authorized_user_info(creds_data, scopes=SCOPES)
    except (GoogleAuth.DoesNotExist, json.JSONDecodeError):
        return None

# Gmail Login and Auth Flow
def start_gmail_auth(request):
    flow = Flow.from_client_secrets_file(
        os.path.join(settings.BASE_DIR, 'credentials.json'),
        scopes=SCOPES,
        redirect_uri=request.build_absolute_uri('/gmail/callback')
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    request.session['state'] = state
    return redirect(authorization_url)

# Gmail Callback
@api_view(['GET'])
def gmail_callback(request):
    state = request.session.get('state')
    flow = Flow.from_client_secrets_file(
        os.path.join(settings.BASE_DIR, 'credentials.json'),
        scopes=SCOPES,
        state=state,
        redirect_uri=request.build_absolute_uri('/gmail/callback')
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials

    # Save credentials to database
    google_auth, _ = GoogleAuth.objects.get_or_create(user=request.user)
    google_auth.token = credentials.token
    google_auth.refresh_token = credentials.refresh_token
    google_auth.token_uri = credentials.token_uri
    google_auth.client_id = credentials.client_id
    google_auth.client_secret = credentials.client_secret
    google_auth.scopes = ','.join(credentials.scopes)
    google_auth.save()

    return redirect('/emails/')

# Get Emails
@api_view(['GET'])
@authentication_classes([JWTAuthentication, BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_emails(request):
    creds = get_credentials(request.user)
    if not creds:
        return JsonResponse({"error": "Google account not linked or invalid token"}, status=400)

    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])
    
    emails = []
    for msg in messages:
        # Get full message details
        message_detail = service.users().messages().get(userId='me', id=msg['id']).execute()

        # Extract threadId and headers
        thread_id = message_detail.get('threadId')
        headers = message_detail.get('payload', {}).get('headers', [])
        
        # Extract required headers
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        # message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), None)
        snippet = message_detail.get('snippet')
        
        emails.append({
            'id': msg['id'],
            'thread_id': thread_id,
            'message_id': msg['id'],
            'subject': subject,
            'sender': sender,
            'snippet': snippet
        })

    return JsonResponse(emails, safe=False)


# Get Email Details
@api_view(['GET'])
@authentication_classes([JWTAuthentication, BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_email_details(request, email_id):
    creds = get_credentials(request.user)
    if not creds:
        return JsonResponse({"error": "Google account not linked or invalid token"}, status=400)

    service = build('gmail', 'v1', credentials=creds)
    try:
        msg = service.users().messages().get(userId='me', id=email_id, format='full').execute()
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    headers = msg.get('payload', {}).get('headers', [])
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')

    # Decode Email Body
    body = ''.join(base64.urlsafe_b64decode(part['body']['data']).decode('utf-8') 
                   for part in msg['payload'].get('parts', []) 
                   if part['mimeType'] == 'text/html')

    return JsonResponse({
        'subject': subject,
        'sender': sender,
        'body': body
    })

# Send Email
@api_view(['POST'])
@authentication_classes([JWTAuthentication, BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def send_email(request):
    creds = get_credentials(request.user)
    if not creds:
        return JsonResponse({'error': 'Google account not linked or invalid token'}, status=400)

    # Get email details from request
    to = request.data.get('to')
    subject = request.data.get('subject')
    body = request.data.get('body')

    if not all([to, subject, body]):
        return JsonResponse({'error': 'Missing email fields (to, subject, body)'}, status=400)

    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    message.attach(MIMEText(body, 'html'))
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    try:
        service = build('gmail', 'v1', credentials=creds)
        send_message = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        return JsonResponse({'message': 'Email sent successfully', 'message_id': send_message['id']}, status=200)
    except Exception as error:
        return JsonResponse({'error': f'An error occurred: {error}'}, status=500)

@api_view(['POST'])
@authentication_classes([JWTAuthentication, BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def reply_email(request):
    creds = get_credentials(request.user)
    if not creds:
        return JsonResponse({'error': 'Google account not linked or invalid token'}, status=400)

    # Get email details from request
    thread_id = request.data.get('thread_id')
    message_id = request.data.get('message_id')
    to = request.data.get('to')
    body = request.data.get('body')

    if not all([thread_id, message_id, to, body]):
        return JsonResponse({'error': 'Missing email fields (thread_id, message_id, to, body)'}, status=400)

    try:
        # Initialize Gmail service
        service = build('gmail', 'v1', credentials=creds)

        # Get original message details to extract the subject
        original_message = service.users().messages().get(userId='me', id=message_id).execute()
        headers = original_message.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        
        # Prefix with "Re: " to indicate a reply
        reply_subject = f"Re: {subject}"

        # Construct the email reply
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = reply_subject
        message['In-Reply-To'] = message_id
        message['References'] = message_id
        message.attach(MIMEText(body, 'html'))
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        # Send the reply email
        send_message = service.users().messages().send(
            userId='me', 
            body={
                'raw': raw_message,
                'threadId': thread_id
            }
        ).execute()
        
        return JsonResponse({'message': 'Reply sent successfully', 'message_id': send_message['id']}, status=200)
    
    except Exception as error:
        return JsonResponse({'error': f'An error occurred: {error}'}, status=500)
