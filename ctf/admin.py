from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from django.utils import timezone
from .models import (
    CompetitionSettings, Category, Challenge, Team, UserProfile, 
    ChallengeFile, Hint, Submission, HintUnlock
)

@admin.register(CompetitionSettings)
class CompetitionSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Competition Information', {
            'fields': ('competition_name', 'description', 'logo_url')
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time', 'freeze_time', 'freeze_scoreboard'),
            'description': 'Set competition start/end times and scoreboard freezing'
        }),
        ('Registration', {
            'fields': ('registration_enabled', 'team_registration_enabled', 'max_team_size')
        }),
        ('Features', {
            'fields': ('show_scoreboard', 'enable_hints', 'dynamic_scoring')
        }),
        ('Contact', {
            'fields': ('contact_info',)
        })
    )
    
    def has_add_permission(self, request):
        # Only allow one settings instance
        return not CompetitionSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of settings
        return False
    
    def get_object(self, request, object_id, from_field=None):
        # Always return the singleton instance
        return CompetitionSettings.get_settings()
    
    def changelist_view(self, request, extra_context=None):
        # Redirect to the single settings instance
        settings = CompetitionSettings.get_settings()
        return self.change_view(request, str(settings.pk), '', extra_context)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'challenge_count', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at']
    
    def challenge_count(self, obj):
        return obj.challenges.count()
    challenge_count.short_description = 'Challenges'

class ChallengeFileInline(admin.TabularInline):
    model = ChallengeFile
    extra = 1
    fields = ['file', 'filename', 'file_size_display']
    readonly_fields = ['file_size_display']
    
    def file_size_display(self, obj):
        if obj.file and hasattr(obj.file, 'size'):
            size = obj.file.size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        return "N/A"
    file_size_display.short_description = 'File Size'

class HintInline(admin.TabularInline):
    model = Hint
    extra = 1
    fields = ['text', 'cost', 'order', 'unlock_count_display']
    readonly_fields = ['unlock_count_display']
    
    def unlock_count_display(self, obj):
        if obj.pk:
            return obj.unlocks.count()
        return 0
    unlock_count_display.short_description = 'Unlocks'

@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'difficulty', 'current_value_display', 'author',
        'hidden', 'solve_count', 'attempt_count', 'created_at'
    ]
    list_filter = ['category', 'difficulty', 'hidden', 'created_at', 'author']
    search_fields = ['title', 'description', 'author']
    list_editable = ['hidden']
    inlines = [ChallengeFileInline, HintInline]
    filter_horizontal = ['requirements']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'author'),
            'description': 'Basic challenge information. Description supports Markdown.'
        }),
        ('Challenge Settings', {
            'fields': ('value', 'flag', 'case_sensitive', 'difficulty', 'hidden'),
            'description': 'Core challenge settings'
        }),
        ('Advanced Settings', {
            'fields': ('max_attempts', 'connection_info'),
            'classes': ('collapse',),
            'description': 'Optional advanced settings'
        }),
        ('Prerequisites', {
            'fields': ('requirements',),
            'classes': ('collapse',),
            'description': 'Challenges that must be solved before this one becomes available'
        }),
        ('Dynamic Scoring', {
            'fields': ('initial_value', 'minimum_value', 'decay_factor'),
            'classes': ('collapse',),
            'description': 'Settings for dynamic scoring (if enabled in competition settings)'
        }),
    )
    
    def current_value_display(self, obj):
        current = obj.current_value
        if current != obj.value:
            return format_html(
                '<span style="color: orange;" title="Dynamic scoring active">{} (was {})</span>',
                current, obj.value
            )
        return obj.value
    current_value_display.short_description = 'Current Value'
    current_value_display.admin_order_field = 'value'
    
    def solve_count(self, obj):
        count = obj.submissions.filter(correct=True).count()
        if count > 0:
            url = reverse('admin:ctf_submission_changelist') + f'?challenge__id__exact={obj.id}&correct__exact=1'
            return format_html('<a href="{}" style="color: green;">{}</a>', url, count)
        return count
    solve_count.short_description = 'Solves'
    
    def attempt_count(self, obj):
        count = obj.submissions.count()
        if count > 0:
            url = reverse('admin:ctf_submission_changelist') + f'?challenge__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    attempt_count.short_description = 'Attempts'
    
    actions = ['duplicate_challenge', 'hide_challenges', 'show_challenges']
    
    def duplicate_challenge(self, request, queryset):
        for challenge in queryset:
            # Create a copy
            new_challenge = Challenge.objects.create(
                title=f"{challenge.title} (Copy)",
                description=challenge.description,
                category=challenge.category,
                value=challenge.value,
                flag=challenge.flag + "_copy",
                case_sensitive=challenge.case_sensitive,
                difficulty=challenge.difficulty,
                author=challenge.author,
                max_attempts=challenge.max_attempts,
                connection_info=challenge.connection_info,
                initial_value=challenge.initial_value,
                minimum_value=challenge.minimum_value,
                decay_factor=challenge.decay_factor,
                hidden=True  # Hidden by default
            )
            
            # Copy files
            for file in challenge.files.all():
                ChallengeFile.objects.create(
                    challenge=new_challenge,
                    file=file.file,
                    filename=file.filename
                )
            
            # Copy hints
            for hint in challenge.hints.all():
                Hint.objects.create(
                    challenge=new_challenge,
                    text=hint.text,
                    cost=hint.cost,
                    order=hint.order
                )
        
        self.message_user(request, f'{len(queryset)} challenge(s) duplicated successfully.')
    duplicate_challenge.short_description = 'Duplicate selected challenges'
    
    def hide_challenges(self, request, queryset):
        updated = queryset.update(hidden=True)
        self.message_user(request, f'{updated} challenge(s) hidden.')
    hide_challenges.short_description = 'Hide selected challenges'
    
    def show_challenges(self, request, queryset):
        updated = queryset.update(hidden=False)
        self.message_user(request, f'{updated} challenge(s) made visible.')
    show_challenges.short_description = 'Show selected challenges'

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'affiliation', 'member_count', 'total_score', 'is_active', 'registered_at']
    list_filter = ['is_active', 'registered_at', 'affiliation']
    search_fields = ['name', 'affiliation']
    list_editable = ['is_active']
    filter_horizontal = ['members']
    
    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'
    
    actions = ['activate_teams', 'deactivate_teams']
    
    def activate_teams(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} teams were successfully activated.')
    activate_teams.short_description = 'Activate selected teams'
    
    def deactivate_teams(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} teams were successfully deactivated.')
    deactivate_teams.short_description = 'Deactivate selected teams'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'display_name', 'website', 'created_at']
    search_fields = ['user__username', 'user__email', 'display_name']
    list_filter = ['created_at']

