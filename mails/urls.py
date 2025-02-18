from django.urls import path
from .views import *

urlpatterns = [
    path('gmail/login/', gmail_login, name='gmail_login'),
    # AUTH
    path('gmail/link/', start_gmail_auth, name='link_account'),
    path('gmail/revoke/', revoke_account, name='revoke_account'),
    path('gmail/check/', check_linked_account, name="check_linked_account"),
    # CALLBACK
    path('gmail/callback/', gmail_callback, name='gmail_callback'),
    # MAIN FUNCTION
    path('email/emails/', get_emails, name='get_emails'),
    path('email/replies/<str:thread_id>/', get_replies, name='get_replies'),
    path('email/<str:email_id>/', get_email_details, name='get_email_details'),
    path('email/send/', send_email, name='send_emails'),
    path('email/reply/', reply_email, name='reply_emails'),
    path('email/forward/', forward_email, name='forward_emails'),
]
