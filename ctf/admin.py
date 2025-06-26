from django.contrib import admin
from .models import Category, Challenge, Team, UserProfile, ChallengeFile, Hint, Submission, HintUnlock

admin.site.register(Category)
admin.site.register(Challenge)
admin.site.register(Team)
admin.site.register(UserProfile)
admin.site.register(ChallengeFile)
admin.site.register(Hint)
admin.site.register(Submission)
admin.site.register(HintUnlock)
