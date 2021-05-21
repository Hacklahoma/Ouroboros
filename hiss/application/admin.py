# pylint: disable=C0330
import csv
from typing import List, Tuple

from django import forms
from django.conf import settings
from django.contrib import admin
from django.db import transaction
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.contrib.admin.filters import RelatedOnlyFieldListFilter
from django_admin_listfilter_dropdown.filters import (
    DropdownFilter,
    ChoiceDropdownFilter,
)
from rangefilter.filter import DateRangeFilter

from application.emails import send_confirmation_email
from application.models import (
    Application,
    Wave,
    STATUS_ADMITTED,
    STATUS_REJECTED,
    RACES,
)
from shared.admin_functions import send_mass_html_mail


class ApplicationAdminForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = "__all__"
        widgets = {
            "gender": forms.RadioSelect,
            "grad_year": forms.RadioSelect,
            "status": forms.RadioSelect,
        }

# Build the approval email from the template
def build_approval_email(
    application: Application, confirmation_deadline: timezone.datetime
) -> Tuple[str, str, str, None, List[str]]:
    """
    Creates a datatuple of (subject, message, html_message, from_email, [to_email]) indicating that a `User`'s
    application has been approved.
    """
    subject = f"Your Hacklahoma application has been approved!"

    context = {
        "first_name": application.first_name,
        "event_name": "Hacklahoma",
        "confirmation_deadline": confirmation_deadline,
    }
    html_message = render_to_string("application/emails/approved.html", context)
    message = strip_tags(html_message)
    return subject, message, html_message, None, [application.user.email]


def build_rejection_email(application: Application) -> Tuple[str, str, None, List[str]]:
    """
    Creates a datatuple of (subject, message, html_message, from_email, [to_email]) indicating that a `User`'s
    application has been rejected.
    """
    subject = f"Regarding your Hacklahoma application"

    context = {"first_name": application.first_name, "event_name": "Hacklahoma"}
    html_message = render_to_string("application/emails/rejected.html", context)
    message = strip_tags(html_message)
    return subject, message, html_message, None, [application.user.email]


def approve(_modeladmin, _request: HttpRequest, queryset: QuerySet) -> None:
    """
    Sets the value of the `approved` field for the selected `Application`s to `True`, creates an RSVP deadline for
    each user based on how many days each wave gives to RSVP, and then emails all of the users to inform them that
    their applications have been approved.
    """
    email_tuples = []
    with transaction.atomic():
        for application in queryset:
            deadline = timezone.now().replace(
                hour=23, minute=59, second=59, microsecond=0
            ) + timezone.timedelta(application.wave.num_days_to_rsvp)
            application.status = STATUS_ADMITTED
            application.confirmation_deadline = deadline
            email_tuples.append(build_approval_email(application, deadline))
            application.save()
    send_mass_html_mail(email_tuples)


def reject(_modeladmin, _request: HttpRequest, queryset: QuerySet) -> None:
    """
    Sets the value of the `approved` field for the selected `Application`s to `False`
    """
    email_tuples = []
    with transaction.atomic():
        for application in queryset:
            application.status = STATUS_REJECTED
            email_tuples.append(build_rejection_email(application))
            application.save()
    send_mass_html_mail(email_tuples)


def resend_confirmation(_modeladmin, _request: HttpRequest, queryset: QuerySet) -> None:
    """
    Resends the confirmation email to the selected applications.
    """
    for application in queryset:
        send_confirmation_email(application)

def interested_in_hacklahoma_export(_modeladmin, _request: HttpRequest, queryset: QuerySet):
    """
    Exports the emails of selected users interested in Hacklahoma
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="emails.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "First Name",
            "Last Name",
            "E-Mail",
            "Phone Number",
            "Current Level of Study",
            "School",
            "Anticipated Graduation Year",
            "Resume"
        ]
    )
    for instance in queryset:
        instance: Application = instance

        if instance.interested_in_hacklahoma == True and str(instance.school) == "University of Oklahoma":
            school = None

            if str(instance.school) == "Other":
                school = instance.school_other
            else:
                school = instance.school

            study_switch = {
                "H": "High School",
                "T": "Tech School",
                "U": "Undergrad University",
                "G": "Graduate University"
            }

            writer.writerow(
                [
                    instance.first_name,
                    instance.last_name,
                    instance.user.email,
                    instance.phone_number,
                    study_switch.get(instance.level_of_study),
                    school,
                    instance.graduation_year
                ]
            )

    return response


def export_application_emails(_modeladmin, _request: HttpRequest, queryset: QuerySet):
    """
    Exports the emails related to the selected `Application`s to a CSV file
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="emails.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "First Name",
            "Last Name",
            "E-Mail",
            "Phone Number",
            "School Name",
            "Level Of Study"
        ]
    )
    for instance in queryset:
        instance: Application = instance
        school = None

        if str(instance.school) == "Other":
            school = instance.school_other
        else:
            school = instance.school

        study_switch = {
            "H": "High School",
            "T": "Tech School",
            "U": "Undergrad University",
            "G": "Graduate University"
        }

        writer.writerow(
            [
                instance.first_name,
                instance.last_name,
                instance.user.email,
                instance.phone_number,
                school,
                study_switch.get(instance.level_of_study)
            ]
        )

    return response

