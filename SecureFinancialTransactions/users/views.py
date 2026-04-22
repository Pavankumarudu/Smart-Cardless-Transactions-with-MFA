# Create your views here.
from django.shortcuts import render, HttpResponse
from django.contrib import messages
from .forms import UserRegistrationForm
from .models import UserRegistrationModel, TokenCountModel,TransactionModel
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from datetime import datetime, timedelta
from jose import JWTError, jwt
import numpy as np
import os
from .utility import Model_tested


SECRET_KEY = "ce9941882f6e044f9809bcee90a2992b4d9d9c21235ab7c537ad56517050f26b"
ALGORITHM = "HS256"

import socket


def get_ipv4_address():
    try:
        # connect to an external host, doesn't send data
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google DNS
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return f"Error: {e}"


def create_access_token(data: dict):
    to_encode = data.copy()
    # expire time of the token
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    # return the generated token
    return encoded_jwt


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HttpResponse(
            status_code=HttpResponse(status=204),
            detail="Could not validate credentials",
        )


# Create your views here.
def UserRegisterActions(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            print('Data is Valid')
            loginId = form.cleaned_data['loginid']
            TokenCountModel.objects.create(loginid=loginId, count=0)
            form.save()
            from .utility import Model_tested
            Model_tested.capture_and_store_face(loginId)
            messages.success(request, 'You have been successfully registered')
            form = UserRegistrationForm()
            return render(request, 'UserRegistrations.html', {'form': form})
        else:
            messages.success(request, 'Email or Mobile Already Existed')
            print("Invalid form")
    else:
        form = UserRegistrationForm()
    return render(request, 'UserRegistrations.html', {'form': form})


def UserLoginCheck(request):
    if request.method == "POST":
        loginid = request.POST.get('loginid')
        pswd = request.POST.get('pswd')
        print("Login ID = ", loginid, ' Password = ', pswd)
        try:
            check = UserRegistrationModel.objects.get(loginid=loginid, password=pswd)
            status = check.status
            print('Status is = ', status)
            if status == "activated":
                request.session['id'] = check.id
                request.session['loggeduser'] = check.name
                request.session['loginid'] = loginid
                request.session['email'] = check.email
                data = {'loginid': loginid}
                token_jwt = create_access_token(data)
                request.session['token'] = token_jwt
                print("User id At", check.id, status)
                return render(request, 'users/UserHomePage.html', {'ip': get_ipv4_address()})
            else:
                messages.success(request, 'Your Account Not at activated')
                return render(request, 'UserLogin.html')
        except Exception as e:
            print('Exception is ', str(e))
            pass
        messages.success(request, 'Invalid Login id and password')
    return render(request, 'UserLogin.html', {})


def UserHome(request):
    return render(request, 'users/UserHomePage.html', {'ip': get_ipv4_address()})


def user_transaction(request):
    if request.method == 'POST':
        sender_id = request.POST.get('sender_id')
        recipient_id = request.POST.get('recipient_id')
        amount = float(request.POST.get('amount'))
        remarks = request.POST.get('remarks')
        response = Model_tested.check_face_match()
        if response=='success':
            # 4. Generate OTP
            otp = Model_tested.generate_otp()
            print(f"Generated OTP: {otp}")
            # 5. Encrypt OTP
            encrypted_otp = Model_tested.encrypt(otp)
            print(f"Encrypted OTP: {encrypted_otp}")
            # 6. Decrypt OTP (Simulate system's decryption)
            decrypted_otp = Model_tested.decrypt(encrypted_otp)
            print(f"Decrypted OTP: {decrypted_otp}")
            request.session['sender_id'] = sender_id
            request.session['recipient_id'] = recipient_id
            request.session['amount'] = amount
            request.session['remarks'] = remarks
            request.session['decrypted_otp'] = decrypted_otp
            return render(request, 'users/otpCheck.html', {})


        else:

            return render(request, 'users/faceNotMatch.html', {'msg': "Transaction failed: your face does not match"})

    else:
        loginid = request.session['loginid']
        from django.db.models import Q
        users = UserRegistrationModel.objects.filter(~Q(loginid=loginid))
        return render(request, 'users/send_money_form.html', {'loginid': loginid, 'users': users})

def userOtpVerify(request):
    brwOtp=request.POST.get('otpBrw')
    sender_id = request.session['sender_id']
    recipient_id = request.session['recipient_id']
    amount = request.session['amount']
    remarks = request.session['remarks']
    decrypted_otp = request.session['decrypted_otp']
    if decrypted_otp==brwOtp:
        import uuid
        transaction_id = str(uuid.uuid4())
        print("Transaction ID:", transaction_id)
        TransactionModel.objects.create(sender_id=sender_id,recipient_id=recipient_id,amount=amount,remarks=remarks,otp=decrypted_otp,transaction_id=transaction_id)
        from django.db.models import Q
        users = UserRegistrationModel.objects.filter(~Q(loginid=sender_id))
        return render(request, 'users/send_money_form.html',
                      {'loginid': sender_id, 'users': users, 'msg': f"Transaction Successful transaction id {transaction_id} "})

    else:
        from django.db.models import Q
        users = UserRegistrationModel.objects.filter(~Q(loginid=sender_id))
        return render(request, 'users/send_money_form.html', {'loginid': sender_id, 'users': users,'msg':"Transaction failed:your OTP wrong "})



def viewHistory(request):
    login_id=request.session['loginid']
    try:
        data_1 = TransactionModel.objects.filter(sender_id=login_id)
        for i in data_1:
            print(i.sender_id)
    except:
        print("No transactions found")
    return render(request, 'users/viewHistory.html',{'data': data_1})

