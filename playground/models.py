from django.db import models
from jsonfield import JSONField

# completed - change if necessary. 
# cannot use postgre therefore no array implementation possible.
# amounts array made with new model introduction and manytomanyfield if no idea how to use in function take help from google

class Users(models.Model):
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    wallet_address = models.CharField(max_length=255)
    email = models.EmailField(max_length=254) #use validate_email inbuilt validator for emails
    roles = (
        (1, "user"),
        (2, "admin"),
    )
    role = models.IntegerField(choices=roles, default=1)
    user_image = models.ImageField()

class Payments(models.Model):
    status = models.BooleanField(default=False)
    user_id = models.JSONField()
    
class Items(models.Model):
    #owner=user.id
    #auction start time
    item_name = models.CharField(max_length=40)
    description = models.CharField(max_length=255)
    end_date = models.DateTimeField()
    starting_bid = models.PositiveBigIntegerField(null=True)
    verification_status = models.BooleanField(default=False)
    sale_status = models.BooleanField(default=False)
    sale_price = models.PositiveIntegerField()
    item_image = models.ImageField()
    bidders = models.ManyToManyField(Users)
    
# class Amount(models.Model):
#     amt = models.PositiveIntegerField()

class Bids(models.Model):
    # users = models.ManyToManyField(Users)
    # amounts = models.ManyToManyField(Amount)
    user_amounts = models.JSONField()
    item = models.ForeignKey(Items)
    time = models.DateTimeField(auto_now_add=True)

class Category(models.Model):
    category_name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    items = models.ManyToManyField(Items)
