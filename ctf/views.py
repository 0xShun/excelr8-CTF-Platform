from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.contrib.auth.models import User
import json

from .models import (
    Challenge, Category, Team, Submission, Hint, HintUnlock, 
    UserProfile, ChallengeFile, CompetitionSettings
)
from django.contrib.auth.hashers import make_password, check_password
from .forms import (
    TeamRegistrationForm, ChallengeSubmissionForm, HintUnlockForm,
    CustomUserRegistrationForm, TeamJoinForm, UserProfileForm
)

def home(request):
    """Home page with basic stats"""
    # Get competition settings
    settings = CompetitionSettings.get_settings()
    total_solves = Submission.objects.filter(correct=True).count()
    
    context = {
        'total_challenges': Challenge.objects.filter(hidden=False).count(),
        'total_teams': Team.objects.filter(is_active=True).count(),
        'total_users': User.objects.count(),
        'total_solves': total_solves,
        'recent_solves': Submission.objects.filter(correct=True).order_by('-timestamp')[:5],
        'competition_settings': settings,
        'competition_start': settings.start_time.isoformat() if settings.start_time else None,
        'competition_end': settings.end_time.isoformat() if settings.end_time else None,
    # Epoch millisecond timestamps for robust client-side countdown logic
    'competition_start_ts': int(settings.start_time.timestamp() * 1000) if settings.start_time else None,
    # Provide a JS-friendly epoch millisecond timestamp to avoid Date parsing issues client-side
    'competition_end_ts': int(settings.end_time.timestamp() * 1000) if settings.end_time else None,
    }
    
    # Add user-specific data if authenticated
    if request.user.is_authenticated:
        user_solves = Submission.objects.filter(user=request.user, correct=True)
        # Calculate individual (non-team) score: sum of challenge values for correct user submissions minus hint costs user unlocked
        individual_score = 0
        for s in user_solves:
            individual_score += s.challenge.value
        # Deduct hint costs (user-specific)
        hint_cost_total = 0
        from .models import HintUnlock  # local import to avoid circular if any
        for unlock in HintUnlock.objects.filter(user=request.user):
            hint_cost_total += unlock.hint.cost
        individual_score = max(0, individual_score - hint_cost_total)
        context.update({
            'user_solved_count': user_solves.count(),
            'recent_solves': user_solves.order_by('-timestamp')[:5],
            'individual_score': individual_score,
        })
    
    return render(request, 'ctf/home.html', context)

def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            # Hash and store team password
            raw_password = form.cleaned_data.get('team_password')
            if raw_password:
                team.password_hash = make_password(raw_password)
            team.save()
            team.members.add(request.user)
            messages.success(request, f'Team "{team.name}" registered successfully!')
            return redirect('ctf:challenge_list')
        form = CustomUserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile(request):
    """User profile view"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    current_team = request.user.teams.filter(is_active=True).first()
    solved_challenges = Submission.objects.filter(user=request.user, correct=True).count()
    total_score = current_team.total_score if current_team else 0
    
    context = {
        'profile': profile,
        'current_team': current_team,
        'solved_challenges': solved_challenges,
        'total_score': total_score,
    }
    return render(request, 'ctf/profile.html', context)

@login_required
def edit_profile(request):
    """Edit user profile"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('ctf:profile')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'ctf/edit_profile.html', {'form': form})

def team_register(request):
    """Team registration view"""
    # Enforce single-team membership
    existing_team = request.user.teams.filter(is_active=True).first()
    if existing_team:
        messages.info(request, f'You are already in team "{existing_team.name}". Leave it before creating a new one.')
        return redirect('ctf:profile')
    if request.method == 'POST':
        form = TeamRegistrationForm(request.POST)
        if form.is_valid():
            team = form.save()
            # Add current user to team
            team.members.add(request.user)
            messages.success(request, f'Team "{team.name}" registered successfully!')
            return redirect('ctf:challenge_list')
    else:
        form = TeamRegistrationForm()
    return render(request, 'ctf/team_register.html', {'form': form})