def export_application_tshirts(_modeladmin, _request: HttpRequest, queryset: QuerySet):
    """
    Exports the data needed to ship out tshirts and other swag
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="deets.csv"'

    

    writer = csv.writer(response)
    writer.writerow(
        [
            "First Name",
            "Last Name",
            "Gender",
            "Major",
            "Graduation Year"
        ]
    )

    gender = None

    for instance in queryset:
        instance: Application = instance

        if str(instance.gender) == "Other":
            gender = instance.gender_other
        else:
            gender = instance.gender

        if instance.shipping_address == True and instance.checked_in == True:
            writer.writerow(
                [
                    instance.first_name,
                    instance.last_name,
                    gender,
                    instance.major,
                    instance.graduation_year
                ] 
            )


    return response

def export_application_prizes(_modeladmin, _request: HttpRequest, queryset: QuerySet):
    """
    Exports the prizes 
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="prizes.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "First Name",
            "Last Name",
            "Prizes"
        ]
    )
    for instance in queryset:
        instance: Application = instance

        writer.writerow(
            [
                instance.first_name,
                instance.last_name,
                instance.question3
            ]
        )

    return response


def custom_titled_filter(title):
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance

    return Wrapper


class RaceFilter(admin.SimpleListFilter):
    title = "Race"
    parameter_name = "race"

    def lookups(self, request: HttpRequest, model_admin) -> List[Tuple[str, str]]:
        return RACES

    def queryset(self, request: HttpRequest, queryset: QuerySet):
        if self.value():
            return queryset.filter(race__contains=self.value())
        return queryset


class ApplicationAdmin(admin.ModelAdmin):
    form = ApplicationAdminForm
    readonly_fields = [
        "datetime_submitted",
        "user",
        "is_a_walk_in",
        "user_email",
    ]
    list_filter = (
        ("school", RelatedOnlyFieldListFilter),
        ("status", ChoiceDropdownFilter),
        ("gender", ChoiceDropdownFilter),
        ("num_hackathons_attended", ChoiceDropdownFilter),
        ("datetime_submitted", DateRangeFilter),
        #RaceFilter,
    )
    list_display = (
        "first_name",
        "last_name",
        "school",
        "user_email",
        "datetime_submitted",
        "status",
        "discord_id",
        "checked_in"
    )
    fieldsets = [
        ("Related Objects", {"fields": ["user"]}),
        ("Status", {"fields": ["status"]}),
        (
            "Personal Information",
            {
                "fields": [
                    "first_name",
                    "last_name",
                    "school_email",
                    "phone_number",
                    "birthday",
                    "social_links",
                    "question1",
                    "question2",
                    "question3",
                    "resume",
                ]
            },
        ),
        (
            "Demographic Information",
            {
                "fields": [
                    "school",
                    "school_other",
                    "gender",
                    "gender_other",
                    "pronouns",
                    "race",
                    "race_other",
                    "level_of_study",
                    "graduation_year",
                    "major",
                    "num_hackathons_attended",
                ]
            },
        ),
        (
            "Logistical Information",
            {
                "fields": [
                    "shirt_size",
                    "where_did_you_hear",
                    "where_did_you_hear_other",
                    "shipping_address",
                    "address1",
                    "address2",
                    "city",
                    "state",
                    "zip_code",
                    "interested_in_hacklahoma",
                ]
            },
        ),
        ("Confirmation Deadline", {"fields": ["confirmation_deadline"]}),
        ("Miscellaneous", {"fields": ["notes"]}),
        ("Discord", {"fields":["discord_id","checked_in"]}),
    ]
    list_per_page = 2000

    approve.short_description = "Approve Selected Applications"
    reject.short_description = "Reject Selected Applications"
    export_application_emails.short_description = (
        "Export Emails for Selected Applications"
    )
    export_application_tshirts.short_description = (
        "Export Tshirt Size and Addresses for Selected Applications"
    )
    resend_confirmation.short_description = (
        "Resend Confirmation to Selected Applications"
    )
    interested_in_hacklahoma_export.short_description = (
        "Interested in Hacklahoma"
    )
    export_application_prizes.short_description = (
        "Export Application Prizes"
    )

    actions = [approve, reject, export_application_emails, resend_confirmation, export_application_tshirts, interested_in_hacklahoma_export, export_application_prizes]

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    @staticmethod
    def user_email(obj: Application) -> str:
        return obj.user.email

    @staticmethod
    def is_a_walk_in(obj: Application) -> bool:
        return obj.wave.is_walk_in_wave


class WaveAdmin(admin.ModelAdmin):
    list_display = ("start", "end", "is_walk_in_wave")


admin.site.register(Application, ApplicationAdmin)
admin.site.register(Wave, WaveAdmin)
