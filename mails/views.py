import base64
import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
import re
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.conf import settings
from django.shortcuts import redirect, render
from django.http import HttpResponse, JsonResponse
import requests
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from users.models import GoogleAuth
from rest_framework.decorators import permission_classes, authentication_classes
from users.models import User
from google.auth.transport.requests import Request
from users.serializers import GoogleAuthSerializer
from django.utils import timezone
from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError


SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',  # ✅ Allows modifying email labels (read/unread)
    'https://www.googleapis.com/auth/gmail.send'     # ✅ Allows sending emails
]

# Helper function to extract credentials and handle expiry
def get_credentials(user):
    try:
        google_auth = GoogleAuth.objects.get(user=user)
        creds_data = GoogleAuthSerializer(google_auth).data
        if not creds_data.get('expiry'):
            expiry_time = datetime.datetime.now() + datetime.timedelta(hours=1)
            creds_data['expiry'] = expiry_time.isoformat()
        creds = Credentials.from_authorized_user_info(creds_data, scopes=SCOPES)
        
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            google_auth.token = creds.token
            if creds.refresh_token is not None and creds.refresh_token != '':
                google_auth.refresh_token = creds.refresh_token
            google_auth.token_uri = creds.token_uri
            google_auth.client_id = creds.client_id
            google_auth.client_secret = creds.client_secret
            google_auth.scopes = ','.join(creds.scopes)
            google_auth.expiry = timezone.make_aware(creds.expiry)
            google_auth.save()
        
        return creds
    except (GoogleAuth.DoesNotExist, json.JSONDecodeError):
        return None

def gmail_login(request):
    return render(request, 'gmail_login.html')

# Gmail Authentication Flow
def start_gmail_auth(request):
    # Check if Content-Type is application/json
    server_url = request.build_absolute_uri('/')  # Get the base server URL
    custom_url = f"{server_url}gmail/link/?user={request.GET.get('user')}"
    
    # Check if Content-Type is application/json
    if request.content_type == 'application/json':
        return JsonResponse({
            'message': 'Please open me in browser tab', 
            'url': custom_url
        }, status=400)
    
    flow = Flow.from_client_secrets_file(
        os.path.join(settings.BASE_DIR, 'credentials.json'),
        scopes=SCOPES,
        redirect_uri=request.build_absolute_uri('/gmail/callback')
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    request.session['state'] = state
    request.session['user'] = request.GET.get('user')
    return redirect(authorization_url)

@api_view(['POST'])
def revoke_account(request):
    user = request.user
    
    try:
        # Retrieve GoogleAuth record for the user
        google_auth = GoogleAuth.objects.get(user=user)
        creds = get_credentials(request.user)

        # Revoke the token using Google's endpoint
        revoke_url = 'https://oauth2.googleapis.com/revoke'
        params = {'token': creds.token}
        response = requests.post(revoke_url, params=params)
        
        # If the revocation is successful
        if response.status_code == 200:
            google_auth.delete()

            # Return a success message
            return JsonResponse({'message': 'Google account successfully unlinked and token revoked'}, status=200)
        else:
            return JsonResponse({'error': 'Failed to revoke Google token'}, status=400)

    except GoogleAuth.DoesNotExist:
        # If no GoogleAuth record is found for the user
        return JsonResponse({'error': 'Google account not linked'}, status=400)

@api_view(["GET"])
def check_linked_account(request):
    try:
        # Check if a Google account is linked to the user
        google_auth = GoogleAuth.objects.get(user=request.user)

        # Get credentials for the user
        creds = get_credentials(request.user)
        
        if creds:
            # Initialize Gmail service
            service = build('gmail', 'v1', credentials=creds)

            # Get user profile (email and name)
            profile = service.users().getProfile(userId='me').execute()

            # Extract email and name
            email = profile.get('emailAddress', 'Not available')

            # Return success response with user's email and name
            return JsonResponse({
                'message': 'Google account is linked',
                'email': email,
            }, status=200)

        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=400)
    
    except GoogleAuth.DoesNotExist:
        # If no Google account is linked, raise a 400 error
        return JsonResponse({'error': 'Google account not found'}, status=404)
    except Exception as e:
        # Handle any other exceptions
        return JsonResponse({'error': str(e)}, status=500)
    

