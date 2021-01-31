"""
Application views
"""

import os
import requests

from django import views
from django.contrib.auth import mixins
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import generic

from user.models import User
from team.models import Team
from application.emails import send_confirmation_email, send_creation_email
from application.forms import ApplicationModelForm
from application.models import (
    Application,
    Wave,
    STATUS_CONFIRMED,
    STATUS_DECLINED,
    STATUS_ADMITTED,
)


class CreateApplicationView(mixins.LoginRequiredMixin, generic.CreateView):
    """
    Creates a new Application and links it to a User if one doesn't already exist and the User's not already
    applied to be a volunteer.
    """

    form_class = ApplicationModelForm
    template_name = "application/application_form.html"
    success_url = reverse_lazy("status")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_wave"] = Wave.objects.active_wave()
        return context

    def form_valid(self, form: ApplicationModelForm):
        if Application.objects.filter(user=self.request.user).exists():
            form.add_error(None, "You can only submit one application to this event.")
            return self.form_invalid(form)
        application: Application = form.save(commit=False)
        application.user = self.request.user
        application.wave = Wave.objects.active_wave()
        application.save()
        send_creation_email(application)
        return redirect(self.success_url)


class UpdateApplicationView(mixins.LoginRequiredMixin, generic.UpdateView):
    """
    Updates a linked Application. Updating an Application does not change the Wave it was originally submitted
    during.
    """

    queryset = Application.objects.all()
    form_class = ApplicationModelForm
    template_name = "application/application_form.html"
    success_url = reverse_lazy("status")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_wave"] = Wave.objects.active_wave()
        return context

    def get_object(self, queryset: QuerySet = None) -> Application:
        """
        Checks to make sure that the user actually owns the application requested.
        """
        app: Application = super().get_object()
        if self.request.user.is_superuser:
            return app
        if app.user != self.request.user:
            raise PermissionDenied("You don't have permission to view this application")
        return app


class ConfirmApplicationView(mixins.LoginRequiredMixin, views.View):
    """
    Changes an application's status from STATUS_ADMITTED to STATUS_CONFIRMED
    """

    def post(self, request: HttpRequest, *args, **kwargs):
        pk = self.kwargs["pk"]
        app: Application = Application.objects.get(pk=pk)
        if app.status == STATUS_CONFIRMED:
            # Do nothing, they already confirmed.
            return redirect(reverse_lazy("status"))
        if app.user != request.user:
            raise PermissionDenied(
                "You don't have permission to view this application."
            )
        if app.status != STATUS_ADMITTED:
            raise PermissionDenied(
                "You can't confirm your application if it hasn't been approved."
            )
        app.status = STATUS_CONFIRMED
        app.save()
        send_confirmation_email(app)
        return redirect(reverse_lazy("status"))


class DeclineApplicationView(mixins.LoginRequiredMixin, views.View):
    """
    Changes an application's status from STATUS_ADMITTED to STATUS_DECLINED
    """

    def post(self, request: HttpRequest, *args, **kwargs):
        pk = self.kwargs["pk"]
        app: Application = Application.objects.get(pk=pk)
        if app.status == STATUS_DECLINED:
            # Do nothing, they already declined
            return redirect(reverse_lazy("status"))
        if app.user != request.user:
            raise PermissionDenied(
                "You don't have permission to view this application."
            )
        if not (app.status == STATUS_ADMITTED or app.status == STATUS_CONFIRMED):
            raise PermissionDenied(
                "You can't decline your spot if it hasn't been approved."
            )
        app.status = STATUS_DECLINED
        app.save()
        return redirect(reverse_lazy("status"))

