from django.contrib import admin
from .models import Vote, Donation, AppTranslation

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('receipt_code', 'voter_phone', 'candidate_name', 'post', 'commune', 'created_at')
    list_filter = ('post', 'commune', 'created_at')
    search_fields = ('receipt_code', 'voter__phone', 'candidate__first_name', 'candidate__last_name', 'commune')
    readonly_fields = ('id', 'receipt_code', 'voter', 'candidate', 'post', 'commune', 'ip_hash', 'created_at')

    def voter_phone(self, obj):
        return obj.voter.phone
    voter_phone.short_description = "Patisipan"

    def candidate_name(self, obj):
        return f"{obj.candidate.first_name} {obj.candidate.last_name}"
    candidate_name.short_description = "Kandida Chwazi"

    def has_add_permission(self, request):
        # Empêche l'ajout manuel de votes depuis l'interface admin pour préserver l'intégrité
        return False


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('donor_name', 'amount', 'currency', 'payment_method', 'transaction_reference', 'donor_contact', 'created_at')
    list_filter = ('currency', 'payment_method', 'created_at')
    search_fields = ('donor_name', 'donor_contact', 'transaction_reference', 'message')
    readonly_fields = ('id', 'created_at')


@admin.register(AppTranslation)
class AppTranslationAdmin(admin.ModelAdmin):
    list_display = ('key', 'category', 'text_ht_preview', 'text_fr_preview', 'text_en_preview', 'updated_at')
    list_filter = ('category', 'updated_at')
    search_fields = ('key', 'text_ht', 'text_fr', 'text_en', 'description')
    list_editable = ()

    def text_ht_preview(self, obj):
        return (obj.text_ht[:50] + '...') if len(obj.text_ht) > 50 else obj.text_ht
    text_ht_preview.short_description = "Kreyòl"

    def text_fr_preview(self, obj):
        return (obj.text_fr[:50] + '...') if len(obj.text_fr) > 50 else obj.text_fr
    text_fr_preview.short_description = "Français"

    def text_en_preview(self, obj):
        return (obj.text_en[:50] + '...') if len(obj.text_en) > 50 else obj.text_en
    text_en_preview.short_description = "English"

