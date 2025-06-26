from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Challenge, Category, Team, Submission, Hint, HintUnlock
from .forms import TeamRegistrationForm, ChallengeSubmissionForm, HintUnlockForm
from django.contrib import messages

# Create your views here.

# Team registration view
def team_register(request):
    if request.method == 'POST':
        form = TeamRegistrationForm(request.POST)
        if form.is_valid():
            team = form.save()
            messages.success(request, 'Team registered successfully!')
            return redirect('challenge_list')
    else:
        form = TeamRegistrationForm()
    return render(request, 'ctf/team_register.html', {'form': form})

# Challenge list view
@login_required
def challenge_list(request):
    categories = Category.objects.all()
    challenges = Challenge.objects.filter(hidden=False)
    return render(request, 'ctf/challenge_list.html', {'categories': categories, 'challenges': challenges})

# Challenge detail and flag submission view
@login_required
def challenge_detail(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk)
    submission_form = ChallengeSubmissionForm()
    if request.method == 'POST':
        submission_form = ChallengeSubmissionForm(request.POST)
        if submission_form.is_valid():
            submission = submission_form.save(commit=False)
            submission.user = request.user
            submission.challenge = challenge
            # Optionally set team if user is in a team
            if hasattr(request.user, 'teams') and request.user.teams.exists():
                submission.team = request.user.teams.first()
            # Check flag (case-insensitive)
            submission.correct = (submission.submitted_flag.strip().lower() == challenge.flag.strip().lower())
            submission.save()
            if submission.correct:
                messages.success(request, 'Correct flag!')
            else:
                messages.error(request, 'Incorrect flag.')
            return redirect('challenge_detail', pk=challenge.pk)
    hints = challenge.hints.all()
    files = challenge.files.all()
    return render(request, 'ctf/challenge_detail.html', {
        'challenge': challenge,
        'submission_form': submission_form,
        'hints': hints,
        'files': files,
    })

# Hint unlock view
@login_required
def unlock_hint(request, hint_id):
    hint = get_object_or_404(Hint, pk=hint_id)
    if request.method == 'POST':
        HintUnlock.objects.get_or_create(user=request.user, hint=hint)
        messages.success(request, 'Hint unlocked!')
        return redirect('challenge_detail', pk=hint.challenge.pk)
    return render(request, 'ctf/unlock_hint.html', {'hint': hint})
