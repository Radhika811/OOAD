from django.urls import path
from . import views


#URLconfg
urlpatterns=[
    #expected that userid can be fetched using the session
    path("home/",views.home),
    path("home/<str:category>/",views.get_all_items),
    path("home/<int:itemId>/",views.get_category_then_item),#filter its category and redirect to the below path accordingly
    path("home/<str:category>/<int:itemId>/",views.get_item),
    path("home/<str:category>/<int:itemId>/place_bid",views.place_bid),
    path("home/<str:category>/<int:itemId>/erase_bid",views.erase_bid),
    path("home/<int:userId>/",views.get_user), #go to profile page
    path("home/intiate_auction",views.initiate_auction), #start the auction
]
