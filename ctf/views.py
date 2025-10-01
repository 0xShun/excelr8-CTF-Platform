from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from datetime import datetime
from django.db import connection, DatabaseError
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
    UserProfile, ChallengeFile, CompetitionSettings, ServiceInstance
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
        # Global recent activity: top 4 most recent correct submissions
        'recent_solves': Submission.objects.filter(correct=True)
            .select_related('user', 'challenge', 'team')
            .order_by('-timestamp')[:4],
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
            'individual_score': individual_score,
        })
    
    return render(request, 'ctf/home.html', context)

def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('ctf:home')
    else:
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

@login_required
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
            'last_solve': team.last_solve_time.isoformat() if team.last_solve_time else None,
            'affiliation': team.affiliation or ''
        })
    
    # Sort by score descending, then by last solve time ascending
    data.sort(key=lambda x: (-x['score'], x['last_solve'] or ''))
    
    return JsonResponse({'teams': data})

def scoreboard_timeseries_json(request):
    """JSON API: cumulative score timeseries for each active team.

    Includes submissions linked directly to the team or made by any current
    team member (covering older data where Submission.team may be null).
    """
    from django.db.models import Q

    series = []
    teams = Team.objects.filter(is_active=True)

    for team in teams:
        member_ids = list(team.members.values_list('id', flat=True))
        submissions = (
            Submission.objects.filter(
                Q(correct=True) & (Q(team=team) | Q(user_id__in=member_ids))
            )
            .select_related('challenge')
            .order_by('timestamp', 'id')
        )

        cumulative = 0
        points = []
        seen_ids = set()

        # Baseline at team registration (y=0)
        baseline_t = (team.registered_at or timezone.now()).isoformat()
        points.append({'t': baseline_t, 'y': 0})

        for s in submissions:
            # De-dupe in case a submission matches both OR branches
            if s.id in seen_ids:
                continue
            seen_ids.add(s.id)
            cumulative += getattr(s.challenge, 'value', 0)
            points.append({'t': s.timestamp.isoformat(), 'y': cumulative})

        # Extend to 'now' so the line reaches current time
        points.append({'t': timezone.now().isoformat(), 'y': cumulative})

        series.append({'team': team.name, 'data': points})

    return JsonResponse({'series': series, 'generated_at': timezone.now().isoformat()})

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


# =========================
# Admin Platform Views
# =========================

def _table_exists(model_cls):
    try:
        return model_cls._meta.db_table in connection.introspection.table_names()
    except Exception:
        return False


@staff_member_required
def admin_dashboard(request):
    settings = CompetitionSettings.get_settings()
    context = {
        'settings': settings,
        'counts': {
            'users': User.objects.count(),
            'teams': Team.objects.count(),
            'challenges': Challenge.objects.count(),
            'submissions': Submission.objects.count(),
            'instances': ServiceInstance.objects.count() if _table_exists(ServiceInstance) else 0,
        }
    }
    return render(request, 'ctf/admin_plat/dashboard.html', context)


