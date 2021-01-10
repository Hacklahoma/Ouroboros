from django import views
from django.conf import settings
from django.contrib.auth import get_user_model, login, authenticate
from django.contrib.auth import views as auth_views
from django.contrib.auth import mixins
from django.contrib.sites import shortcuts as site_shortcuts
from django.contrib.sites.requests import RequestSite
from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import generic

from customauth import forms as customauth_forms
from customauth.tokens import email_confirmation_generator
from user.models import User

from application.models import (
    Application,
    Wave,
    STATUS_CONFIRMED,
    STATUS_DECLINED,
    STATUS_ADMITTED,
)


def send_confirmation_email(curr_domain: RequestSite, user: User) -> None:
    subject = "Confirm your email address!"
    template_name = "registration/emails/activate.html"
    context = {
        "user": user,
        "domain": curr_domain,
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": email_confirmation_generator.make_token(user),
        "event_name": "Hacklahoma",
    }
    user.send_html_email(template_name, context, subject)


class RegistrationLoginView(auth_views.LoginView):
    """
    Discord Authentication portion of registration
    """

    template_name = "registration/login.html"
    form_class = customauth_forms.LoginForm


class SignupView(generic.FormView):
    form_class = customauth_forms.SignupForm
    template_name = "registration/signup.html"

    def form_valid(self, form):
        user: User = form.save(commit=False)
        user.is_active = False
        user.save()
        curr_domain = site_shortcuts.get_current_site(self.request)
        send_confirmation_email(curr_domain, user)
        return render(self.request, "registration/check_inbox.html")


class ResendActivationEmailView(generic.FormView):
    form_class = customauth_forms.ResendActivationEmailForm
    template_name = "registration/resend_activation.html"

    def form_valid(self, form):
        user: User = get_object_or_404(User, email=form.cleaned_data["email"])
        curr_domain = site_shortcuts.get_current_site(self.request)
        send_confirmation_email(curr_domain, user)
        return render(self.request, "registration/check_inbox.html")


class ActivateView(views.View):
    def get(self, request, *_args, **kwargs):
        user = None
        try:
            uid = force_text(urlsafe_base64_decode(kwargs["uidb64"]))
            user = get_user_model().objects.get(id=int(uid))
        except (
            TypeError,
            ValueError,
            OverflowError,
            get_user_model().DoesNotExist,
        ) as e:
            print(e)
        if user is not None and email_confirmation_generator.check_token(
            user, kwargs["token"]
        ):
            user.is_active = True
            user.save()
            login(request, user)
            return redirect(reverse_lazy("status"))
        else:
            return HttpResponse("Activation link is invalid.")


class PlaceholderPasswordResetView(auth_views.PasswordResetView):
    """
    Uses PlaceholderPasswordResetForm instead of default PasswordResetForm.
    """

    form_class = customauth_forms.PlaceholderPasswordResetForm
    html_email_template_name = "registration/emails/password_reset.html"
    email_template_name = "registration/emails/password_reset.html"
    subject_template_name = "registration/emails/password_reset_subject.txt"
    success_url = reverse_lazy("customauth:password_reset_done")
    extra_email_context = {"event_name": "Hacklahoma"}


class PlaceholderPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """
    Uses PlaceholderSetPasswordForm instead of default SetPasswordForm.
    """

    template_name = "registration/password_reset_confirm.html"
    form_class = customauth_forms.PlaceholderSetPasswordForm
    success_url = reverse_lazy("customauth:login")

class DiscordAuthView(auth_views.LoginView):
    """
    Discord Authentication portion of registration
    """

    template_name = "registration/discord_auth.html"
    form_class = customauth_forms.DiscordAuthForm

class CheckDiscordId(mixins.LoginRequiredMixin, views.View):
    """
    Checks to see if a discord id has been used already or if the current user 
    already has a discord id linked to it.
    """

    queryset = Application.objects.all()

    def get(self, request, *_args, **kwargs):
        app = None
        discord_id = None
        try:
            pk = self.kwargs["pk"]
            app: Application = Application.objects.get(pk=pk)
            discord_id = reqeust.GET.get("id")
        except (
            TypeError,
            ValueError,
            OverflowError,
            get_user_model().DoesNotExist,
        ) as e:
            print(e)
        if app is not None:
            if Application.objects.get(discord_id=discord_id is not None):
                return HttpResponse("Discord id already being using. Please contact a Hacklahoma team member through the Hacklahoma Discord or through team@hacklahoma.org.")
            elif app.discord_id:
                return HttpResponse("Application already has a discord id linked to it. Please contact a Hacklahoma team member through the Hacklahoma Discord or through team@hacklahoma.org.")
            elif app.status == STATUS_DECLINED:
                return HttpResponse("Application was declined. Please contact a Hacklahoma team member through the Hacklahoma Discord or through team@hacklahoma.org.")
            else:
                return HttpResponse(f"This is where we enter the matrix or something.\ndiscord_id: {discord_id}\napp: {app}")
        else:
            return HttpResponse("Application")