from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ctf.models import Category, Challenge, Team, Hint, ChallengeFile
import random

class Command(BaseCommand):
    help = 'Populate database with sample CTF data'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create categories
        categories_data = [
            {'name': 'Web', 'description': 'Web application security challenges'},
            {'name': 'Crypto', 'description': 'Cryptography and encryption challenges'},
            {'name': 'Pwn', 'description': 'Binary exploitation challenges'},
            {'name': 'Rev', 'description': 'Reverse engineering challenges'},
            {'name': 'Forensics', 'description': 'Digital forensics challenges'},
            {'name': 'Misc', 'description': 'Miscellaneous challenges'},
        ]
        
        categories = []
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories.append(category)
            if created:
                self.stdout.write(f'Created category: {category.name}')
        
        # Create challenges
        challenges_data = [
            {
                'title': 'Easy Web Challenge',
                'description': 'Find the hidden flag in this simple web application. Look for common vulnerabilities like SQL injection or directory traversal.',
                'category': 'Web',
                'value': 100,
                'flag': 'flag{w3b_ch4ll3ng3_s0lv3d}',
            },
            {
                'title': 'Caesar Cipher',
                'description': 'Decrypt this message encrypted with Caesar cipher: IODJ{FDHVDU_FLSKHU_LV_HDV!}',
                'category': 'Crypto',
                'value': 150,
                'flag': 'flag{caesar_cipher_is_easy!}',
            },
            {
                'title': 'Buffer Overflow Basics',
                'description': 'Exploit this simple buffer overflow vulnerability to get the flag.',
                'category': 'Pwn',
                'value': 250,
                'flag': 'flag{buff3r_0v3rfl0w_pwn3d}',
            },
            {
                'title': 'Simple Crackme',
                'description': 'Reverse engineer this binary to find the correct password.',
                'category': 'Rev',
                'value': 200,
                'flag': 'flag{r3v3rs3_3ng1n33r1ng}',
            },
            {
                'title': 'Network Analysis',
                'description': 'Analyze this PCAP file to find the hidden flag in network traffic.',
                'category': 'Forensics',
                'value': 300,
                'flag': 'flag{n3tw0rk_f0r3ns1cs}',
            },
            {
                'title': 'Image Steganography',
                'description': 'There\'s something hidden in this image. Can you find it?',
                'category': 'Forensics',
                'value': 175,
                'flag': 'flag{h1dd3n_1n_p1x3ls}',
            },
            {
                'title': 'XOR Challenge',
                'description': 'Decrypt this XOR encrypted message to get the flag.',
                'category': 'Crypto',
                'value': 125,
                'flag': 'flag{x0r_1s_fun}',
            },
            {
                'title': 'Advanced Web Challenge',
                'description': 'This web application has multiple layers of security. Find your way through.',
                'category': 'Web',
                'value': 400,
                'flag': 'flag{adv4nc3d_w3b_h4ck3r}',
            },
            {
                'title': 'Mystery Challenge',
                'description': 'This challenge doesn\'t fit into any specific category. Good luck!',
                'category': 'Misc',
                'value': 350,
                'flag': 'flag{m1sc_ch4ll3ng3}',
            },
            {
                'title': 'Hash Cracking',
                'description': 'Crack this hash: 5d41402abc4b2a76b9719d911017c592',
                'category': 'Crypto',
                'value': 100,
                'flag': 'flag{hello}',
            },
        ]
        
        for chall_data in challenges_data:
            category = Category.objects.get(name=chall_data['category'])
            challenge, created = Challenge.objects.get_or_create(
                title=chall_data['title'],
                defaults={
                    'description': chall_data['description'],
                    'category': category,
                    'value': chall_data['value'],
                    'flag': chall_data['flag'],
                    'hidden': False,
                }
            )
            if created:
                self.stdout.write(f'Created challenge: {challenge.title}')
                
                # Add hints to some challenges
                if challenge.title == 'Easy Web Challenge':
                    Hint.objects.create(
                        challenge=challenge,
                        text='Try looking at the page source or checking for hidden directories.',
                        cost=10,
                        order=1
                    )
                    Hint.objects.create(
                        challenge=challenge,
                        text='Common web vulnerabilities include SQL injection and XSS.',
                        cost=25,
                        order=2
                    )
                
                elif challenge.title == 'Caesar Cipher':
                    Hint.objects.create(
                        challenge=challenge,
                        text='Caesar cipher shifts each letter by a fixed number. Try different shift values.',
                        cost=15,
                        order=1
                    )
                    Hint.objects.create(
                        challenge=challenge,
                        text='The shift value is 3. Decrypt by shifting backwards.',
                        cost=50,
                        order=2
                    )
                
                elif challenge.title == 'Hash Cracking':
                    Hint.objects.create(
                        challenge=challenge,
                        text='This is an MD5 hash of a common English word.',
                        cost=20,
                        order=1
                    )
        
        # Create sample users and teams
        sample_users = [
            {'username': 'alice', 'email': 'alice@example.com', 'password': 'password123'},
            {'username': 'bob', 'email': 'bob@example.com', 'password': 'password123'},
            {'username': 'charlie', 'email': 'charlie@example.com', 'password': 'password123'},
            {'username': 'diana', 'email': 'diana@example.com', 'password': 'password123'},
        ]
        
        users = []
        for user_data in sample_users:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['username'].capitalize(),
                }
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
                users.append(user)
                self.stdout.write(f'Created user: {user.username}')
        
        # Create sample teams
        if users:
            team1, created = Team.objects.get_or_create(
                name='CyberWarriors',
                defaults={'affiliation': 'University of Technology'}
            )
            if created:
                team1.members.add(users[0], users[1])
                self.stdout.write(f'Created team: {team1.name}')
            
            team2, created = Team.objects.get_or_create(
                name='HackerSquad',
                defaults={'affiliation': 'Security Institute'}
            )
            if created:
                team2.members.add(users[2], users[3])
                self.stdout.write(f'Created team: {team2.name}')
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write('You can now login with:')
        self.stdout.write('- Admin: admin/admin (superuser)')
        self.stdout.write('- Users: alice/password123, bob/password123, etc.')
