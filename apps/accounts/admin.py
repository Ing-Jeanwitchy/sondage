from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from .models import User, CandidateProfile, SurveyConfig, VoterProfile

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone', 'username', 'role', 'is_verified', 'is_staff', 'created_at')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_superuser')
    search_fields = ('phone', 'username', 'email')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Informations personnelles', {'fields': ('username', 'first_name', 'last_name', 'email')}),
        ('Rôles & Vérifications', {'fields': ('role', 'is_verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates importantes', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'username', 'password', 'role', 'is_verified'),
        }),
    )

@admin.action(description="Approuver les candidatures sélectionnées")
def approve_candidates(modeladmin, request, queryset):
    queryset.update(status='APPROVED', validated_at=timezone.now(), rejection_reason='')

@admin.action(description="Rejeter les candidatures sélectionnées")
def reject_candidates(modeladmin, request, queryset):
    queryset.update(status='REJECTED', validated_at=timezone.now())

@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'post', 'commune', 'status', 'created_at')
    list_filter = ('post', 'commune', 'status', 'created_at')
    search_fields = ('first_name', 'last_name', 'slogan', 'user__phone')
    actions = [approve_candidates, reject_candidates]
    readonly_fields = ('created_at', 'updated_at')

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = "Nom du candidat"

@admin.register(SurveyConfig)
class SurveyConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_registration_open', 'registration_deadline', 'is_voting_open', 'support_whatsapp', 'support_email', 'updated_at')
    list_editable = ('is_registration_open', 'is_voting_open')
    fieldsets = (
        ('Peryòd & Kalandriye Sondaj', {
            'fields': ('is_registration_open', 'registration_deadline', 'is_voting_open', 'show_official_publications')
        }),
        ('Kontak Sipò ("Bezwen Èd pou Fè Don an ?")', {
            'fields': ('support_whatsapp', 'support_email'),
            'description': 'Mete nimewo WhatsApp ak Imèl ofisyèl ki afiche pou asiste sitwayen k ap fè don yo.'
        }),
        ('Peman MonCash & Natcash', {
            'fields': ('donation_moncash_number', 'donation_moncash_name', 'donation_natcash_number', 'donation_natcash_name')
        }),
        ('Peman Dyaspora (Zelle & CashApp)', {
            'fields': ('donation_zelle_info', 'donation_zelle_name', 'donation_cashapp_tag')
        }),
        ('Peman Labank', {
            'fields': ('donation_bank_info', 'donation_bank_name')
        }),
    )

@admin.register(VoterProfile)
class VoterProfileAdmin(admin.ModelAdmin):
    list_display = ('phone_display', 'commune', 'commune_locked', 'has_voted_senateur', 'has_voted_maire', 'created_at')
    list_filter = ('commune', 'commune_locked', 'has_voted_senateur', 'has_voted_maire')
    search_fields = ('user__phone', 'commune')
    readonly_fields = ('created_at', 'updated_at')

    def phone_display(self, obj):
        return obj.user.phone
    phone_display.short_description = "Téléphone"