@login_required
def team_join(request):
    """Join existing team"""
    # Enforce single-team membership
    existing_team = request.user.teams.filter(is_active=True).first()
    if existing_team:
        messages.info(request, f'You are already in team "{existing_team.name}". Leave it before joining another team.')
        return redirect('ctf:profile')
    if request.method == 'POST':
        form = TeamJoinForm(request.POST)
        if form.is_valid():
            team_name = form.cleaned_data['team_name']
            try:
                team = Team.objects.get(name=team_name)
                team.members.add(request.user)
                messages.success(request, f'Successfully joined team "{team.name}"!')
                return redirect('ctf:challenge_list')
            except Team.DoesNotExist:
                messages.error(request, 'Team not found or password incorrect.')
    else:
        form = TeamJoinForm()
    
    return render(request, 'ctf/team_join.html', {'form': form})

@login_required
@require_POST
def leave_team(request):
    """Allow user to leave their current team"""
    team = request.user.teams.filter(is_active=True).first()
    if not team:
        messages.info(request, 'You are not in a team.')
        return redirect('ctf:profile')
    team.members.remove(request.user)
    messages.success(request, f'You left team "{team.name}".')
    return redirect('ctf:profile')
@login_required
def challenge_list(request):
    """List all visible challenges"""
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search', '')
    
    challenges = Challenge.objects.filter(hidden=False)
    
    if category_filter:
        challenges = challenges.filter(category__id=category_filter)
    
    if search_query:
        challenges = challenges.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    challenges = challenges.select_related('category').prefetch_related('submissions')
    
    # Add solve status for current user
    for challenge in challenges:
        challenge.user_solved = challenge.is_solved_by_user(request.user)
    
    categories = Category.objects.all()
    
    context = {
        'challenges': challenges,
        'categories': categories,
        'selected_category': category_filter,
        'search_query': search_query,
    }
    return render(request, 'ctf/challenge_list.html', context)

@login_required
def challenge_detail(request, pk):
    """Challenge detail and flag submission view"""
    challenge = get_object_or_404(Challenge, pk=pk, hidden=False)
    
    # Check if user already solved this challenge
    user_solved = challenge.is_solved_by_user(request.user)
    
    # Get user's unlocked hints
    user_unlocked_hints = HintUnlock.objects.filter(
        user=request.user, 
        hint__challenge=challenge
    ).values_list('hint_id', flat=True)
    
    # Get hints with unlock status
    hints = []
    for hint in challenge.hints.all().order_by('order'):
        hints.append({
            'hint': hint,
            'unlocked': hint.id in user_unlocked_hints
        })
    
    # Handle flag submission
    if request.method == 'POST' and not user_solved:
        form = ChallengeSubmissionForm(
            request.POST, 
            user=request.user, 
            challenge=challenge
        )
        if form.is_valid():
            submission = form.save()
            if submission.correct:
                messages.success(request, '🎉 Correct flag! Well done!')
            else:
                messages.error(request, '❌ Incorrect flag. Try again!')
            return redirect('ctf:challenge_detail', pk=challenge.pk)
    else:
        form = ChallengeSubmissionForm()
    
    files = challenge.files.all()
    recent_submissions = Submission.objects.filter(
        challenge=challenge, user=request.user
    ).order_by('-timestamp')[:5]
    
    context = {
        'challenge': challenge,
        'form': form,
        'hints': hints,
        'files': files,
        'user_solved': user_solved,
        'recent_submissions': recent_submissions,
    }
    return render(request, 'ctf/challenge_detail.html', context)

@login_required
@require_POST
def unlock_hint(request, hint_id):
    """Unlock a hint for points"""
    hint = get_object_or_404(Hint, pk=hint_id)
    
    # Check if hint is already unlocked
    unlock, created = HintUnlock.objects.get_or_create(
        user=request.user, 
        hint=hint,
        defaults={
            'team': request.user.teams.filter(is_active=True).first()
        }
    )
    
    if created:
        messages.success(request, f'Hint unlocked! -{hint.cost} points')
    else:
        messages.info(request, 'Hint already unlocked')
    
    return redirect('ctf:challenge_detail', pk=hint.challenge.pk)