@api_view(['GET'])
def gmail_callback(request):
    state = request.session.get('state')
    user = request.session.get('user')

    flow = Flow.from_client_secrets_file(
        os.path.join(settings.BASE_DIR, 'credentials.json'),
        scopes=SCOPES,
        state=state,
        redirect_uri=request.build_absolute_uri('/gmail/callback')
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials

    try:
        # Get or create GoogleAuth object for the user
        google_auth, _ = GoogleAuth.objects.get_or_create(user=User.objects.filter(id=user).first())
        google_auth.token = credentials.token
        if credentials.refresh_token is not None and credentials.refresh_token != '':
            google_auth.refresh_token = credentials.refresh_token
        google_auth.token_uri = credentials.token_uri
        google_auth.client_id = credentials.client_id
        google_auth.client_secret = credentials.client_secret
        google_auth.scopes = ','.join(credentials.scopes)
        google_auth.expiry = timezone.make_aware(credentials.expiry)
        google_auth.save()

        # Return an HTML page that closes the tab after a short delay
        return HttpResponse("""
            <html>
                <head>
                    <script type="text/javascript">
                        window.close();
                    </script>
                </head>
                <body>
                    <p>Google account linked successfully. You can now close this tab.</p>
                </body>
            </html>
        """)
    except Exception as e:
        # Handle any errors, if needed
        return JsonResponse({'error': str(e)}, status=500)

# Utility function to parse email headers
def parse_sender(sender):
    match = re.match(r'([^<]+)\s*<([^>]+)>', sender)
    if match:
        name, email = match.groups()
    else:
        name = email = sender.strip()
    return {'name': name, 'email': email}

# Function to fetch emails
@api_view(['GET'])
@authentication_classes([JWTAuthentication, BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_emails(request):
    creds = get_credentials(request.user)
    if not creds:
        return JsonResponse({"error": "Google account not linked or invalid token"}, status=400)

    try:
        # ✅ Initialize Gmail API service
        service = build('gmail', 'v1', credentials=creds)

        # ✅ Get folder and pagination token
        folder = request.GET.get('folder', 'inbox')
        page_token = request.GET.get('page_token', None)

        # ✅ Define query for the selected folder
        folder_queries = {
            'inbox': 'in:inbox',
            'sent': 'in:sent',
            'junk': 'in:spam',
            'trash': 'in:trash',
            'archive': '-in:inbox -in:sent -in:spam -in:trash'
        }
        query = folder_queries.get(folder.lower(), 'in:inbox')

        # ✅ Fetch message list (only IDs)
        query_params = {
            'userId': 'me',
            'maxResults': 15,  # ✅ Increase batch size
            'q': query
        }
        if page_token:
            query_params['pageToken'] = page_token

        results = service.users().messages().list(**query_params).execute()
        messages = results.get('messages', [])
        next_page_token = results.get('nextPageToken')

        if not messages:
            return JsonResponse({'emails': [], 'next_page_token': None}, safe=False)

        # ✅ Use `batchGet` to retrieve multiple emails in one request
        def batch_get_request(request_id, response, exception):
            if exception is None:
                emails.append(process_message(response))

        batch = service.new_batch_http_request(callback=batch_get_request)
        emails = []

        for msg in messages:
            batch.add(service.users().messages().get(userId='me', id=msg['id'], format='metadata'))

        batch.execute()  # ✅ Executes all requests in parallel

        return JsonResponse({'emails': emails, 'next_page_token': next_page_token}, safe=False)

    except HttpError as e:
        return JsonResponse({"error": f"Failed to get emails: {e}"}, status=500)

def process_message(message_detail):
    """Extracts email details from API response"""
    headers = message_detail.get('payload', {}).get('headers', [])
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
    is_read = 'UNREAD' not in message_detail.get('labelIds', [])

    return {
        'thread_id': message_detail.get('threadId'),
        'message_id': message_detail['id'],
        'subject': subject,
        'sender': parse_sender(sender),
        'snippet': message_detail.get('snippet', ''),
        'is_read': is_read,
    }

# Function to fetch replies
@api_view(['GET'])
@authentication_classes([JWTAuthentication, BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_replies(request, thread_id):
    creds = get_credentials(request.user)
    if not creds:
        return JsonResponse({"error": "Google account not linked or invalid token"}, status=400)

    service = build('gmail', 'v1', credentials=creds)

    if thread_id:
        try:
            thread = service.users().threads().get(userId='me', id=thread_id).execute()
            emails = [
                {
                    'thread_id': thread_id,
                    'message_id': message.get('id'),
                    'subject': next((h['value'] for h in message['payload'].get('headers', []) if h['name'].lower() == 'subject'), 'No Subject'),
                    'sender': parse_sender(next((h['value'] for h in message['payload'].get('headers', []) if h['name'] == 'From'), 'Unknown Sender')),
                    'snippet': message.get('snippet'),
                    'body': ''.join(base64.urlsafe_b64decode(part['body']['data']).decode('utf-8') 
                                    for part in message['payload'].get('parts', []) if part['mimeType'] == 'text/html'),
                }
                for message in thread.get('messages', [])
            ]
            return JsonResponse(emails, safe=False)
        except Exception as e:
            return JsonResponse({"error": f"Failed to get thread: {str(e)}"}, status=500)

# Function to get email details
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
        headers = msg.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        body = ''.join(base64.urlsafe_b64decode(part['body']['data']).decode('utf-8') 
                       for part in msg['payload'].get('parts', []) if part['mimeType'] == 'text/html')
        
        return JsonResponse({
            'thread_id': msg.get('threadId'),
            'message_id': msg['id'],
            'subject': subject,
            'sender': parse_sender(sender),
            'body': body,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def create_email_message(to, subject, body, attachment=None, in_reply_to=None, references=None):
    """Helper function to construct the email message."""
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    if in_reply_to:
        message['In-Reply-To'] = in_reply_to
    if references:
        message['References'] = references
    message.attach(MIMEText(body, 'html'))

    if attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={attachment.name}')
        message.attach(part)

    return message
def send_raw_message(service, message, thread_id=None):
    """Helper function to send a raw email message with optional thread_id."""
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    body = {'raw': raw_message}
    if thread_id:
        body['threadId'] = thread_id  # Include thread_id for replies
    return service.users().messages().send(userId='me', body=body).execute()

# Send Email
@api_view(['POST'])
@authentication_classes([JWTAuthentication, BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def send_email(request):
    creds = get_credentials(request.user)
    if not creds:
        return JsonResponse({'error': 'Google account not linked or invalid token'}, status=400)

    to = request.POST.get('to')
    subject = request.POST.get('subject')
    body = request.POST.get('body')
    attachment = request.FILES.get('attachment')

    if not all([to, subject, body]):
        return JsonResponse({'error': 'Missing email fields (to, subject, body)'}, status=400)

    try:
        service = build('gmail', 'v1', credentials=creds)
        message = create_email_message(to, subject, body, attachment)
        send_message = send_raw_message(service, message)
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

    thread_id = request.POST.get('thread_id')
    message_id = request.POST.get('message_id')
    to = request.POST.get('to')
    body = request.POST.get('body')
    attachment = request.FILES.get('attachment')

    if not all([thread_id, message_id, to, body]):
        return JsonResponse({'error': 'Missing email fields (thread_id, message_id, to, body)'}, status=400)

    try:
        service = build('gmail', 'v1', credentials=creds)
        message = create_email_message(to, f"{request.POST.get('subject', '')}", body, attachment, message_id, message_id)
        send_message = send_raw_message(service, message, thread_id)
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
    message_id = request.POST.get('message_id')
    to = request.POST.get('to')
    additional_body = request.POST.get('body', '')
    attachment = request.FILES.get('attachment')

    if not all([message_id, to]):
        return JsonResponse({'error': 'Missing email fields (message_id, to)'}, status=400)

    try:
        # Initialize Gmail service
        service = build('gmail', 'v1', credentials=creds)

        # Get original message details
        original_message = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        headers = original_message.get('payload', {}).get('headers', [])
        
        # Extract details for the forward
        original_subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
        
        # Get the original body (supports plain text and HTML)
        parts = original_message.get('payload', {}).get('parts', [])
        body = ""
        attachments = []  # List to hold any attachments
        for part in parts:
            mime_type = part.get('mimeType')
            filename = part.get('filename', '')

            # Check if there's an attachmentId
            if 'attachmentId' in part['body']:
                attachment_id = part['body']['attachmentId']
                attachment_data = service.users().messages().attachments().get(userId='me', messageId=message_id, id=attachment_id).execute()

                # Retrieve attachment data
                attachment_data_content = base64.urlsafe_b64decode(attachment_data['data'])
                attachments.append({
                    'filename': filename or 'Unknown File',
                    'data': attachment_data_content
                })

            # Process the body for text/plain or text/html
            if mime_type == 'text/plain' or mime_type == 'text/html':
                body_data = part['body'].get('data')
                if body_data:
                    body += base64.urlsafe_b64decode(body_data).decode('utf-8')
        
        # Construct the forwarded email content
        forward_subject = f"{request.POST.get('subject')}"
        forward_body = f"""
            <p>{additional_body}</p>
            <br><hr>
            <p>---------- Forwarded message ---------</p>
            <p>From: {sender}<br>
            Date: {date}<br>
            Subject: {original_subject}</p>
            <br>
            {body}
        """

        # Construct the email to be forwarded
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = forward_subject
        message.attach(MIMEText(forward_body, 'html'))

        # Attach any existing attachments to the forwarded email
        for attachment_data in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment_data['data'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{attachment_data["filename"]}"'
            )
            message.attach(part)

        # Add the new attachment from the request if provided (as file-like object)
        if attachment and hasattr(attachment, 'read'):
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())  # Now `.read()` should work because it's a file-like object
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={attachment.name}'
            )
            message.attach(part)

        # Encode the message to base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        # Send the forwarded email
        send_message = service.users().messages().send(
            userId='me', 
            body={'raw': raw_message}
        ).execute()
        
        return JsonResponse({'message': 'Forwarded successfully', 'message_id': send_message['id']}, status=200)
    
    except Exception as error:
        return JsonResponse({'error': f'An error occurred: {error}'}, status=500)

def modify_email_status(user, message_id, is_read):
    """Helper function to modify email read/unread status."""
    creds = get_credentials(user)
    if not creds:
        return {'error': 'Google account not linked or invalid token'}

    try:
        # Initialize Gmail service
        service = build('gmail', 'v1', credentials=creds)

        # Labels to modify
        modify_labels = {
            'removeLabelIds': ['UNREAD'] if is_read else [],
            'addLabelIds': [] if is_read else ['UNREAD']
        }

        # Update email status
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body=modify_labels
        ).execute()

        return {'message': 'Email status updated successfully'}

    except Exception as error:
        return {'error': f'An error occurred: {error}'}
    
@api_view(['POST'])
@authentication_classes([JWTAuthentication, BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def read_email(request, message_id):
    if not message_id:
        return JsonResponse({'error': 'Missing email field: message_id'}, status=400)

    response = modify_email_status(request.user, message_id, is_read=True)
    return JsonResponse(response, status=200 if 'message' in response else 500)

@api_view(['POST'])
@authentication_classes([JWTAuthentication, BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def unread_email(request, message_id):
    """Marks an email as unread (adds 'UNREAD' label)."""

    if not message_id:
        return JsonResponse({'error': 'Missing email field: message_id'}, status=400)

    response = modify_email_status(request.user, message_id, is_read=False)
    return JsonResponse(response, status=200 if 'message' in response else 500)