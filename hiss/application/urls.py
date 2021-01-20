from django.urls import path

from application import views

app_name = "application"
urlpatterns = [
    path("", views.CreateApplicationView.as_view(), name="create"),
    path("<uuid:pk>", views.UpdateApplicationView.as_view(), name="update"),
    path("<uuid:pk>/confirm", views.ConfirmApplicationView.as_view(), name="confirm"),
    path("<uuid:pk>/decline", views.DeclineApplicationView.as_view(), name="decline"),
    path("check_id/<str:discord_id>/", views.CheckDiscordIdView.as_view(), name="check_id"),
    path("link_discord/<str:discord_id>/", views.LinkDiscordView.as_view(), name="link_discord"),
    path("discord_data/<str:discord_id>/", views.DiscordDataView.as_view(), name="discord_data")
]
