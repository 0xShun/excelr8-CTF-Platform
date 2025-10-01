import io
import pytest
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from ctf.models import Category, Challenge, ChallengeFile, CompetitionSettings, ServiceInstance


@pytest.fixture
def staff_user(db, django_user_model):
    user = django_user_model.objects.create_user(
        username="admin_user",
        email="admin@example.com",
        password="password123",
        is_staff=True,
        is_superuser=True,
    )
    return user


@pytest.fixture
def client_staff(client, staff_user):
    client.force_login(staff_user)
    return client


def test_admin_dashboard_get(client_staff):
    url = reverse("ctf:admin_dashboard")
    resp = client_staff.get(url)
    assert resp.status_code == 200
    assert "Admin Platform" in resp.content.decode()


def test_admin_users_list_and_actions(client_staff, django_user_model):
    # Create a normal user to manage
    u = django_user_model.objects.create_user(
        username="jane", email="jane@example.com", password="pw"
    )
    url = reverse("ctf:admin_users")
    # List page loads
    resp = client_staff.get(url)
    assert resp.status_code == 200
    # Promote
    resp = client_staff.post(url, {"user_id": u.id, "action": "promote"}, follow=True)
    u.refresh_from_db()
    assert u.is_staff is True
    # Deactivate
    resp = client_staff.post(url, {"user_id": u.id, "action": "deactivate"}, follow=True)
    u.refresh_from_db()
    assert u.is_active is False
    # Activate
    resp = client_staff.post(url, {"user_id": u.id, "action": "activate"}, follow=True)
    u.refresh_from_db()
    assert u.is_active is True
    # Demote
    resp = client_staff.post(url, {"user_id": u.id, "action": "demote"}, follow=True)
    u.refresh_from_db()
    assert u.is_staff is False


def test_admin_competition_update(client_staff):
    settings = CompetitionSettings.get_settings()
    url = reverse("ctf:admin_competition")
    new_name = "SmokeTest CTF"
    payload = {
        "competition_name": new_name,
        "description": "Updated by test",
        "max_team_size": 5,
        "registration_enabled": "on",
        "team_registration_enabled": "on",
        "show_scoreboard": "on",
        "freeze_scoreboard": "",
        "start_time": timezone.now().strftime("%Y-%m-%dT%H:%M"),
        "end_time": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
        "freeze_time": "",
    }
    resp = client_staff.post(url, data=payload, follow=True)
    assert resp.status_code == 200
    settings.refresh_from_db()
    assert settings.competition_name == new_name
    assert settings.max_team_size == 5


def test_admin_categories_add_delete(client_staff):
    url = reverse("ctf:admin_categories")
    # Add
    resp = client_staff.post(url, {"name": "Forensics"}, follow=True)
    assert resp.status_code == 200
    assert Category.objects.filter(name="Forensics").exists()
    # Delete (only allowed if no challenges)
    cat = Category.objects.get(name="Forensics")
    del_url = reverse("ctf:admin_category_delete", args=[cat.id])
    resp = client_staff.post(del_url, follow=True)
    assert resp.status_code == 200
    assert not Category.objects.filter(name="Forensics").exists()


def test_admin_challenges_create_edit_upload_file(client_staff, tmp_path):
    # Ensure a category exists
    cat = Category.objects.create(name="Crypto")
    # Create a challenge
    create_url = reverse("ctf:admin_challenge_new")
    payload = {
        "title": "Test Challenge",
        "description": "Solve me",
        "category": cat.id,
        "value": 200,
        "difficulty": "medium",
        "flag": "flag{test}",
        "case_sensitive": "",
        "hidden": "",
        "connection_info": "",
        "author": "tester",
    }
    resp = client_staff.post(create_url, data=payload, follow=True)
    assert resp.status_code == 200
    ch = Challenge.objects.get(title="Test Challenge")
    # Edit page loads
    edit_url = reverse("ctf:admin_challenge_edit", args=[ch.id])
    resp = client_staff.get(edit_url)
    assert resp.status_code == 200
    # Update challenge
    payload_update = {
        "title": "Test Challenge v2",
        "description": "Updated",
        "category": cat.id,
        "value": 250,
        "difficulty": "hard",
        "flag": "flag{test2}",
        "case_sensitive": "on",
        "hidden": "",
        "connection_info": "localhost:31337",
        "author": "tester2",
    }
    resp = client_staff.post(edit_url, data=payload_update, follow=True)
    assert resp.status_code == 200
    ch.refresh_from_db()
    assert ch.value == 250
    assert ch.difficulty == "hard"
    # Upload a file
    file_bytes = b"dummy content"
    upload = SimpleUploadedFile("readme.txt", file_bytes, content_type="text/plain")
    resp = client_staff.post(
        edit_url,
        data={"subaction": "upload_file", "file": upload},
        format="multipart",
        follow=True,
    )
    assert resp.status_code == 200
    assert ChallengeFile.objects.filter(challenge=ch).count() == 1


def test_admin_instances_create_and_update(client_staff):
    # Ensure challenge exists
    cat = Category.objects.create(name="Pwn")
    ch = Challenge.objects.create(
        title="Instance Challenge",
        description="",
        category=cat,
        value=100,
        flag="flag{ok}",
        difficulty="easy",
    )
    url = reverse("ctf:admin_instances")
    # Create instance
    resp = client_staff.post(
        url,
        data={
            "action": "create",
            "challenge": ch.id,
            "host": "127.0.0.1",
            "port": 9001,
            "notes": "smoke",
        },
        follow=True,
    )
    assert resp.status_code == 200
    inst = ServiceInstance.objects.get(challenge=ch)
    # Save updates
    resp = client_staff.post(
        url,
        data={
            "id": inst.id,
            "action": "save",
            "host": "10.0.0.2",
            "port": 9002,
            "status": "running",
            "notes": "updated",
        },
        follow=True,
    )
    assert resp.status_code == 200
    inst.refresh_from_db()
    assert inst.status == "running"
    assert inst.port == 9002
    # Start/stop actions (state transitions only)
    resp = client_staff.post(url, data={"id": inst.id, "action": "start"}, follow=True)
    assert resp.status_code == 200
    resp = client_staff.post(url, data={"id": inst.id, "action": "stop"}, follow=True)
    assert resp.status_code == 200
