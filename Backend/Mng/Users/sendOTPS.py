from __future__ import print_function
import random 
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings
import requests
from twilio.rest import Client
import http.client
import json
from decouple import config


# def send_email(subject, email,message):
   
#     configuration = sib_api_v3_sdk.Configuration()
#     configuration.api_key['api-key'] = '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'

#     api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
#     email_content = message
 
#     sender = {
#         "email": "shivanandgarg1234@gmail.com",
#         "name": "SATCARD"
#     }
#     receiver = [
#         {
#             "email": email, 
#         }
#     ]

#     try:
      
#         api_response = api_instance.send_transac_email({
#             "sender": sender,
#             "to": receiver,
#             "subject": subject,
#             "textContent": email_content,
#         })
#         print("Email sent successfully:", api_response)
#         # return Response({"message": "Email sent successfully"}, status=200)
#     except ApiException as e:
#         print("Exception when calling TransactionalEmailsApi->send_transac_email: %s\n" % e)
#         # return Response({"error": "An error occurred while sending the email."}, status=500)


def sendSMS(phone, message):

    account_sid = config("ACCOUNT_SID", default="unsafe-secret-key")
    auth_token = config("ACCOUNT_TOKEN", default="unsafe-secret-key")
    client = Client(account_sid ,auth_token)
    
    Message = client.messages.create(
        body = message ,
        from_ = '+1 641 435 6293',
        to = phone
    )
    print(Message.body)