@staff_member_required
def admin_users(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        if action and user_id:
            u = get_object_or_404(User, pk=user_id)
            if action == 'promote':
                u.is_staff = True
                messages.success(request, f'Promoted {u.username} to staff.')
            elif action == 'demote':
                u.is_staff = False
                messages.success(request, f'Demoted {u.username} from staff.')
            elif action == 'activate':
                u.is_active = True
                messages.success(request, f'Activated {u.username}.')
            elif action == 'deactivate':
                u.is_active = False
                messages.success(request, f'Deactivated {u.username}.')
            elif action == 'delete':
                username = u.username
                u.delete()
                messages.success(request, f'Deleted user {username}.')
                return redirect('ctf:admin_users')
            u.save()
            return redirect('ctf:admin_users')
    users = User.objects.all().select_related('userprofile')
    teams = Team.objects.all().prefetch_related('members')
    return render(request, 'ctf/admin_plat/users.html', {'users': users, 'teams': teams})


@staff_member_required
def admin_competition(request):
    settings = CompetitionSettings.get_settings()
    if request.method == 'POST':
        # Text/number fields
        settings.competition_name = request.POST.get('competition_name', settings.competition_name)
        settings.description = request.POST.get('description', settings.description)
        try:
            settings.max_team_size = int(request.POST.get('max_team_size', settings.max_team_size))
        except (TypeError, ValueError):
            pass

        # Boolean toggles: treat absence as False
        settings.registration_enabled = 'registration_enabled' in request.POST
        settings.team_registration_enabled = 'team_registration_enabled' in request.POST
        settings.freeze_scoreboard = 'freeze_scoreboard' in request.POST
        settings.show_scoreboard = 'show_scoreboard' in request.POST

        # Time fields (allow clearing freeze_time)
        for tf in ['start_time', 'end_time', 'freeze_time']:
            v = request.POST.get(tf, '')
            if v:
                try:
                    dt = datetime.fromisoformat(v)
                    aware = timezone.make_aware(dt)
                    setattr(settings, tf, aware)
                except Exception:
                    # leave unchanged on parse error
                    pass
            else:
                if tf == 'freeze_time':
                    setattr(settings, tf, None)
        settings.save()
        messages.success(request, 'Competition settings updated.')
        return redirect('ctf:admin_competition')
    return render(request, 'ctf/admin_plat/competition.html', {'settings': settings})


@staff_member_required
def admin_challenges(request):
    challenges = Challenge.objects.select_related('category').all()
    categories = Category.objects.all()
    return render(request, 'ctf/admin_plat/challenges.html', {'challenges': challenges, 'categories': categories})


@staff_member_required
def admin_challenge_new(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category')
        value = int(request.POST.get('value') or 100)
        difficulty = request.POST.get('difficulty', 'medium')
        flag = request.POST.get('flag', '')
        case_sensitive = request.POST.get('case_sensitive') == 'on'
        hidden = request.POST.get('hidden') == 'on'
        connection_info = request.POST.get('connection_info', '')
        author = request.POST.get('author', '')

        category = get_object_or_404(Category, pk=category_id)
        ch = Challenge.objects.create(
            title=title,
            description=description,
            category=category,
            value=value,
            difficulty=difficulty,
            flag=flag,
            case_sensitive=case_sensitive,
            hidden=hidden,
            connection_info=connection_info,
            author=author,
        )
        messages.success(request, 'Challenge created.')
        return redirect('ctf:admin_challenges')
    return render(request, 'ctf/admin_plat/challenge_form.html', {'categories': categories})


@staff_member_required
def admin_challenge_edit(request, pk):
    ch = get_object_or_404(Challenge, pk=pk)
    categories = Category.objects.all()
    if request.method == 'POST':
        subaction = request.POST.get('subaction')
        if subaction == 'upload_file' and request.FILES.get('file'):
            ChallengeFile.objects.create(challenge=ch, file=request.FILES['file'])
            messages.success(request, 'File uploaded.')
            return redirect('ctf:admin_challenge_edit', pk=ch.id)
        elif subaction == 'delete_file':
            fid = request.POST.get('file_id')
            if fid:
                fobj = get_object_or_404(ChallengeFile, pk=fid, challenge=ch)
                fobj.delete()
                messages.success(request, 'File deleted.')
                return redirect('ctf:admin_challenge_edit', pk=ch.id)
        else:
            ch.title = request.POST.get('title', ch.title)
            ch.description = request.POST.get('description', ch.description)
            cat_id = request.POST.get('category')
            if cat_id:
                ch.category = get_object_or_404(Category, pk=cat_id)
            ch.value = int(request.POST.get('value') or ch.value)
            ch.difficulty = request.POST.get('difficulty', ch.difficulty)
            ch.flag = request.POST.get('flag', ch.flag)
            ch.case_sensitive = request.POST.get('case_sensitive') == 'on'
            ch.hidden = request.POST.get('hidden') == 'on'
            ch.connection_info = request.POST.get('connection_info', ch.connection_info)
            ch.author = request.POST.get('author', ch.author)
            ch.save()
            messages.success(request, 'Challenge updated.')
            return redirect('ctf:admin_challenges')
    files = ch.files.all()
    return render(request, 'ctf/admin_plat/challenge_form.html', {'challenge': ch, 'categories': categories, 'files': files})


@staff_member_required
def admin_instances(request):
    if not _table_exists(ServiceInstance):
        messages.warning(request, 'ServiceInstance table not created yet. Please run migrations to enable instance management.')
        instances = []
        return render(request, 'ctf/admin_plat/instances.html', {'instances': instances, 'challenges': Challenge.objects.all()})
    instances = ServiceInstance.objects.select_related('challenge', 'requested_by').all()
    if request.method == 'POST':
        # Minimal state changes (start/stop) and connection info updates
        action = request.POST.get('action')
        inst_id = request.POST.get('id')
        if action == 'create':
            ch_id = request.POST.get('challenge')
            if ch_id:
                ch = get_object_or_404(Challenge, pk=ch_id)
                inst = ServiceInstance.objects.create(
                    challenge=ch,
                    requested_by=request.user,
                    status='stopped',
                    host=request.POST.get('host', ''),
                    port=(int(request.POST.get('port')) if request.POST.get('port') else None),
                    notes=request.POST.get('notes', ''),
                )
                messages.success(request, f'Instance created for {ch.title}.')
                return redirect('ctf:admin_instances')
        elif action and inst_id:
            inst = get_object_or_404(ServiceInstance, pk=inst_id)
            if action in ['start', 'stop']:
                inst.status = 'starting' if action == 'start' else 'stopping'
                messages.info(request, f'Instance {action} requested for {inst.challenge.title}.')
            elif action == 'save':
                inst.host = request.POST.get('host', inst.host)
                port = request.POST.get('port')
                inst.port = int(port) if port else None
                inst.status = request.POST.get('status', inst.status)
                inst.notes = request.POST.get('notes', inst.notes)
                messages.success(request, 'Instance updated.')
            inst.save()
            return redirect('ctf:admin_instances')
    return render(request, 'ctf/admin_plat/instances.html', {'instances': instances, 'challenges': Challenge.objects.all()})


@staff_member_required
def admin_categories(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            Category.objects.get_or_create(name=name)
            messages.success(request, f'Category "{name}" added.')
            return redirect('ctf:admin_categories')
    cats = Category.objects.all()
    return render(request, 'ctf/admin_plat/categories.html', {'categories': cats})


@staff_member_required
def admin_category_delete(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        if not cat.challenges.exists():
            cat.delete()
            messages.success(request, 'Category deleted.')
        else:
            messages.error(request, 'Cannot delete a category with challenges.')
        return redirect('ctf:admin_categories')
    return render(request, 'ctf/admin_plat/categories.html', {'categories': Category.objects.all()})
