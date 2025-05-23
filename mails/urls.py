from django.urls import path
from .views import *

urlpatterns = [
    path('gmail/login/', gmail_login, name='gmail_login'),
    # AUTH
    path('google/link/', start_gmail_auth, name='link_account'),
    path('google/revoke/', revoke_account, name='revoke_account'),
    path('google/check/', check_linked_account, name="check_linked_account"),
    # CALLBACK
    path('gmail/callback/', gmail_callback, name='gmail_callback'),
    # MAIN FUNCTION
    path('email/emails/', get_emails, name='get_emails'),
    path('email/replies/<str:thread_id>/', get_replies, name='get_replies'),
    path('email/email/<str:email_id>/', get_email_details, name='get_email_details'),
    path('email/send/', send_email, name='send_emails'),
    path('email/reply/', reply_email, name='reply_emails'),
    path('email/forward/', forward_email, name='forward_emails'),
    path('email/read/<str:message_id>/', read_email, name='read_email'),
    path('email/unread/<str:message_id>/', unread_email, name='unread_email'),
    # TEST CBV
    path('email/emailsv2/', GetEmailsView.as_view(), name='get-emails'),
]
