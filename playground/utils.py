from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.utils import timezone
from playground.models import Bids, Items, Users
from web3 import Web3


def SendNotif(bid):
    item = Items.objects.get(id=bid.itemId)
    curr_bidders = list(bid.userId.keys())
    req_bidders = item.bidders.exclude(id__in=curr_bidders)
    for bidder in req_bidders:
        user = Users.objects.get(id=bidder)

        subject = 'New Bid Placed on {}'.format(item.itemName)
        message = 'Hello {},\n\nA new bid has been placed on the item "{}".\n\nSincerely,\nYourApp Team'.format(
            user.username, item.itemName
        )
        from_email = 'yourapp@example.com'
        recipient_list = [user.email]

        send_mail(subject, message, from_email, recipient_list, fail_silently=False)

def SendConfirmationNotif(bid):
    item = Items.objects.get(id=bid.itemId)
    curr_bidders = list(bid.userId.keys())

    for bidder in curr_bidders:
        user = Users.objects.get(id=bidder)

        subject = 'New Bid Successfully Placed on {}'.format(item.itemName)
        message = 'Hello {},\n\nYou have successfully placed a new bid on the item "{}".\n\nSincerely,\nYourApp Team'.format(
            user.username, item.itemName
        )
        from_email = 'yourapp@example.com'
        recipient_list = [user.email]

        send_mail(subject, message, from_email, recipient_list, fail_silently=False)

def TimeBuffer(itemId):
    item = Items.objects.get(id=itemId)

    if timezone.now()< item.timeBuffer:
        return False
    else:
        item.timeBuffer = timezone.now() + timezone.timedelta(milliseconds=1000)
        item.save()
        return True
    
def CheckBalance(userId, bidAmount):
    w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))  

    user = Users.objects.get(id=userId)
    wallet_address = user.walletAddress

    try:
        balance_wei = w3.eth.get_balance(wallet_address)
        balance_eth = w3.fromWei(balance_wei, 'ether')
        
        if balance_eth >= bidAmount:
            return True
        else:
            #print(f"Error: User {userId} has insufficient funds.")
            return False

    except Exception as e:
        #print("Error fetching balance")
        return False

def CheckBid(bid):
    total_amount = sum(bid.userId.values())
    item = Items.objects.get(id=bid.itemId)
    item_bids = item.bids.all()
    max_bid = max(item_bids, key=lambda x: x.amount).amount

    bid.amount = total_amount
    bid.save()

    for userId, amount in bid.userId.items():
        try:
            user = Users.objects.get(id=userId)
        except Users.DoesNotExist:
            #print(f"Error: User {userId} does not exist.")
            return False

        if not CheckBalance(userId, amount):
            return False
        
    if total_amount <= max_bid:
            #print(f"Error: Bid amount is insufficient.")
            return False
    
    return True

def AuctionInProgress(itemId):
    item = Items.objects.get(id=itemId)
    if item.auctionStartTime <= timezone.now() < item.auctionStartTime + item.auctionDuration:
        return True
    else:
        return False




    
    






    