class CheckDiscordIdView(mixins.LoginRequiredMixin, views.View):
    """
    Checks to see if a discord id has been used already or if the current user 
    already has a discord id linked to it. Also pings bot to ensure that the 
    linked discord account is in the server.
    """

    def get(self, request, *_args, **kwargs):
        if not Application.objects.filter(user_id=self.request.user.id):
            return HttpResponse("Application is not finished.")

        app: Application = Application.objects.get(user_id=self.request.user.id)
        discord_id = kwargs.get('discord_id')
        request_user = os.environ['REG_USERNAME']
        request_pass = os.environ['REG_PASSWORD'] 

        if app is not None:
            # Check to see if the application was declined
            if app.status == STATUS_DECLINED:
                return HttpResponse("Application to Hacklahoma was declined. Please contact a Hacklahoma team member through the Hacklahoma Discord or through team@hacklahoma.org.")
            # Check to see if the application returned already has a discord id
            # elif app.discord_id and app.discord_id != 0:
            #    return HttpResponse("Application already has a Discord account linked to it. If you think this is an error please contact a Hacklahoma team member through the Hacklahoma Discord or through team@hacklahoma.org.")
           
            # Check to see if the discord id was provided
            if discord_id is not None:
                # Check to see if there is an application with the specified discord id
                if Application.objects.filter(discord_id=discord_id):
                    return HttpResponse("Discord account already linked. If you think this is an error please contact a Hacklahoma team member through the Hacklahoma Discord or through team@hacklahoma.org.")
                else:
                    try:
                        # Ping the bot asking for the specified user
                        r = requests.get(
                            f"{os.environ['DISCORD_BOT_URL']}check_user/{discord_id}",
                            json={
                                "request_user": request_user,
                                "request_pass": request_pass
                            }
                        )

                        if(r.json()['exists']):
                            return redirect(reverse_lazy("application:link_discord", kwargs={'discord_id': discord_id}))
                        else:
                            return HttpRequest("Discord account not found within server. Please make sure you have already joined the Hacklahoma discord server.")
                    except requests.ConnectionError as e:
                        # handle the exception
                        return HttpResponse(e)
        else:
            return redirect(reverse_lazy("status"))


class LinkDiscordView(mixins.LoginRequiredMixin, views.View):
    """
    Gets the Application and then updates the discord_id, and checked_in
    """

    def get(self, request: HttpRequest, *args, **kwargs):
        app: Application = Application.objects.get(user_id=self.request.user.id)
        discord_id = kwargs.get('discord_id')
        request_user = os.environ['REG_USERNAME']
        request_pass = os.environ['REG_PASSWORD'] 

        if app:
            app.discord_id = discord_id
            app.checked_in = True
            app.save()

            user: User = User.objects.get(id=app.user_id)

            if user.team_id:
                team = Team.objects.get(id=user.team_id)

                requests.put(
                    f"{os.environ['DISCORD_BOT_URL']}check_in",
                    json={
                        "discord_id": discord_id,
                        "name": f"{app.first_name} {app.last_name}",
                        "team_name": team.name,
                        "request_user": request_user,
                        "request_pass": request_pass
                    }
                )
            else:
                requests.put(
                    f"{os.environ['DISCORD_BOT_URL']}check_in",
                    json={
                        "discord_id": discord_id,
                        "name": f"{app.first_name} {app.last_name}",
                        "team_name": None,
                        "request_user": request_user,
                        "request_pass": request_pass
                    }
                )

            return redirect(reverse_lazy("application:discord_success"))
            #return HttpResponse(f"discord_id: {discord_id}, name: {app.first_name}")

        return redirect(reverse_lazy("status"))

class DiscordSuccessView(generic.TemplateView, mixins.LoginRequiredMixin):
    """
    Template for the successful discord link page
    """

    template_name = "application/discord_success.html"
    

class DiscordDataView(views.View):
    queryset = Application.objects.all()

    def get(self, request, *_args, **kwargs):
        discord_id = request.GET.get('discord_id')
        request_user = request.GET.get('user')
        request_pass = request.GET.get('pass')

        if (not os.environ['REG_USERNAME'] == request_user and not os.environ['REG_PASSWORD'] == request_pass):
            data = {
                    'discord_id': discord_id,
                    'request_user': request_user,
                    'request_pass': request_pass
                }
            return JsonResponse(data)

        if (not discord_id):
            return HttpResponse('Discord id not specified.')

        if not Application.objects.filter(discord_id=discord_id):
            return HttpResponse('no_app')
        else:
            data = None 
            app: Application = Application.objects.get(discord_id=discord_id)
            user: User = User.objects.get(id=app.user_id)

            if user.team_id:
                team = Team.objects.get(id=user.team_id)

                data = {
                    'discord_id': discord_id,
                    'name': f"{app.first_name} {app.last_name}",
                    'team_name': team.name
                }
            else:
                data = {
                    'discord_id': discord_id,
                    'name': f"{app.first_name} {app.last_name}",
                    'team_name': None
                }
            
            return JsonResponse(data)