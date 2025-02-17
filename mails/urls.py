from django.urls import path
from .views import forward_email, gmail_login, gmail_callback, get_emails, get_email_details, reply_email, send_email, start_gmail_auth

urlpatterns = [
    path('gmail/login/', gmail_login, name='gmail_login'),
    path('gmail/start-auth/', start_gmail_auth, name='start_gmail_auth'),
    path('gmail/callback/', gmail_callback, name='gmail_callback'),
    path('emails/', get_emails, name='get_emails'),
    path('emails/send/', send_email, name='send_emails'),
    path('emails/reply/', reply_email, name='reply_emails'),
    path('emails/forward/', forward_email, name='forward_emails'),
    path('emails/<str:email_id>/', get_email_details, name='get_email_details'),
]