@admin.register(ChallengeFile)
class ChallengeFileAdmin(admin.ModelAdmin):
    list_display = ['challenge', 'filename', 'file_size_display', 'file_type', 'uploaded_at']
    list_filter = ['uploaded_at', 'challenge__category']
    search_fields = ['challenge__title', 'filename']
    readonly_fields = ['file_size_display', 'file_type']
    
    def file_size_display(self, obj):
        if obj.file and hasattr(obj.file, 'size'):
            size = obj.file.size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        return "N/A"
    file_size_display.short_description = 'File Size'
    
    def file_type(self, obj):
        if obj.file and obj.filename:
            ext = obj.filename.split('.')[-1].upper() if '.' in obj.filename else 'Unknown'
            return ext
        return "N/A"
    file_type.short_description = 'Type'

@admin.register(Hint)
class HintAdmin(admin.ModelAdmin):
    list_display = ['challenge', 'preview_text', 'cost', 'order', 'unlock_count']
    list_filter = ['cost', 'challenge__category']
    search_fields = ['challenge__title', 'text']
    list_editable = ['cost', 'order']
    
    def preview_text(self, obj):
        return obj.text[:50] + ('...' if len(obj.text) > 50 else '')
    preview_text.short_description = 'Text'
    
    def unlock_count(self, obj):
        return obj.unlocks.count()
    unlock_count.short_description = 'Unlocks'

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'team', 'challenge', 'submitted_flag', 'correct', 'timestamp']
    list_filter = ['correct', 'timestamp', 'challenge__category', 'team']
    search_fields = ['user__username', 'challenge__title', 'submitted_flag']
    readonly_fields = ['timestamp', 'correct', 'ip_address']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ['user', 'challenge', 'submitted_flag']
        return self.readonly_fields

@admin.register(HintUnlock)
class HintUnlockAdmin(admin.ModelAdmin):
    list_display = ['user', 'team', 'hint_challenge', 'hint_cost', 'unlocked_at']
    list_filter = ['unlocked_at', 'hint__challenge__category']
    search_fields = ['user__username', 'hint__challenge__title']
    readonly_fields = ['unlocked_at']
    
    def hint_challenge(self, obj):
        return obj.hint.challenge.title
    hint_challenge.short_description = 'Challenge'
    
    def hint_cost(self, obj):
        return obj.hint.cost
    hint_cost.short_description = 'Cost'

# Customize admin site
from django.contrib.admin import AdminSite
from django.template.response import TemplateResponse
from django.urls import path

class CTFAdminSite(AdminSite):
    site_header = "EXCELR8 CTF Administration"
    site_title = "EXCELR8 CTF Admin" 
    index_title = "Competition Management Dashboard"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='ctf_dashboard'),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        """Custom dashboard with competition statistics"""
        from django.db.models import Count, Q
        
        settings = CompetitionSettings.get_settings()
        
        # Get statistics
        stats = {
            'total_challenges': Challenge.objects.count(),
            'visible_challenges': Challenge.objects.filter(hidden=False).count(),
            'total_teams': Team.objects.filter(is_active=True).count(),
            'total_users': UserProfile.objects.count(),
            'total_submissions': Submission.objects.count(),
            'correct_submissions': Submission.objects.filter(correct=True).count(),
            'categories': Category.objects.annotate(
                challenge_count=Count('challenges')
            ).order_by('-challenge_count'),
            'recent_submissions': Submission.objects.select_related(
                'user', 'challenge', 'team'
            ).order_by('-timestamp')[:10],
            'top_teams': Team.objects.filter(is_active=True).order_by(
                '-submissions__timestamp'
            )[:10],
            'competition_settings': settings,
        }
        
        context = {
            **self.each_context(request),
            'stats': stats,
            'title': 'Competition Dashboard',
        }
        
        return TemplateResponse(request, 'admin/ctf_dashboard.html', context)

# Replace the default admin site
admin_site = CTFAdminSite(name='ctf_admin')

# Re-register all models with the custom admin site
admin_site.register(CompetitionSettings, CompetitionSettingsAdmin)
admin_site.register(Category, CategoryAdmin)  
admin_site.register(Challenge, ChallengeAdmin)
admin_site.register(Team, TeamAdmin)
admin_site.register(UserProfile, UserProfileAdmin)
admin_site.register(ChallengeFile, ChallengeFileAdmin)
admin_site.register(Hint, HintAdmin)
admin_site.register(Submission, SubmissionAdmin)
admin_site.register(HintUnlock, HintUnlockAdmin)

# Keep the default registrations for compatibility
admin.site.site_header = "EXCELR8 CTF Administration"
admin.site.site_title = "EXCELR8 CTF Admin"
admin.site.index_title = "Competition Management Dashboard"
