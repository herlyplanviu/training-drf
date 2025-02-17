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

    folder = request.GET.get('folder', 'inbox')
    # Get page token from request (if provided)
    page_token = request.GET.get('page_token', None)
    
    # Determine query based on folder
    folder_queries = {
        'inbox': 'in:inbox',
        'sent': 'in:sent',
        'junk': 'in:spam',
        'trash': 'in:trash',
        'archive': '-in:inbox -in:sent -in:spam -in:trash'
    }
    query = folder_queries.get(folder.lower(), 'in:inbox')  # Default to inbox

    # Initialize Gmail service
    service = build('gmail', 'v1', credentials=creds)

    # Fetch messages with optional page token
    query_params = {
        'userId': 'me',
        'maxResults': 10,
        'q': query
    }
    if page_token:
        query_params['pageToken'] = page_token

    results = service.users().messages().list(**query_params).execute()
    messages = results.get('messages', [])
    next_page_token = results.get('nextPageToken')

    # Construct email list
    emails = []
    for msg in messages:
        message_detail = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = message_detail.get('payload', {}).get('headers', [])

        # Extract required fields
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        snippet = message_detail.get('snippet')
        thread_id = message_detail.get('threadId')

        emails.append({
            'thread_id': thread_id,
            'message_id': msg['id'],
            'subject': subject,
            'sender': sender,
            'snippet': snippet,
        })

    # Return paginated response
    return JsonResponse({
        'emails': emails,
        'next_page_token': next_page_token
    }, safe=False)


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

    thread_id = msg.get('threadId')
    headers = msg.get('payload', {}).get('headers', [])
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')

    # Decode Email Body
    body = ''.join(base64.urlsafe_b64decode(part['body']['data']).decode('utf-8') 
                   for part in msg['payload'].get('parts', []) 
                   if part['mimeType'] == 'text/html')

    return JsonResponse({
        'thread_id': thread_id,
        'message_id': msg['id'],
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

        # Construct the email reply
        message = MIMEMultipart()
        message['to'] = to
        # message['subject'] = f"Re: {request.data.get('subject', '')}"
        message['subject'] = f"{request.data.get('subject', '')}"
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

@api_view(['POST'])
@authentication_classes([JWTAuthentication, BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def forward_email(request):
    creds = get_credentials(request.user)
    if not creds:
        return JsonResponse({'error': 'Google account not linked or invalid token'}, status=400)

    # Get email details from request
    message_id = request.data.get('message_id')
    to = request.data.get('to')
    additional_body = request.data.get('body', '')

    if not all([message_id, to]):
        return JsonResponse({'error': 'Missing email fields (message_id, to)'}, status=400)

    try:
        # Initialize Gmail service
        service = build('gmail', 'v1', credentials=creds)

        # Get original message details
        original_message = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        headers = original_message.get('payload', {}).get('headers', [])
        
        # Extract details for the forward
        # original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
        
        # Get the original body (supports plain text and HTML)
        parts = original_message.get('payload', {}).get('parts', [])
        body = ""
        for part in parts:
            mime_type = part.get('mimeType')
            if mime_type == 'text/plain' or mime_type == 'text/html':
                body_data = part['body'].get('data')
                if body_data:
                    body += base64.urlsafe_b64decode(body_data).decode('utf-8')
        
        # Construct the forwarded email content
        # forward_subject = f"Fwd: {request.data.get('subject', '')}"
        forward_subject = f"{request.data.get('subject', '')}"
        forward_body = f"""
            <p>{additional_body}</p>
            <br><hr>
            <p>---------- Forwarded message ---------</p>
            <p>From: {sender}<br>
            Date: {date}<br>
            Subject: {request.data.get('subject', '')}</p>
            <br>
            {body}
        """

        # Construct the email to be forwarded
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = forward_subject
        message.attach(MIMEText(forward_body, 'html'))
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        # Send the forwarded email
        send_message = service.users().messages().send(
            userId='me', 
            body={'raw': raw_message}
        ).execute()
        
        return JsonResponse({'message': 'Forwarded successfully', 'message_id': send_message['id']}, status=200)
    
    except Exception as error:
        return JsonResponse({'error': f'An error occurred: {error}'}, status=500)
