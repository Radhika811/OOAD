from django.shortcuts import render,redirect
import json
from django.http import JsonResponse,HttpResponse
from playground.models import Users,Payments,Items,Category,Amount,Bids
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from playground.utils import SendNotif, SendConfirmationNotif, TimeBuffer, CheckBalance, CheckBid, AuctionInProgress 
from web3 import Web3
import os
from os.path import join, dirname
from dotenv import load_dotenv


contract_address = "0x6D892cD478BeE23f8dD91F10479b40bE9f4C9b7a"
abi = json.loads('[{"inputs":[{"internalType":"address","name":"_address","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[{"internalType":"address","name":"_from","type":"address"},{"internalType":"uint256","name":"_amount","type":"uint256"}],"name":"checkWalletBalance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"_to","type":"address"},{"internalType":"uint256","name":"_amount","type":"uint256"}],"name":"makePayment","outputs":[],"stateMutability":"payable","type":"function"}]')
    
infura_url = ""
web3 = Web3(Web3.HTTPProvider(infura_url))

contract = web3.eth.contract(address = contract_address, abi = abi)
#payment functions

#done
@login_required
def make_payment(request):
    
    req_body = request.body.decode("utf-8")
    req_body_json = json.loads(req_body)
    to_address = req_body_json["to_address"]
    user_id = req_body_json["user_id"]
    item_id = req_body_json["item_id"]
    user = Users.objects.get(id=user_id)
    item = Items.objects.get(id=item_id)
    from_address = user.wallet_address
    highest_bid = Bids.objects.filter(item = item).latest("time")
    amt_dict = highest_bid.user_amounts
    amt_json = json.loads(amt_dict)
    amount = amt_json[""+user_id+""]
            
    print(to_address, from_address, amount)
    web3.eth.send_transaction({ 
            'to': contract_address,
            'from': from_address,
            'value': amount,
        })
    tx_hash = contract.functions.makePayment(to_address, amount).transact()
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    payment = Payments(user_id = user_id, status = True)
    payment.save()
    
    print("deducted amount : ", amount)
    balance = web3.eth.get_balance(from_address)
    print("remaining balance : ", balance)
# add request handleers and send emails and map those view functionalities to the urls in the urls.py 

def home(request):
    return JsonResponse("hello")

#get items and display functions
def get_all_items(request,category):
    try:
        items = Category.objects.filter(category_name=category)
        auctions_data = []
        for item in items:
            auction_data = {
                'itemId' : item.itemId,
                'itemName': item.itemName,
                'startingBid': item.startingBid,
                'imageURL': item.get_image_url(),  # Include the image URL
                # Add other fields as needed
            }
            auctions_data.append(auction_data)

        return JsonResponse({'auctions': auctions_data})
    
    except Items.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)





#auction functions 
@login_required
def initiate_auction(request):
    if request.method == 'POST':
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'error': 'User not authenticated.',"message":"login to access this route"}, status=401)
        item_data = {
            'item_name': request.POST.get('item_name'),
            'description': request.POST.get('item_description'),
            'item_image': request.POST.get('item_image'),
            'starting_bid': request.POST.get('starting_bid'),
            'end_date': request.POST.get('auction_duration'),
            'category_name': request.POST.get('category_name'),
            'auctionStartTime': timezone.now(),
            'userId' : user_id,
            # Add other fields as needed
        }

        try:
            item = Items.objects.create(**item_data)
            # messages.success(request, 'Auction initiated successfully.')
            return JsonResponse({'status': 'success', 'message': 'Auction initiated successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

#assumption : itemId is present in url. If it is provided by frontend, change accordingly.
@login_required
def erase_bid(request, itemId):
    if request.method == 'POST':
        bid_id = request.data.get('bidId')

        if not TimeBuffer(itemId):
            return JsonResponse({'error': 'Cannot erase bid. Please try again in a few seconds.'}, status=400)

        if not AuctionInProgress(itemId):
            return JsonResponse({'error': 'Cannot erase bid. Auction has ended.'}, status=400)

        try:
            bid = Bids.objects.get(bidId=bid_id)
        except Bids.DoesNotExist:
            return JsonResponse({'error': 'Bid does not exist.'}, status=400)

        user_id = request.user.id
        if user_id not in bid.userId:
            return JsonResponse({'error': 'User does not have permission to erase this bid.'}, status=403)

        bid.delete()
        return JsonResponse({'success': 'Bid erased successfully.'})

    return JsonResponse({'error': 'Invalid request method.'}, status=400)

@login_required 
def place_bid(request, item_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_amounts = data.get('user_amounts', None)

            if user_amounts is None:
                return JsonResponse({'error': 'Invalid data. Missing user_amounts field.'}, status=400)

            if not TimeBuffer(item_id):
                return JsonResponse({'error': 'Cannot place bid. Please try again in a few seconds.'}, status=400)
            
            if not AuctionInProgress(item_id):
                return JsonResponse({'error': 'Cannot place bid. Auction has ended.'}, status=400)

            try:
                item = Items.objects.get(id=item_id)
                bid = Bids.objects.create(itemId=item_id, userId=user_amounts)

                if not CheckBid(bid):
                    bid.delete()
                    return JsonResponse({'error': 'Bid is invalid.'}, status=400)

                item.bids.add(bid)
                
                SendNotif(bid)
                SendConfirmationNotif(bid)
                
                for user_id in bid.userId.keys():
                    if user_id not in item.bidders.all():
                        item.bidders.add(user_id)

                # Send relevant data to the frontend
                response_data = {
                    'success': 'Bid placed successfully.',
                    'item_id': item_id,
                    'bid_id': bid.bidId,
                    # Add other relevant data
                }

                return JsonResponse(response_data)

            except Items.DoesNotExist:
                return JsonResponse({'error': 'Item does not exist.'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data.'}, status=400)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)

def DisplayBids(request, itemId):
    try:
        user_id=request.session.get("user_id")
        bids = Bids.objects.filter(userId=user_id)
        bid_data = [{'bidId': bid.bidId, 'itemId': bid.itemId, 'amount': float(bid.amount)} for bid in bids]
        return JsonResponse({'bids': bid_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def DisplayAuctions(request, categoryName):
    try:
        items = Items.objects.filter(category_name=categoryName)
        auctions_data = []
        for item in items:
            auction_data = {
                'itemId' : item.itemId,
                'itemName': item.itemName,
                'startingBid': item.startingBid,
                'imageURL': item.get_image_url(),  # Include the image URL
                # Add other fields as needed
            }
            auctions_data.append(auction_data)

        return JsonResponse({'auctions': auctions_data})
    
    except Items.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)

def Graph(request, itemId):
    try:
        item = Items.objects.get(id=itemId)
    except Items.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)

    bids = Bids.objects.filter(itemId=itemId)
    bid_ids = [bid.id for bid in bids]
    amounts = [bid.amount for bid in bids]

    data = {'bid_ids': bid_ids, 'amounts': amounts}
    return JsonResponse({'item': {'id': item.id, 'name': item.name}, 'graph_data': data})

def get_category_then_item(request,itemId):
    item= Items.objects.filter(id__in=itemId)
    category_name=Category.objects.filter(item)
    #get the category using foreignkey  and then redirect to the below url

    redirect("home/<category_name>/<int:itemId>/")

def get_user(request):
    user=request.session.get("user_id")
    return JsonResponse({"user":user,"message":"success"})