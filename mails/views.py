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
        creds_data = json.loads(google_auth.token)
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
    google_auth.token = credentials.to_json()
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
    
    emails = [{
        'id': msg['id'],
        'subject': next((h['value'] for h in service.users().messages().get(userId='me', id=msg['id']).execute().get('payload', {}).get('headers', []) if h['name'] == 'Subject'), 'No Subject'),
        'sender': next((h['value'] for h in service.users().messages().get(userId='me', id=msg['id']).execute().get('payload', {}).get('headers', []) if h['name'] == 'From'), 'Unknown Sender'),
        'snippet': service.users().messages().get(userId='me', id=msg['id']).execute().get('snippet')
    } for msg in messages]

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