def scoreboard(request):
    """Display team scoreboard"""
    teams = Team.objects.filter(is_active=True).annotate(
        solve_count=Count('submissions', filter=Q(submissions__correct=True))
    ).order_by('-solve_count')
    
    # Calculate scores and last solve times
    team_data = []
    for team in teams:
        team_data.append({
            'team': team,
            'score': team.total_score,
            'solve_count': team.solve_count,
            'last_solve': team.last_solve_time
        })
    
    # Sort by score, then by last solve time (faster = better)
    team_data.sort(key=lambda x: (-x['score'], x['last_solve']))
    
    return render(request, 'ctf/scoreboard.html', {'team_data': team_data})

def scoreboard_json(request):
    """JSON API for scoreboard data"""
    teams = Team.objects.filter(is_active=True)
    
    data = []
    for team in teams:
        data.append({
            'name': team.name,
            'score': team.total_score,
            'solved_count': team.solved_challenges.count(),
            'last_solve': team.last_solve_time.isoformat() if team.last_solve_time else None
        })
    
    # Sort by score descending, then by last solve time ascending
    data.sort(key=lambda x: (-x['score'], x['last_solve'] or ''))
    
    return JsonResponse({'teams': data})

@login_required
def user_stats(request):
    """User statistics and progress"""
    user = request.user
    teams = user.teams.filter(is_active=True)
    
    # Get solved challenges per category
    solved_by_category = {}
    for category in Category.objects.all():
        solved_count = Submission.objects.filter(
            user=user, 
            correct=True, 
            challenge__category=category
        ).count()
        total_count = Challenge.objects.filter(
            category=category, 
            hidden=False
        ).count()
        solved_by_category[category.name] = {
            'solved': solved_count,
            'total': total_count
        }
    
    # Get solve timeline
    correct_submissions = Submission.objects.filter(
        user=user, correct=True
    ).order_by('timestamp').values('timestamp', 'challenge__title', 'challenge__value')
    
    context = {
        'teams': teams,
        'solved_by_category': solved_by_category,
        'timeline': list(correct_submissions),
        'total_solved': Submission.objects.filter(user=user, correct=True).count(),
    }
    return render(request, 'ctf/user_stats.html', context)

def download_file(request, file_id):
    """Download challenge file"""
    file_obj = get_object_or_404(ChallengeFile, pk=file_id)
    
    # Security: Only allow download if challenge is not hidden
    if file_obj.challenge.hidden:
        messages.error(request, 'File not available')
        return redirect('ctf:challenge_list')
    
    response = HttpResponse(file_obj.file.read(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{file_obj.filename}"'
    return response

# AJAX Views for better UX

@login_required
def submit_flag_ajax(request):
    """AJAX flag submission"""
    if request.method == 'POST':
        challenge_id = request.POST.get('challenge_id')
        submitted_flag = request.POST.get('flag', '').strip()
        
        try:
            challenge = Challenge.objects.get(id=challenge_id, hidden=False)
            
            # Check if already solved
            if challenge.is_solved_by_user(request.user):
                return JsonResponse({'success': False, 'message': 'Already solved!'})
            
            # Create submission
            submission = Submission.objects.create(
                user=request.user,
                challenge=challenge,
                submitted_flag=submitted_flag,
                team=request.user.teams.filter(is_active=True).first()
            )
            
            return JsonResponse({
                'success': submission.correct,
                'message': '🎉 Correct flag!' if submission.correct else '❌ Incorrect flag',
                'solved': submission.correct
            })
            
        except Challenge.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Challenge not found'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def challenge_stats_json(request, pk):
    """Get challenge statistics in JSON format"""
    challenge = get_object_or_404(Challenge, pk=pk)
    
    data = {
        'title': challenge.title,
        'solves': challenge.solve_count,
        'attempts': challenge.attempt_count,
        'value': challenge.value,
        'category': challenge.category.name,
    }
    
    return JsonResponse(data)
